"""
Connection pool for NomDB client connections.
"""

from __future__ import annotations
import asyncio
import socket
from typing import List, Optional, Tuple
from nomdb.protocol.encoder import RESPEncoder
from nomdb.protocol.parser import RESPParser


class SyncConnection:
    """Synchronous socket connection to NomDB."""

    def __init__(self, host: str = "127.0.0.1", port: int = 6379, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.parser = RESPParser()

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def execute(self, *parts: Any) -> Any:
        if not self.sock:
            self.connect()

        payload = RESPEncoder.encode_command(*parts)
        self.sock.sendall(payload)

        while True:
            cmds = self.parser.get_parsed_commands()
            if cmds:
                return cmds[0]
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("Server closed connection")
            self.parser.feed(chunk)


class AsyncConnection:
    """Asynchronous asyncio socket connection to NomDB."""

    def __init__(self, host: str = "127.0.0.1", port: int = 6379):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.parser = RESPParser()

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

    async def close(self) -> None:
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
            self.reader = None

    async def execute(self, *parts: Any) -> Any:
        if not self.writer:
            await self.connect()

        payload = RESPEncoder.encode_command(*parts)
        self.writer.write(payload)
        await self.writer.drain()

        while True:
            cmds = self.parser.get_parsed_commands()
            if cmds:
                return cmds[0]
            chunk = await self.reader.read(65536)
            if not chunk:
                raise ConnectionError("Server closed connection")
            self.parser.feed(chunk)
