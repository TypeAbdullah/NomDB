"""
Integration tests for Python Client library (async and sync).
"""

import asyncio
import pytest
from nomdb.client.client import Client, AsyncClient


def test_sync_client_context_manager(running_server):
    with Client(host=running_server.settings.host, port=running_server.settings.port) as client:
        assert client.ping() == b"PONG"
        client.set("foo", "bar")
        assert client.get("foo") == b"bar"


def test_sync_client_ping(running_server):
    client = Client(host=running_server.settings.host, port=running_server.settings.port)
    assert client.ping() == b"PONG"
    assert client.ping("hello") == b"hello"
    client.close()
