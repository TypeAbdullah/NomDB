"""
Set data type operations.
Unordered collection of unique binary elements with constant-time lookup and set operations.
"""

from __future__ import annotations
import random
from typing import List, Optional, Set
from nomdb.protocol.exceptions import NomDBError


class SetStore:
    """Python set wrapper for Set data structure."""

    def __init__(self, initial_members: Optional[Set[bytes]] = None):
        self._members: Set[bytes] = set(initial_members) if initial_members else set()

    @property
    def members(self) -> Set[bytes]:
        return self._members

    def sadd(self, members: List[bytes]) -> int:
        """Add members to set. Returns count of newly added elements."""
        added = 0
        for m in members:
            if m not in self._members:
                self._members.add(m)
                added += 1
        return added

    def srem(self, members: List[bytes]) -> int:
        """Remove members from set. Returns count of removed elements."""
        removed = 0
        for m in members:
            if m in self._members:
                self._members.remove(m)
                removed += 1
        return removed

    def sismember(self, member: bytes) -> bool:
        return member in self._members

    def smismember(self, members: List[bytes]) -> List[int]:
        return [1 if m in self._members else 0 for m in members]

    def smembers(self) -> List[bytes]:
        return list(self._members)

    def scard(self) -> int:
        return len(self._members)

    def spop(self, count: int = 1) -> List[bytes]:
        """Pop random distinct elements from set."""
        popped = []
        for _ in range(min(count, len(self._members))):
            popped.append(self._members.pop())
        return popped

    def srandmember(self, count: int = 1) -> List[bytes]:
        """Return random element(s) without removing."""
        if not self._members or count == 0:
            return []
        if count > 0:
            # Distinct elements up to set size
            k = min(count, len(self._members))
            return random.sample(list(self._members), k)
        else:
            # Allow repeated elements if count is negative
            items = list(self._members)
            return [random.choice(items) for _ in range(abs(count))]

    @staticmethod
    def sunion(sets: List[SetStore]) -> Set[bytes]:
        res: Set[bytes] = set()
        for s in sets:
            res.update(s.members)
        return res

    @staticmethod
    def sinter(sets: List[SetStore]) -> Set[bytes]:
        if not sets:
            return set()
        # Sort by length for efficiency
        sorted_sets = sorted(sets, key=lambda s: len(s.members))
        res = set(sorted_sets[0].members)
        for s in sorted_sets[1:]:
            res.intersection_update(s.members)
            if not res:
                break
        return res

    @staticmethod
    def sdiff(sets: List[SetStore]) -> Set[bytes]:
        if not sets:
            return set()
        res = set(sets[0].members)
        for s in sets[1:]:
            res.difference_update(s.members)
            if not res:
                break
        return res
