"""
Integration tests for request pipelining.
"""

from nomdb.client.client import Client


def test_pipelining_batch(sync_client):
    pipe = sync_client.pipeline()
    for i in range(100):
        pipe.set(f"pipe:{i}", f"val_{i}")
        pipe.get(f"pipe:{i}")

    results = pipe.execute()
    assert len(results) == 200
    for i in range(0, 200, 2):
        assert results[i] == "OK"
        idx = i // 2
        assert results[i + 1] == f"val_{idx}".encode("ascii")
