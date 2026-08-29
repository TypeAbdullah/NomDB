"""
Replica Client Engine.
Maintains connection to primary, handles handshakes, PSYNC streaming, and command replication.
"""

from __future__ import annotations
import asyncio
import logging
from typing import TYPE_CHECKING, Optional
from nomdb.protocol.encoder import RESPEncoder
from nomdb.protocol.parser import RESPParser
from nomdb.protocol.resp import SimpleString
from nomdb.protocol.exceptions import ProtocolError

if TYPE_CHECKING:
    from nomdb.server.dispatcher import CommandDispatcher

logger = logging.getLogger("nomdb.replication.replica")


class ReplicaManager:
    """Manages outgoing connection to primary from replica node."""

    def __init__(
        self,
        master_host: str,
        master_port: int,
        local_port: int,
        dispatcher: CommandDispatcher,
    ):
        self.master_host = master_host
        self.master_port = master_port
        self.local_port = local_port
        self.dispatcher = dispatcher

        self.master_replid: str = "?"
        self.processed_offset: int = -1
        self.connected = False
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    def start(self) -> None:
        """Start replica synchronization loop."""
        self._running = True
        self._sync_task = asyncio.create_task(self._replication_client_loop())

    def stop(self) -> None:
        """Stop replica synchronization."""
        self._running = False
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
        if self._writer:
            self._writer.close()

    async def _replication_client_loop(self) -> None:
        """Replication client loop with automatic reconnect."""
        while self._running:
            try:
                logger.info(f"Connecting to primary {self.master_host}:{self.master_port}...")
                self._reader, self._writer = await asyncio.open_connection(
                    self.master_host, self.master_port
                )
                self.connected = True
                await self._perform_handshake()
                await self._consume_master_stream()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.connected = False
                logger.warning(f"Replication connection failed: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3.0)

    async def _send_command(self, *parts: str | bytes) -> bytes:
        """Send command and read one raw line/response."""
        cmd = RESPEncoder.encode_command(*parts)
        self._writer.write(cmd)
        await self._writer.drain()
        line = await self._reader.readline()
        return line

    async def _perform_handshake(self) -> None:
        """Perform Redis replication handshake sequence."""
        # 1. PING
        res = await self._send_command("PING")
        if not res.startswith(b"+PONG"):
            logger.warning(f"Unexpected PING response from primary: {res}")

        # 2. REPLCONF listening-port
        res = await self._send_command("REPLCONF", "listening-port", str(self.local_port))

        # 3. PSYNC
        psync_resp = await self._send_command("PSYNC", self.master_replid, str(self.processed_offset))
        psync_str = psync_resp.decode("utf-8", errors="replace").strip()

        if psync_str.startswith("+FULLRESYNC"):
            parts = psync_str.split()
            if len(parts) >= 3:
                self.master_replid = parts[1]
                self.processed_offset = int(parts[2])
                logger.info(f"FULLRESYNC with primary {self.master_replid} at offset {self.processed_offset}")
        elif psync_str.startswith("+CONTINUE"):
            parts = psync_str.split()
            if len(parts) >= 2:
                self.master_replid = parts[1]
                logger.info(f"Partial resynchronization (CONTINUE) with {self.master_replid}")

    async def _consume_master_stream(self) -> None:
        """Consume streamed replication commands from master."""
        parser = RESPParser()
        while self._running and self.connected:
            chunk = await self._reader.read(65536)
            if not chunk:
                logger.warning("Primary connection closed")
                self.connected = False
                break

            parser.feed(chunk)
            self.processed_offset += len(chunk)

            try:
                commands = parser.get_parsed_commands()
            except ProtocolError as pe:
                logger.error(f"Replication protocol error: {pe}")
                break

            for cmd_parts in commands:
                if not cmd_parts or not isinstance(cmd_parts, list):
                    continue

                cmd_name = (
                    cmd_parts[0].decode("utf-8", errors="replace").upper()
                    if isinstance(cmd_parts[0], bytes)
                    else str(cmd_parts[0]).upper()
                )

                if cmd_name == "PING":
                    continue  # Master heartbeat

                if cmd_name == "REPLCONF" and len(cmd_parts) > 1 and cmd_parts[1].upper() == b"GETACK":
                    # Respond with REPLCONF ACK <offset>
                    ack_cmd = RESPEncoder.encode_command("REPLCONF", "ACK", str(self.processed_offset))
                    self._writer.write(ack_cmd)
                    await self._writer.drain()
                    continue

                # Execute write command locally without re-propagating
                self.dispatcher.execute_replayed_command(0, cmd_parts)
