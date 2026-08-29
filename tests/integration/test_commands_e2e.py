"""
End-to-End integration tests for all command types through the client interface.
"""

import time
import pytest
from nomdb.protocol.exceptions import NomDBError


def test_e2e_strings(sync_client):
    assert sync_client.set("name", "Noman") == "OK"
    assert sync_client.get("name") == b"Noman"

    assert sync_client.incr("counter") == 1
    assert sync_client.incrby("counter", 5) == 6
    assert sync_client.decr("counter") == 5
    assert sync_client.decrby("counter", 2) == 3

    assert sync_client.set("temp", "val", ex=100) == "OK"
    assert sync_client.exists("temp") == 1
    assert sync_client.delete("temp") == 1
    assert sync_client.get("temp") is None


def test_e2e_hashes(sync_client):
    assert sync_client.hset("user:100", mapping={"name": "Alice", "age": "30"}) == 2
    assert sync_client.hget("user:100", "name") == b"Alice"
    assert sync_client.hget("user:100", "age") == b"30"

    all_fields = sync_client.hgetall("user:100")
    assert all_fields[b"name"] == b"Alice"
    assert all_fields[b"age"] == b"30"

    assert sync_client.hdel("user:100", "age") == 1
    assert sync_client.hget("user:100", "age") is None


def test_e2e_lists(sync_client):
    assert sync_client.rpush("tasks", "task1", "task2", "task3") == 3
    assert sync_client.lpush("tasks", "urgent") == 4
    assert sync_client.lrange("tasks", 0, -1) == [b"urgent", b"task1", b"task2", b"task3"]
    assert sync_client.lpop("tasks") == b"urgent"
    assert sync_client.rpop("tasks") == b"task3"


def test_e2e_sets(sync_client):
    assert sync_client.sadd("tags", "python", "database", "redis") == 3
    assert sync_client.sismember("tags", "python") == 1
    assert sync_client.sismember("tags", "rust") == 0
    members = sync_client.smembers("tags")
    assert set(members) == {b"python", b"database", b"redis"}
    assert sync_client.srem("tags", "redis") == 1
    assert sync_client.sismember("tags", "redis") == 0


def test_e2e_sorted_sets(sync_client):
    assert sync_client.zadd("leaderboard", {"player1": 100.0, "player2": 250.0, "player3": 50.0}) == 3
    assert sync_client.zscore("leaderboard", "player2") == 250.0
    assert sync_client.zrank("leaderboard", "player3") == 0
    assert sync_client.zrank("leaderboard", "player2") == 2
    assert sync_client.zrange("leaderboard", 0, 1) == [b"player3", b"player1"]


def test_e2e_wrongtype_error(sync_client):
    sync_client.set("str_key", "hello")
    with pytest.raises(NomDBError, match="WRONGTYPE"):
        sync_client.hget("str_key", "field")


def test_e2e_info_and_dbsize(sync_client):
    sync_client.set("k1", "v1")
    sync_client.set("k2", "v2")
    assert sync_client.execute_command("DBSIZE") >= 2

    info = sync_client.execute_command("INFO")
    info_str = info.decode("utf-8") if isinstance(info, bytes) else str(info)
    assert "nomdb_version:1.0.0" in info_str
    assert "connected_clients" in info_str
    assert "used_memory" in info_str
