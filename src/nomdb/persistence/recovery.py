"""
Crash Recovery Engine.
Restores database state by loading snapshot and replaying AOF log.
"""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING
from nomdb.persistence.aof import AOFManager
from nomdb.persistence.snapshot import SnapshotManager
from nomdb.protocol.parser import RESPParser
from nomdb.protocol.exceptions import ProtocolError
from nomdb.storage.database import DatabaseManager

if TYPE_CHECKING:
    from nomdb.expiration.manager import ExpirationManager
    from nomdb.server.dispatcher import CommandDispatcher

logger = logging.getLogger("nomdb.persistence.recovery")


class RecoveryManager:
    """Coordinates startup data loading and crash recovery."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        snapshot_manager: SnapshotManager,
        aof_manager: AOFManager,
        expiration_manager: ExpirationManager,
    ):
        self._db_manager = db_manager
        self._snapshot = snapshot_manager
        self._aof = aof_manager
        self._expiration = expiration_manager

    def recover(self, dispatcher: Optional[CommandDispatcher] = None) -> None:
        """
        Execute recovery pipeline:
        1. Load Snapshot (RDB) if available.
        2. Replay AOF log if available.
        3. Rebuild active expiration min-heap.
        """
        if self._aof.enabled and self._aof.filepath.exists():
            try:
                self._replay_aof(dispatcher)
                logger.info(f"Replayed AOF from {self._aof.filepath}")
            except Exception as e:
                logger.error(f"Failed to replay AOF {self._aof.filepath}: {e}", exc_info=True)
        elif self._snapshot.enabled and self._snapshot.filepath.exists():
            try:
                snapshot_loaded = self._snapshot.load(self._db_manager)
                if snapshot_loaded:
                    logger.info(f"Loaded snapshot from {self._snapshot.filepath}")
            except Exception as e:
                logger.error(f"Failed to load snapshot {self._snapshot.filepath}: {e}", exc_info=True)

        # Rebuild expiration heap from restored keyspaces
        self._rebuild_expiration_heap()

    def _replay_aof(self, dispatcher: Optional[CommandDispatcher]) -> None:
        """Replay commands stored in AOF log."""
        if not self._aof.filepath.exists():
            return

        parser = RESPParser()
        current_db_id = 0
        replayed_count = 0

        with open(self._aof.filepath, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                parser.feed(chunk)

                try:
                    commands = parser.get_parsed_commands()
                except ProtocolError as pe:
                    logger.warning(f"AOF ended with truncated or incomplete frame: {pe}")
                    break

                for cmd_parts in commands:
                    if not cmd_parts or not isinstance(cmd_parts, list):
                        continue

                    cmd_name = (
                        cmd_parts[0].decode("utf-8", errors="replace").upper()
                        if isinstance(cmd_parts[0], bytes)
                        else str(cmd_parts[0]).upper()
                    )

                    if cmd_name == "SELECT" and len(cmd_parts) > 1:
                        try:
                            current_db_id = int(cmd_parts[1])
                        except ValueError:
                            pass
                        continue

                    if dispatcher is not None:
                        # Execute command via dispatcher without re-logging to AOF
                        dispatcher.execute_replayed_command(current_db_id, cmd_parts)
                        replayed_count += 1

        logger.info(f"Successfully replayed {replayed_count} write commands from AOF")

    def _rebuild_expiration_heap(self) -> None:
        """Scan all keys and re-populate the expiration min-heap."""
        for db_id in range(self._db_manager._num_databases):
            keyspace = self._db_manager.get_database(db_id)
            for k, entry in keyspace.entries.items():
                if entry.expire_at_ms is not None:
                    self._expiration.register_expiration(db_id, k, entry.expire_at_ms)
