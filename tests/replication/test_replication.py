"""
Replication integration tests (Primary -> Replica synchronization and command streaming).
"""

import asyncio
import pytest
from nomdb.config.settings import ServerSettings
from nomdb.server.server import NomDBServer
from nomdb.client.client import AsyncClient
from nomdb.protocol.exceptions import NomDBError


@pytest.mark.asyncio
async def test_primary_replica_replication(temp_data_dir):
    primary_dir = temp_data_dir / "primary"
    replica_dir = temp_data_dir / "replica"

    primary_settings = ServerSettings(
        host="127.0.0.1",
        port=6395,
        data_dir=str(primary_dir),
        aof_enabled=False,
        metrics_enabled=False,
    )
    replica_settings = ServerSettings(
        host="127.0.0.1",
        port=6396,
        data_dir=str(replica_dir),
        aof_enabled=False,
        metrics_enabled=False,
        replica_of_host="127.0.0.1",
        replica_of_port=6395,
    )

    primary_server = NomDBServer(primary_settings)
    await primary_server.start()

    replica_server = NomDBServer(replica_settings)
    await replica_server.start()

    # Wait for handshake and initial sync
    await asyncio.sleep(0.5)

    primary_client = AsyncClient(host=primary_settings.host, port=primary_settings.port)
    replica_client = AsyncClient(host=replica_settings.host, port=replica_settings.port)

    # 1. Write on Primary
    await primary_client.set("replicated_key", "replicated_value")
    await primary_client.execute_command("HSET", "user:rep", "name", "Noman")

    # Wait for command propagation
    await asyncio.sleep(0.3)

    # 2. Read on Replica
    assert await replica_client.get("replicated_key") == b"replicated_value"
    assert await replica_client.execute_command("HGET", "user:rep", "name") == b"Noman"

    # 3. Verify Replica is READONLY
    with pytest.raises(NomDBError, match="READONLY"):
        await replica_client.set("direct_write", "forbidden")

    await primary_client.close()
    await replica_client.close()

    await replica_server.shutdown()
    await primary_server.shutdown()
