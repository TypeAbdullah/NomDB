"""
Unit tests for memory tracking and sizing of data types.
"""

from nomdb.storage.database import DatabaseManager
from nomdb.storage.entry import DataType
from nomdb.memory.tracker import MemoryTracker
from nomdb.storage.datatypes import HashStore, ListStore, SetStore, SortedSetStore


def test_memory_tracker_stats():
    db_mgr = DatabaseManager(1)
    ks = db_mgr.get_database(0)
    tracker = MemoryTracker(db_mgr)

    initial_used = tracker.get_used_memory()
    assert initial_used > 0

    ks.set(b"str_key", DataType.STRING, b"X" * 1000)
    h = HashStore({b"f1": b"v1", b"f2": b"v2"})
    ks.set(b"hash_key", DataType.HASH, h)

    after_used = tracker.get_used_memory()
    assert after_used > initial_used

    stats = tracker.get_memory_stats()
    assert stats["total_keys"] == 2
    assert "used_memory_human" in stats
    assert stats["type_counts"]["string"] == 1
    assert stats["type_counts"]["hash"] == 1
