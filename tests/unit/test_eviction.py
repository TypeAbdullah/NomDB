"""
Unit tests for maxmemory enforcement and LRU/LFU eviction policies.
"""

import pytest
from nomdb.storage.database import DatabaseManager
from nomdb.storage.entry import DataType
from nomdb.memory.tracker import MemoryTracker
from nomdb.memory.eviction import EvictionManager
from nomdb.protocol.exceptions import OutOfMemoryError


def test_eviction_allkeys_lru():
    db_mgr = DatabaseManager(1)
    ks = db_mgr.get_database(0)
    tracker = MemoryTracker(db_mgr)

    # Set tight memory limit
    evict_mgr = EvictionManager(
        db_mgr, tracker, max_memory_bytes=1024 * 1024 + 500, policy="allkeys-lru", samples=10
    )

    # Add key1 with old access time
    e1 = ks.set(b"key1", DataType.STRING, b"A" * 100)
    e1.last_accessed_at_ms = 1000

    # Add key2 with newer access time
    e2 = ks.set(b"key2", DataType.STRING, b"B" * 100)
    e2.last_accessed_at_ms = 5000

    # Trigger eviction check
    evict_mgr.max_memory_bytes = tracker.get_used_memory() - 50
    evict_mgr.check_and_evict()

    # Oldest accessed key1 should have been evicted
    assert ks.exists(b"key1") is False
    assert ks.exists(b"key2") is True


def test_eviction_noeviction_raises_oom():
    db_mgr = DatabaseManager(1)
    ks = db_mgr.get_database(0)
    tracker = MemoryTracker(db_mgr)

    evict_mgr = EvictionManager(
        db_mgr, tracker, max_memory_bytes=100, policy="noeviction"
    )

    ks.set(b"key1", DataType.STRING, b"A" * 500)
    with pytest.raises(OutOfMemoryError):
        evict_mgr.check_and_evict()
