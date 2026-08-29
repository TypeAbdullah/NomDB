"""
Primary Replication Server Engine.
Coordinates replica synchronization, PSYNC backlog streaming, and offset tracking.
"""

from __future__ import annotations
import asyncio
import logging
import secrets
import time
from typing import TYPE_CHECKING, Dict, List, Optional
from nomdb.protocol.encoder import RESPEncoder
from nomdb.protocol.resp import SimpleString, BulkString
from nomdb.replication.backlog import ReplicationBacklog

if TYPE_CHECKING:
    from nomdb.server.connection import ClientConnection
    from nomdb.storage.database import DatabaseManager

logger = logging.getLogger("nomdb.replication.primary")


class ReplicaClientInfo:
    """State tracking for a connected replica."""

    def __init__(self, connection: ClientConnection):
        self.connection = connection
        self.listening_port: int = 0
        self.ack_offset: int = 0
        self.last_ack_time: float = time.time()
        self.state: str = "HANDSHAKE"  # HANDSHAKE, SYNCING, ONLINE


class PrimaryReplicationManager:
    """Manages replication from primary perspective."""

    def __init__(self, backlog_size: int = 1024 * 1024):
        self.replid: str = secrets.token_hex(20)  # 40-character hex string
        self.backlog = ReplicationBacklog(backlog_size)
        self._replicas: Dict[ClientConnection, ReplicaClientInfo] = {}
        self._ping_task: Optional[asyncio.Task] = None
        self._running = False

    @property
    def master_offset(self) -> int:
        return self.backlog.master_offset

    @property
    def connected_replicas_count(self) -> int:
        return len(self._replicas)

    def start(self) -> None:
        self._running = True
        self._ping_task = asyncio.create_task(self._replication_ping_loop())

    def stop(self) -> None:
        self._running = False
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()

    def register_replica(self, client: ClientConnection) -> ReplicaClientInfo:
        """Register client connection as replica."""
        if client not in self._replicas:
            self._replicas[client] = ReplicaClientInfo(client)
        return self._replicas[client]

    def remove_replica(self, client: ClientConnection) -> None:
        self._replicas.pop(client, None)

    def update_replica_ack(self, client: ClientConnection, offset: int) -> None:
        """Record ACK offset received from replica."""
        if client in self._replicas:
            self._replicas[client].ack_offset = offset
            self._replicas[client].last_ack_time = time.time()

    def propagate_write(self, cmd_parts: List[bytes]) -> None:
        """
        Record write command in replication backlog and stream to all online replicas.
        """
        raw_cmd = RESPEncoder.encode_command(*cmd_parts)
        self.backlog.feed(raw_cmd)

        for client, info in list(self._replicas.items()):
            if info.state == "ONLINE":
                client.send_raw(raw_cmd)

    def handle_psync(
        self,
        client: ClientConnection,
        requested_replid: str,
        requested_offset: int,
        db_manager: DatabaseManager,
    ) -> bytes:
        """
        Handle PSYNC command from replica:
        - If replid matches and offset is in backlog: +CONTINUE <replid>\r\n followed by missing backlog stream.
        - Else: +FULLRESYNC <replid> <offset>\r\n followed by snapshot data.
        """
        info = self.register_replica(client)

        if (
            requested_replid == self.replid
            and self.backlog.is_offset_in_backlog(requested_offset)
        ):
            # Partial resynchronization
            info.state = "ONLINE"
            continue_resp = RESPEncoder.encode(SimpleString(f"CONTINUE {self.replid}"))
            backlog_data = self.backlog.get_data_since_offset(requested_offset) or b""
            return continue_resp + backlog_data
        else:
            # Full resynchronization
            info.state = "ONLINE"
            current_offset = self.master_offset
            fullresync_resp = RESPEncoder.encode(SimpleString(f"FULLRESYNC {self.replid} {current_offset}"))
            # Stream current database state as set commands
            commands_stream = bytearray()
            for db_id in range(db_manager._num_databases):
                keyspace = db_manager.get_database(db_id)
                for k, entry in keyspace.entries.items():
                    if entry.is_expired():
                        continue
                    # Replay minimal command
                    commands_stream.extend(RESPEncoder.encode_command(b"SET", k, entry.value if isinstance(entry.value, bytes) else str(entry.value).encode("utf-8")))
            return fullresync_resp + bytes(commands_stream)

    async def _replication_ping_loop(self) -> None:
        """Send periodic PING heartbeats to online replicas every 10s."""
        while self._running:
            try:
                await asyncio.sleep(10.0)
                ping_raw = RESPEncoder.encode_command(b"PING")
                for client, info in list(self._replicas.items()):
                    if info.state == "ONLINE":
                        client.send_raw(ping_raw)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in replication ping loop: {e}")
