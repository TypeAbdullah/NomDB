"""
Persistence tests for AOF, Snapshot (RDB), and Crash Recovery.
"""

import asyncio
import pytest
from nomdb.config.settings import ServerSettings
from nomdb.server.server import NomDBServer
from nomdb.client.client import AsyncClient


@pytest.mark.asyncio
async def test_persistence_restart_and_recovery(temp_data_dir):
    settings = ServerSettings(
        host="127.0.0.1",
        port=6389,
        data_dir=str(temp_data_dir),
        aof_enabled=True,
        aof_fsync="always",
        snapshot_enabled=True,
        metrics_enabled=False,
    )

    # 1. Start Server 1, populate diverse data types
    server1 = NomDBServer(settings)
    await server1.start()

    c1 = AsyncClient(host=settings.host, port=settings.port)
    await c1.set("persisted_str", "hello_aof")
    await c1.execute_command("HSET", "persisted_hash", "f1", "v1", "f2", "v2")
    await c1.execute_command("RPUSH", "persisted_list", "item1", "item2")
    await c1.execute_command("SADD", "persisted_set", "alpha", "beta")
    await c1.execute_command("ZADD", "persisted_zset", "100.0", "alice", "200.0", "bob")
    await c1.close()

    # Graceful shutdown (saves snapshot and flushes AOF)
    await server1.shutdown()

    # 2. Start Server 2 from same data_dir and verify recovery
    server2 = NomDBServer(settings)
    await server2.start()

    c2 = AsyncClient(host=settings.host, port=settings.port)
    assert await c2.get("persisted_str") == b"hello_aof"
    assert await c2.execute_command("HGET", "persisted_hash", "f1") == b"v1"
    assert await c2.execute_command("LRANGE", "persisted_list", 0, -1) == [b"item1", b"item2"]
    members = await c2.execute_command("SMEMBERS", "persisted_set")
    assert set(members) == {b"alpha", b"beta"}
    assert await c2.execute_command("ZSCORE", "persisted_zset", "bob") == b"200"
    await c2.close()

    await server2.shutdown()


@pytest.mark.asyncio
async def test_corrupted_aof_tail_recovery(temp_data_dir):
    settings = ServerSettings(
        host="127.0.0.1",
        port=6390,
        data_dir=str(temp_data_dir),
        aof_enabled=True,
        aof_fsync="always",
        metrics_enabled=False,
    )

    server1 = NomDBServer(settings)
    await server1.start()

    c1 = AsyncClient(host=settings.host, port=settings.port)
    await c1.set("key1", "val1")
    await c1.set("key2", "val2")
    await c1.close()
    await server1.shutdown()

    # Intentionally corrupt the tail of the AOF file (partial write simulation)
    with open(settings.aof_path, "ab") as f:
        f.write(b"*3\r\n$3\r\nSET\r\n$4\r\nkey3\r\n$10\r\ntrunc")  # Missing trailing bytes

    # Server 2 should safely recover valid commands up to truncation point
    server2 = NomDBServer(settings)
    await server2.start()

    c2 = AsyncClient(host=settings.host, port=settings.port)
    assert await c2.get("key1") == b"val1"
    assert await c2.get("key2") == b"val2"
    assert await c2.get("key3") is None
    await c2.close()

    await server2.shutdown()
