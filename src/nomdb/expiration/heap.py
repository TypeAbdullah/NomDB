"""
Min-heap indexed priority queue for key expirations.
"""

from __future__ import annotations
import heapq
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(order=True)
class ExpirationItem:
    expire_at_ms: int
    db_id: int = field(compare=False)
    key: bytes = field(compare=False)


class ExpirationHeap:
    """Min-heap containing (expire_at_ms, db_id, key) tuples."""

    def __init__(self):
        self._heap: List[ExpirationItem] = []

    def push(self, db_id: int, key: bytes, expire_at_ms: int) -> None:
        """Add expiration record."""
        heapq.heappush(self._heap, ExpirationItem(expire_at_ms, db_id, key))

    def pop_expired(self, now_ms: Optional[int] = None, max_count: int = 100) -> List[Tuple[int, bytes]]:
        """Pop all items where expire_at_ms <= now_ms, up to max_count."""
        now = now_ms if now_ms is not None else int(time.time() * 1000)
        expired = []
        while self._heap and self._heap[0].expire_at_ms <= now and len(expired) < max_count:
            item = heapq.heappop(self._heap)
            expired.append((item.db_id, item.key))
        return expired

    def peek_next_expire_ms(self) -> Optional[int]:
        """Return earliest expiration timestamp in heap."""
        if self._heap:
            return self._heap[0].expire_at_ms
        return None

    def size(self) -> int:
        return len(self._heap)

    def clear(self) -> None:
        self._heap.clear()
