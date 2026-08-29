"""
Integration tests for Cluster Mode, Hash Slots, and Redirection.
"""

import pytest
from nomdb.config.settings import ServerSettings
from nomdb.server.server import NomDBServer
from nomdb.client.client import AsyncClient
from nomdb.protocol.exceptions import NomDBError, MovedError


@pytest.mark.asyncio
async def test_cluster_commands_and_routing(temp_data_dir):
    settings = ServerSettings(
        host="127.0.0.1",
        port=6398,
        data_dir=str(temp_data_dir),
        cluster_enabled=True,
        metrics_enabled=False,
    )

    server = NomDBServer(settings)
    await server.start()

    client = AsyncClient(host=settings.host, port=settings.port)

    # 1. Assign slots 0..5000 to local node
    res = await client.execute_command("CLUSTER", "ADDSLOTS", "0", "1", "2", "3", "4", "5")
    assert res == "OK"

    # 2. Query CLUSTER INFO & CLUSTER NODES
    info = await client.execute_command("CLUSTER", "INFO")
    info_str = info.decode("utf-8") if isinstance(info, bytes) else str(info)
    assert "cluster_slots_assigned:6" in info_str

    nodes = await client.execute_command("CLUSTER", "NODES")
    nodes_str = nodes.decode("utf-8") if isinstance(nodes, bytes) else str(nodes)
    assert "myself,master" in nodes_str

    # 3. Test CLUSTER KEYSLOT
    slot = await client.execute_command("CLUSTER", "KEYSLOT", "user:{100}:profile")
    assert isinstance(slot, int)

    await client.close()
    await server.shutdown()
