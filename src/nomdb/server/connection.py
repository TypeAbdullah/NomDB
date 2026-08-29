"""
Client connection state and socket buffer management.
"""

from __future__ import annotations
import asyncio
import time
from typing import TYPE_CHECKING, List, Optional, Set
from nomdb.protocol.parser import RESPParser
from nomdb.protocol.encoder import RESPEncoder
from nomdb.transaction.manager import TransactionState

if TYPE_CHECKING:
    from nomdb.server.server import NomDBServer


class ClientConnection:
    """Represents a connected client with socket streams and session state."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        server: NomDBServer,
    ):
        self.reader = reader
        self.writer = writer
        self.server = server

        self.client_id: str = f"{writer.get_extra_info('peername')}"
        self.created_at: float = time.time()
        self.last_active_at: float = time.time()

        self.db_id: int = 0
        self.authenticated: bool = not server.settings.require_auth
        self.should_close: bool = False

        self.parser = RESPParser()
        self.transaction = TransactionState()

        # Pub/Sub subscriptions for this connection
        self.subscribed_channels: Set[bytes] = set()
        self.subscribed_patterns: Set[bytes] = set()

    @property
    def is_pubsub(self) -> bool:
        return bool(self.subscribed_channels or self.subscribed_patterns)

    @property
    def total_subscriptions(self) -> int:
        return len(self.subscribed_channels) + len(self.subscribed_patterns)

    def touch(self) -> None:
        self.last_active_at = time.time()

    def send_response(self, value: Any) -> None:
        """Encode and send RESP response directly to client socket."""
        raw_resp = RESPEncoder.encode(value)
        self.send_raw(raw_resp)

    def send_raw(self, raw_bytes: bytes) -> None:
        """Send pre-encoded bytes to socket writer."""
        if self.writer and not self.writer.is_closing():
            try:
                self.writer.write(raw_bytes)
            except Exception:
                self.should_close = True

    async def flush(self) -> None:
        """Drain socket buffer."""
        if self.writer and not self.writer.is_closing():
            try:
                await self.writer.drain()
            except Exception:
                self.should_close = True

    def close(self) -> None:
        """Close client connection safely."""
        self.should_close = True
        if self.writer and not self.writer.is_closing():
            try:
                self.writer.close()
            except Exception:
                pass
