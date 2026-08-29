"""
AOF (Append-Only Log) Persistence Engine.
Logs every write command to disk and provides configurable fsync strategies and AOF rewrite.
"""

from __future__ import annotations
import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional
from nomdb.protocol.encoder import RESPEncoder
from nomdb.storage.database import DatabaseManager
from nomdb.storage.entry import DataType

logger = logging.getLogger("nomdb.persistence.aof")


class AOFManager:
    """Manages append-only file persistence and synchronization."""

    def __init__(
        self,
        filepath: Path,
        fsync_mode: str = "everysec",  # always, everysec, no
        enabled: bool = True,
    ):
        self.filepath = filepath
        self.fsync_mode = fsync_mode.lower()
        self.enabled = enabled
        self._file: Optional[open] = None
        self._buffer = bytearray()
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False
        self.total_writes = 0
        self.last_fsync_time = 0.0

    def start(self) -> None:
        """Open AOF file and start background fsync worker if everysec."""
        if not self.enabled:
            return

        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.filepath, "a+b")
        self._running = True

        if self.fsync_mode == "everysec":
            self._sync_task = asyncio.create_task(self._periodic_fsync())

    def stop(self) -> None:
        """Flush buffer, fsync, and close file."""
        self._running = False
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()

        if self._file:
            self.flush(force_sync=True)
            self._file.close()
            self._file = None

    def append_command(self, db_id: int, command_parts: List[bytes]) -> None:
        """Append a write command to AOF."""
        if not self.enabled or not self._file:
            return

        # If multi-database, prepend SELECT db_id command if needed
        resp_data = RESPEncoder.encode_command(*command_parts)
        self._buffer.extend(resp_data)
        self.total_writes += 1

        if self.fsync_mode == "always":
            self.flush(force_sync=True)
        elif len(self._buffer) >= 65536:
            self.flush(force_sync=False)

    def flush(self, force_sync: bool = False) -> None:
        """Write in-memory buffer to disk."""
        if not self._file or not self._buffer:
            return

        self._file.write(self._buffer)
        self._file.flush()
        self._buffer.clear()

        if force_sync or self.fsync_mode == "always":
            try:
                os.fsync(self._file.fileno())
            except OSError:
                pass

    async def _periodic_fsync(self) -> None:
        """Background task for appendfsync everysec."""
        while self._running:
            try:
                await asyncio.sleep(1.0)
                if self._file:
                    self.flush(force_sync=True)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in AOF fsync task: {e}")

    def rewrite(self, db_manager: DatabaseManager, target_path: Optional[Path] = None) -> None:
        """
        Rewrite AOF to minimize file size by exporting current keyspace state as RESP commands.
        """
        out_path = target_path or self.filepath.with_suffix(".aof.tmp")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "wb") as f:
            for db_id in range(db_manager._num_databases):
                keyspace = db_manager.get_database(db_id)
                if not keyspace.entries:
                    continue

                # SELECT db_id
                f.write(RESPEncoder.encode_command(b"SELECT", str(db_id).encode("ascii")))

                for key, entry in keyspace.entries.items():
                    if entry.is_expired():
                        continue

                    # Generate minimal reconstruction commands
                    if entry.data_type == DataType.STRING:
                        f.write(RESPEncoder.encode_command(b"SET", key, entry.value))

                    elif entry.data_type == DataType.HASH:
                        for field, val in entry.value.fields.items():
                            f.write(RESPEncoder.encode_command(b"HSET", key, field, val))

                    elif entry.data_type == DataType.LIST:
                        for item in entry.value.items:
                            f.write(RESPEncoder.encode_command(b"RPUSH", key, item))

                    elif entry.data_type == DataType.SET:
                        for member in entry.value.members:
                            f.write(RESPEncoder.encode_command(b"SADD", key, member))

                    elif entry.data_type == DataType.ZSET:
                        for member, score in entry.value.dict_index.items():
                            f.write(RESPEncoder.encode_command(b"ZADD", key, str(score).encode("ascii"), member))

                    # TTL restoration
                    if entry.expire_at_ms is not None:
                        f.write(RESPEncoder.encode_command(b"PEXPIREAT", key, str(entry.expire_at_ms).encode("ascii")))

            f.flush()
            os.fsync(f.fileno())

        if target_path is None:
            # Replace current AOF file safely
            if self._file:
                self._file.close()
            os.replace(out_path, self.filepath)
            self._file = open(self.filepath, "a+b")
