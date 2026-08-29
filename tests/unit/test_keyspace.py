"""
Unit tests for Keyspace operations, TTL, Scan, and Glob matching.
"""

from nomdb.storage.keyspace import Keyspace
from nomdb.storage.entry import DataType


def test_keyspace_set_get_delete():
    ks = Keyspace()
    assert ks.size() == 0
    ks.set(b"user:1", DataType.STRING, b"Noman")
    assert ks.size() == 1
    assert ks.exists(b"user:1") is True

    entry = ks.get_entry(b"user:1")
    assert entry is not None
    assert entry.value == b"Noman"

    assert ks.delete(b"user:1") == 1
    assert ks.exists(b"user:1") is False


def test_keyspace_scan_and_keys():
    ks = Keyspace()
    for i in range(25):
        ks.set(f"key:{i}".encode("ascii"), DataType.STRING, b"val")

    assert len(ks.keys(b"key:*")) == 25
    assert len(ks.keys(b"key:1*")) == 11  # 1, 10..19

    cursor, keys = ks.scan(0, count=10)
    assert cursor == 10
    assert len(keys) == 10

    cursor2, keys2 = ks.scan(cursor, count=10)
    assert cursor2 == 20
    assert len(keys2) == 10

    cursor3, keys3 = ks.scan(cursor2, count=10)
    assert cursor3 == 0  # Completed
    assert len(keys3) == 5
