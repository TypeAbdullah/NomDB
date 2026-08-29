"""
List data type operations.
Backed by double-ended queue supporting fast head/tail operations and positional queries.
"""

from __future__ import annotations
from collections import deque
from typing import List, Optional, Tuple
from nomdb.protocol.exceptions import NomDBError, NoSuchKeyError


class ListStore:
    """Double-ended queue list data structure."""

    def __init__(self, initial_items: Optional[List[bytes]] = None):
        self._deque: deque[bytes] = deque(initial_items) if initial_items else deque()

    @property
    def items(self) -> deque[bytes]:
        return self._deque

    def lpush(self, values: List[bytes]) -> int:
        """Push values onto head of list (in left-to-right order as specified in Redis)."""
        for v in values:
            self._deque.appendleft(v)
        return len(self._deque)

    def rpush(self, values: List[bytes]) -> int:
        """Push values onto tail of list."""
        for v in values:
            self._deque.append(v)
        return len(self._deque)

    def lpop(self, count: int = 1) -> List[bytes]:
        popped = []
        for _ in range(min(count, len(self._deque))):
            popped.append(self._deque.popleft())
        return popped

    def rpop(self, count: int = 1) -> List[bytes]:
        popped = []
        for _ in range(min(count, len(self._deque))):
            popped.append(self._deque.pop())
        return popped

    def llen(self) -> int:
        return len(self._deque)

    def lindex(self, index: int) -> Optional[bytes]:
        n = len(self._deque)
        if index < 0:
            index = n + index
        if 0 <= index < n:
            return self._deque[index]
        return None

    def lset(self, index: int, value: bytes) -> None:
        n = len(self._deque)
        if index < 0:
            index = n + index
        if 0 <= index < n:
            self._deque[index] = value
        else:
            raise NomDBError("index out of range")

    def lrange(self, start: int, stop: int) -> List[bytes]:
        n = len(self._deque)
        if n == 0:
            return []
        if start < 0:
            start = max(0, n + start)
        if stop < 0:
            stop = max(0, n + stop)
        if start > stop or start >= n:
            return []
        stop = min(stop, n - 1)
        # Convert to list and slice
        items_list = list(self._deque)
        return items_list[start : stop + 1]

    def ltrim(self, start: int, stop: int) -> None:
        n = len(self._deque)
        if n == 0:
            return
        if start < 0:
            start = max(0, n + start)
        if stop < 0:
            stop = max(0, n + stop)
        if start > stop or start >= n:
            self._deque.clear()
            return
        stop = min(stop, n - 1)
        items_list = list(self._deque)[start : stop + 1]
        self._deque = deque(items_list)

    def linsert(self, where: str, pivot: bytes, value: bytes) -> int:
        """Insert value before or after pivot. Returns new length or -1 if pivot not found."""
        try:
            idx = self._deque.index(pivot)
        except ValueError:
            return -1

        if where.upper() == "BEFORE":
            self._deque.insert(idx, value)
        elif where.upper() == "AFTER":
            self._deque.insert(idx + 1, value)
        else:
            raise NomDBError("syntax error")
        return len(self._deque)

    def lrem(self, count: int, element: bytes) -> int:
        """Remove occurrences of element from list."""
        removed = 0
        if count == 0:
            # Remove all occurrences
            new_deque = deque(x for x in self._deque if x != element)
            removed = len(self._deque) - len(new_deque)
            self._deque = new_deque
        elif count > 0:
            # Remove from head to tail up to count
            new_deque = deque()
            for x in self._deque:
                if x == element and removed < count:
                    removed += 1
                else:
                    new_deque.append(x)
            self._deque = new_deque
        else:
            # Remove from tail to head up to abs(count)
            target = abs(count)
            rev_deque = deque()
            for x in reversed(self._deque):
                if x == element and removed < target:
                    removed += 1
                else:
                    rev_deque.appendleft(x)
            self._deque = rev_deque
        return removed
