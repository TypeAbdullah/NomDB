"""
Memory usage tracker and memory overhead estimation for NomDB keyspace objects.
"""

from __future__ import annotations
import sys
from typing import Any, Dict, List, Tuple
from nomdb.storage.database import DatabaseManager
from nomdb.storage.entry import DataType, StorageEntry
from nomdb.storage.datatypes import HashStore, ListStore, SetStore, SortedSetStore


class MemoryTracker:
    """Estimates memory footprint of data structures and keyspace objects."""

    def __init__(self, db_manager: DatabaseManager):
        self._db_manager = db_manager
        self._peak_memory_bytes: int = 0
        self.evicted_keys_count = 0

    @classmethod
    def estimate_entry_bytes(cls, key: bytes, entry: StorageEntry) -> int:
        """Estimate total bytes consumed by a key and its value."""
        base_size = sys.getsizeof(key) + sys.getsizeof(entry)

        val = entry.value
        if entry.data_type == DataType.STRING:
            if isinstance(val, (bytes, bytearray)):
                base_size += sys.getsizeof(val)
            else:
                base_size += sys.getsizeof(str(val))

        elif entry.data_type == DataType.HASH:
            if isinstance(val, HashStore):
                base_size += sys.getsizeof(val.fields)
                for f, v in val.fields.items():
                    base_size += sys.getsizeof(f) + sys.getsizeof(v)

        elif entry.data_type == DataType.LIST:
            if isinstance(val, ListStore):
                base_size += sys.getsizeof(val.items)
                for item in val.items:
                    base_size += sys.getsizeof(item)

        elif entry.data_type == DataType.SET:
            if isinstance(val, SetStore):
                base_size += sys.getsizeof(val.members)
                for item in val.members:
                    base_size += sys.getsizeof(item)

        elif entry.data_type == DataType.ZSET:
            if isinstance(val, SortedSetStore):
                base_size += sys.getsizeof(val.dict_index)
                for member, score in val.dict_index.items():
                    base_size += sys.getsizeof(member) + sys.getsizeof(score) + 64  # SkipList node overhead

        return base_size

    def get_used_memory(self) -> int:
        """Calculate total used memory in bytes."""
        total = 1024 * 1024  # Base server runtime overhead (1MB)
        for db_id in range(self._db_manager._num_databases):
            keyspace = self._db_manager.get_database(db_id)
            total += sys.getsizeof(keyspace.entries)
            for k, entry in keyspace.entries.items():
                total += self.estimate_entry_bytes(k, entry)

        if total > self._peak_memory_bytes:
            self._peak_memory_bytes = total
        return total

    @property
    def peak_memory(self) -> int:
        return self._peak_memory_bytes

    def get_memory_stats(self) -> Dict[str, Any]:
        """Detailed memory stats for INFO memory."""
        used = self.get_used_memory()
        type_counts: Dict[str, int] = {t.value: 0 for t in DataType}
        type_memory: Dict[str, int] = {t.value: 0 for t in DataType}

        for db_id in range(self._db_manager._num_databases):
            keyspace = self._db_manager.get_database(db_id)
            for k, entry in keyspace.entries.items():
                type_counts[entry.data_type.value] += 1
                type_memory[entry.data_type.value] += self.estimate_entry_bytes(k, entry)

        return {
            "used_memory": used,
            "used_memory_human": f"{used / (1024 * 1024):.2f}M",
            "used_memory_peak": self._peak_memory_bytes,
            "used_memory_peak_human": f"{self._peak_memory_bytes / (1024 * 1024):.2f}M",
            "evicted_keys": self.evicted_keys_count,
            "total_keys": self._db_manager.total_keys(),
            "type_counts": type_counts,
            "type_memory": type_memory,
        }
