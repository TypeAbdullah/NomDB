"""
Active and Lazy Expiration Manager.
Runs periodic background inspections of expiration heap and keyspaces.
"""

from __future__ import annotations
import asyncio
import logging
import time
from typing import Optional
from nomdb.expiration.heap import ExpirationHeap
from nomdb.storage.database import DatabaseManager

logger = logging.getLogger("nomdb.expiration")


class ExpirationManager:
    """Coordinates active expiration and tracks metrics."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        interval_ms: int = 100,
        batch_size: int = 20,
    ):
        self._db_manager = db_manager
        self._interval_sec = max(0.01, interval_ms / 1000.0)
        self._batch_size = batch_size
        self._heap = ExpirationHeap()
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self.expired_keys_count = 0

    @property
    def heap(self) -> ExpirationHeap:
        return self._heap

    def register_expiration(self, db_id: int, key: bytes, expire_at_ms: int) -> None:
        """Register a key's expiration with the min-heap."""
        self._heap.push(db_id, key, expire_at_ms)

    def start(self) -> None:
        """Start the active expiration background task."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._active_expire_loop())

    def stop(self) -> None:
        """Stop the active expiration task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    async def _active_expire_loop(self) -> None:
        """Periodic loop to actively purge expired keys."""
        while self._running:
            try:
                self.purge_expired_batch()
                await asyncio.sleep(self._interval_sec)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in active expiration loop: {e}", exc_info=True)
                await asyncio.sleep(self._interval_sec)

    def purge_expired_batch(self) -> int:
        """
        Actively pop and delete expired keys from the heap and sample random keys.
        Returns count of keys deleted in this cycle.
        """
        now = int(time.time() * 1000)
        deleted = 0

        # 1. Pop from min-heap
        expired_candidates = self._heap.pop_expired(now_ms=now, max_count=self._batch_size)
        for db_id, key in expired_candidates:
            keyspace = self._db_manager.get_database(db_id)
            entry = keyspace.entries.get(key)
            if entry is not None and entry.is_expired(now):
                keyspace.delete(key)
                deleted += 1
                self.expired_keys_count += 1

        # 2. Random sampling across databases (active sample sweep like Redis)
        for db_id in range(self._db_manager._num_databases):
            keyspace = self._db_manager.get_database(db_id)
            if not keyspace.entries:
                continue
            # Sample up to batch_size keys
            sample_keys = list(keyspace.entries.keys())[:self._batch_size]
            for key in sample_keys:
                entry = keyspace.entries.get(key)
                if entry is not None and entry.is_expired(now):
                    keyspace.delete(key)
                    deleted += 1
                    self.expired_keys_count += 1

        return deleted
