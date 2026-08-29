"""
Transaction Engine (MULTI, EXEC, DISCARD, WATCH, UNWATCH).
Provides atomic execution and optimistic concurrency control.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple
from nomdb.protocol.resp import OK, QUEUED
from nomdb.storage.database import DatabaseManager


class TransactionState:
    """Per-connection transaction state."""

    def __init__(self):
        self.in_transaction: bool = False
        self.queued_commands: List[List[bytes]] = []
        # Watched keys: dict of (db_id, key) -> version_at_watch_time
        self.watched_keys: Dict[Tuple[int, bytes], int] = {}
        self.dirty: bool = False  # Set to True if watched key was modified

    def multi(self) -> None:
        self.in_transaction = True
        self.queued_commands.clear()

    def discard(self) -> None:
        self.in_transaction = False
        self.queued_commands.clear()
        self.dirty = False

    def watch(self, db_id: int, key: bytes, current_version: int) -> None:
        self.watched_keys[(db_id, key)] = current_version

    def unwatch(self) -> None:
        self.watched_keys.clear()
        self.dirty = False

    def queue_command(self, cmd_parts: List[bytes]) -> None:
        self.queued_commands.append(cmd_parts)

    def check_watched_keys(self, db_manager: DatabaseManager) -> bool:
        """
        Check if any watched key was modified since WATCH was called.
        Returns True if safe (no modification), False if modified.
        """
        if self.dirty:
            return False

        for (db_id, key), watched_version in self.watched_keys.items():
            keyspace = db_manager.get_database(db_id)
            current_ver = keyspace.get_version(key)
            if current_ver != watched_version:
                return False
        return True
