"""
Multi-database manager for NomDB.
Holds indexed database keyspaces (0 to 15 by default).
"""

from __future__ import annotations
from typing import Dict, List
from nomdb.storage.keyspace import Keyspace


class DatabaseManager:
    """Manages separate keyspace databases."""

    def __init__(self, num_databases: int = 16):
        self._num_databases = num_databases
        self._databases: Dict[int, Keyspace] = {
            i: Keyspace() for i in range(num_databases)
        }

    def get_database(self, db_id: int) -> Keyspace:
        """Get keyspace for database id."""
        if db_id not in self._databases:
            if 0 <= db_id < 256:
                self._databases[db_id] = Keyspace()
            else:
                raise ValueError(f"Invalid database id: {db_id}")
        return self._databases[db_id]

    def total_keys(self) -> int:
        """Total key count across all databases."""
        return sum(db.size() for db in self._databases.values())

    def flush_all(self) -> None:
        """Flush all databases."""
        for db in self._databases.values():
            db.flush()
