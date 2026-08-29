"""
Unit tests for active and lazy expiration mechanisms.
"""

import time
from nomdb.storage.database import DatabaseManager
from nomdb.storage.entry import DataType
from nomdb.expiration.manager import ExpirationManager


def test_lazy_expiration():
    db_mgr = DatabaseManager(1)
    ks = db_mgr.get_database(0)

    now_ms = int(time.time() * 1000)
    # Set key that expired 1 second ago
    ks.set(b"expired_key", DataType.STRING, b"old_val", expire_at_ms=now_ms - 1000)
    # Set key that expires in 100 seconds
    ks.set(b"live_key", DataType.STRING, b"live_val", expire_at_ms=now_ms + 100000)

    # Lazy expiration check on get_entry
    assert ks.get_entry(b"expired_key") is None
    assert ks.exists(b"expired_key") is False

    assert ks.get_entry(b"live_key") is not None
    assert ks.exists(b"live_key") is True


def test_active_expiration_batch():
    db_mgr = DatabaseManager(1)
    ks = db_mgr.get_database(0)
    exp_mgr = ExpirationManager(db_mgr)

    now_ms = int(time.time() * 1000)
    for i in range(10):
        key = f"temp:{i}".encode("ascii")
        ks.set(key, DataType.STRING, b"val", expire_at_ms=now_ms - 50)
        exp_mgr.register_expiration(0, key, now_ms - 50)

    assert ks.size() == 10
    purged = exp_mgr.purge_expired_batch()
    assert purged >= 10
    assert ks.size() == 0
