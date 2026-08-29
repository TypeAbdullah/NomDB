"""
Eviction policies when memory exceeds configured maxmemory.
"""

from __future__ import annotations
import random
from typing import List, Optional, Tuple
from nomdb.memory.tracker import MemoryTracker
from nomdb.protocol.exceptions import OutOfMemoryError
from nomdb.storage.database import DatabaseManager
from nomdb.storage.entry import StorageEntry


class EvictionManager:
    """Handles maxmemory enforcement and key evictions."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        memory_tracker: MemoryTracker,
        max_memory_bytes: int = 0,
        policy: str = "noeviction",
        samples: int = 5,
    ):
        self._db_manager = db_manager
        self._tracker = memory_tracker
        self.max_memory_bytes = max_memory_bytes
        self.policy = policy.lower()
        self.samples = samples

    def check_and_evict(self) -> None:
        """
        Check if used memory exceeds max_memory_bytes.
        If so, evict keys until under limit or raise OutOfMemoryError.
        """
        if self.max_memory_bytes <= 0:
            return  # Unlimited

        used = self._tracker.get_used_memory()
        if used <= self.max_memory_bytes:
            return

        if self.policy == "noeviction":
            raise OutOfMemoryError()

        # Evict loop
        while used > self.max_memory_bytes:
            evicted_key = self._find_and_evict_candidate()
            if not evicted_key:
                # Could not find any suitable keys to evict
                raise OutOfMemoryError("Cannot evict any keys under current policy")
            self._tracker.evicted_keys_count += 1
            used = self._tracker.get_used_memory()

    def _find_and_evict_candidate(self) -> bool:
        """Pick sample candidates and evict best according to policy."""
        candidates: List[Tuple[int, bytes, StorageEntry]] = []

        # Sample across databases
        for db_id in range(self._db_manager._num_databases):
            keyspace = self._db_manager.get_database(db_id)
            if not keyspace.entries:
                continue

            all_keys = list(keyspace.entries.keys())
            sample_keys = random.sample(all_keys, min(self.samples, len(all_keys)))

            for k in sample_keys:
                entry = keyspace.entries.get(k)
                if entry is None:
                    continue

                if "volatile" in self.policy and entry.expire_at_ms is None:
                    continue  # Skip keys without TTL

                candidates.append((db_id, k, entry))

        if not candidates:
            return False

        # Apply eviction policy sort
        if "lru" in self.policy:
            # Smallest last_accessed_at_ms (least recently used)
            candidates.sort(key=lambda item: item[2].last_accessed_at_ms)
        elif "lfu" in self.policy:
            # Smallest access_count (least frequently used)
            candidates.sort(key=lambda item: item[2].access_count)

        # Evict the best candidate
        target_db_id, target_key, _ = candidates[0]
        keyspace = self._db_manager.get_database(target_db_id)
        keyspace.delete(target_key)
        return True
