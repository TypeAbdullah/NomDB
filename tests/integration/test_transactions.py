"""
Integration tests for transactions (MULTI, EXEC, DISCARD, WATCH, UNWATCH).
"""

from nomdb.client.client import Client


def test_transaction_multi_exec(sync_client):
    assert sync_client.execute_command("MULTI") == "OK"
    assert sync_client.execute_command("SET", "balance", "100") == "QUEUED"
    assert sync_client.execute_command("INCRBY", "balance", "50") == "QUEUED"
    assert sync_client.execute_command("GET", "balance") == "QUEUED"

    results = sync_client.execute_command("EXEC")
    assert results == ["OK", 150, b"150"]


def test_transaction_discard(sync_client):
    sync_client.set("foo", "initial")
    assert sync_client.execute_command("MULTI") == "OK"
    assert sync_client.execute_command("SET", "foo", "changed") == "QUEUED"
    assert sync_client.execute_command("DISCARD") == "OK"

    # Foo should remain initial
    assert sync_client.get("foo") == b"initial"


def test_transaction_watch_abort_on_concurrent_modification(running_server):
    c1 = Client(host=running_server.settings.host, port=running_server.settings.port)
    c2 = Client(host=running_server.settings.host, port=running_server.settings.port)

    c1.set("stock", "10")

    # Client 1 watches stock
    assert c1.execute_command("WATCH", "stock") == "OK"
    assert c1.execute_command("MULTI") == "OK"
    assert c1.execute_command("INCR", "stock") == "QUEUED"

    # Client 2 mutates stock concurrently
    c2.set("stock", "20")

    # Client 1 tries to EXEC -> should abort and return None (nil)
    res = c1.execute_command("EXEC")
    assert res is None

    # Stock remains 20
    assert c1.get("stock") == b"20"

    c1.close()
    c2.close()
