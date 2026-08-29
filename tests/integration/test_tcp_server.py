"""
Integration test for raw TCP socket communication with NomDBServer.
"""

import asyncio
import pytest
import socket


def test_tcp_raw_ping_pong(running_server):
    s = socket.create_connection((running_server.settings.host, running_server.settings.port))
    s.sendall(b"*1\r\n$4\r\nPING\r\n")
    data = s.recv(1024)
    s.close()
    assert data == b"+PONG\r\n"


def test_tcp_raw_set_get(running_server):
    s = socket.create_connection((running_server.settings.host, running_server.settings.port))
    # SET test_key "Hello World"
    s.sendall(b"*3\r\n$3\r\nSET\r\n$8\r\ntest_key\r\n$11\r\nHello World\r\n")
    res1 = s.recv(1024)
    assert res1 == b"+OK\r\n"

    # GET test_key
    s.sendall(b"*2\r\n$3\r\nGET\r\n$8\r\ntest_key\r\n")
    res2 = s.recv(1024)
    assert res2 == b"$11\r\nHello World\r\n"
    s.close()
