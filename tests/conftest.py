"""
Pytest configuration and shared fixtures for NomDB tests.
Runs test server in a background daemon thread with its own event loop to support
both synchronous and asynchronous client testing concurrently without deadlock.
"""

import asyncio
import pytest
import shutil
import socket
import tempfile
import threading
import time
from pathlib import Path
from nomdb.config.settings import ServerSettings
from nomdb.server.server import NomDBServer
from nomdb.client.client import Client, AsyncClient


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for testing persistence."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def server_settings(temp_data_dir):
    """Generate isolated test server settings on random high port."""
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()

    return ServerSettings(
        host="127.0.0.1",
        port=port,
        data_dir=str(temp_data_dir),
        aof_enabled=True,
        snapshot_enabled=True,
        metrics_enabled=False,
    )


@pytest.fixture
def running_server(server_settings):
    """Start an isolated NomDBServer in a dedicated background thread."""
    server = NomDBServer(server_settings)
    loop = asyncio.new_event_loop()
    ready_event = threading.Event()

    def run_server():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.start())
        ready_event.set()
        loop.run_forever()

    th = threading.Thread(target=run_server, daemon=True)
    th.start()
    ready_event.wait(timeout=5.0)

    # Yield server for test execution
    yield server

    # Teardown
    shutdown_future = asyncio.run_coroutine_threadsafe(server.shutdown(), loop)
    try:
        shutdown_future.result(timeout=5.0)
    except Exception:
        pass
    loop.call_soon_threadsafe(loop.stop)
    th.join(timeout=3.0)


@pytest.fixture
def sync_client(running_server):
    """Provide a connected synchronous client."""
    client = Client(host=running_server.settings.host, port=running_server.settings.port)
    yield client
    client.close()


@pytest.fixture
async def async_client(running_server):
    """Provide a connected asynchronous client."""
    client = AsyncClient(host=running_server.settings.host, port=running_server.settings.port)
    yield client
    await client.close()
