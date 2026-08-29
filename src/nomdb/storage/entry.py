"""
Storage entry wrapper for database keyspace values with metadata for LRU, LFU, and expiration.
"""

from __future__ import annotations
import enum
import time
from dataclasses import dataclass, field
from typing import Any, Optional


class DataType(enum.Enum):
    STRING = "string"
    HASH = "hash"
    LIST = "list"
    SET = "set"
    ZSET = "zset"


@dataclass(slots=True)
class StorageEntry:
    data_type: DataType
    value: Any
    expire_at_ms: Optional[int] = None  # Epoch milliseconds or None
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    last_accessed_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    access_count: int = 1

    def is_expired(self, current_time_ms: Optional[int] = None) -> bool:
        if self.expire_at_ms is None:
            return False
        now = current_time_ms if current_time_ms is not None else int(time.time() * 1000)
        return now >= self.expire_at_ms

    def touch(self, current_time_ms: Optional[int] = None) -> None:
        """Update LRU timestamp and LFU frequency count."""
        self.last_accessed_at_ms = current_time_ms if current_time_ms is not None else int(time.time() * 1000)
        # Logarithmic LFU frequency increment counter (Redis-style approximation)
        if self.access_count < 255:
            self.access_count += 1

    @property
    def ttl_seconds(self) -> int:
        if self.expire_at_ms is None:
            return -1
        remaining = self.expire_at_ms - int(time.time() * 1000)
        if remaining <= 0:
            return -2
        return int(remaining / 1000)

    @property
    def ttl_ms(self) -> int:
        if self.expire_at_ms is None:
            return -1
        remaining = self.expire_at_ms - int(time.time() * 1000)
        if remaining <= 0:
            return -2
        return remaining
