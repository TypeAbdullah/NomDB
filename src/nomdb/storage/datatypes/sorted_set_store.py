"""
Sorted Set (ZSET) data structure using a SkipList + Hash Index.
Provides O(log N) insert, delete, rank, and range queries by score or rank.
"""

from __future__ import annotations
import math
import random
from typing import Dict, List, Optional, Tuple, Union
from nomdb.protocol.exceptions import NomDBError

SKIPLIST_MAXLEVEL = 32
SKIPLIST_P = 0.25  # Probability for level generation


class SkipListNode:
    """Node in the SkipList with forward pointers, backward pointer, and span tracking."""

    __slots__ = ("member", "score", "backward", "level")

    def __init__(self, level: int, score: float, member: bytes):
        self.score = score
        self.member = member
        self.backward: Optional[SkipListNode] = None
        # Array of [forward_node, span] for each level
        self.level: List[List[Union[Optional[SkipListNode], int]]] = [[None, 0] for _ in range(level)]


class SkipList:
    """SkipList with span metrics for O(log N) rank calculation."""

    def __init__(self):
        self.header = SkipListNode(SKIPLIST_MAXLEVEL, 0.0, b"")
        self.tail: Optional[SkipListNode] = None
        self.length = 0
        self.level = 1

    @staticmethod
    def _random_level() -> int:
        lvl = 1
        while random.random() < SKIPLIST_P and lvl < SKIPLIST_MAXLEVEL:
            lvl += 1
        return lvl

    def insert(self, score: float, member: bytes) -> SkipListNode:
        update: List[Optional[SkipListNode]] = [None] * SKIPLIST_MAXLEVEL
        rank = [0] * SKIPLIST_MAXLEVEL

        x = self.header
        for i in range(self.level - 1, -1, -1):
            rank[i] = rank[i + 1] if i < self.level - 1 else 0
            while (
                x.level[i][0] is not None
                and (
                    x.level[i][0].score < score
                    or (x.level[i][0].score == score and x.level[i][0].member < member)
                )
            ):
                rank[i] += x.level[i][1]
                x = x.level[i][0]
            update[i] = x

        lvl = self._random_level()
        if lvl > self.level:
            for i in range(self.level, lvl):
                rank[i] = 0
                update[i] = self.header
                update[i].level[i][1] = self.length
            self.level = lvl

        node = SkipListNode(lvl, score, member)
        for i in range(lvl):
            node.level[i][0] = update[i].level[i][0]
            update[i].level[i][0] = node

            # Update span
            node.level[i][1] = update[i].level[i][1] - (rank[0] - rank[i])
            update[i].level[i][1] = (rank[0] - rank[i]) + 1

        for i in range(lvl, self.level):
            update[i].level[i][1] += 1

        node.backward = None if update[0] == self.header else update[0]
        if node.level[0][0] is not None:
            node.level[0][0].backward = node
        else:
            self.tail = node

        self.length += 1
        return node

    def delete_node(self, node: SkipListNode, update: List[Optional[SkipListNode]]) -> None:
        for i in range(self.level):
            if update[i].level[i][0] == node:
                update[i].level[i][1] += node.level[i][1] - 1
                update[i].level[i][0] = node.level[i][0]
            else:
                update[i].level[i][1] -= 1

        if node.level[0][0] is not None:
            node.level[0][0].backward = node.backward
        else:
            self.tail = node.backward

        while self.level > 1 and self.header.level[self.level - 1][0] is None:
            self.level -= 1
        self.length -= 1

    def delete(self, score: float, member: bytes) -> bool:
        update: List[Optional[SkipListNode]] = [None] * SKIPLIST_MAXLEVEL
        x = self.header
        for i in range(self.level - 1, -1, -1):
            while (
                x.level[i][0] is not None
                and (
                    x.level[i][0].score < score
                    or (x.level[i][0].score == score and x.level[i][0].member < member)
                )
            ):
                x = x.level[i][0]
            update[i] = x

        target = x.level[0][0]
        if target is not None and target.score == score and target.member == member:
            self.delete_node(target, update)
            return True
        return False

    def get_rank(self, score: float, member: bytes) -> int:
        """Return 1-based rank of member in sorted set, or 0 if not found."""
        rank = 0
        x = self.header
        for i in range(self.level - 1, -1, -1):
            while (
                x.level[i][0] is not None
                and (
                    x.level[i][0].score < score
                    or (x.level[i][0].score == score and x.level[i][0].member <= member)
                )
            ):
                rank += x.level[i][1]
                x = x.level[i][0]
            if x.member == member:
                return rank
        return 0

    def get_element_by_rank(self, rank: int) -> Optional[SkipListNode]:
        """Find node by 1-based rank in O(log N)."""
        traversed = 0
        x = self.header
        for i in range(self.level - 1, -1, -1):
            while x.level[i][0] is not None and (traversed + x.level[i][1] <= rank):
                traversed += x.level[i][1]
                x = x.level[i][0]
            if traversed == rank:
                return x
        return None


class SortedSetStore:
    """Complete Sorted Set structure combining SkipList and dictionary."""

    def __init__(self):
        self._dict: Dict[bytes, float] = {}
        self._skiplist = SkipList()

    @property
    def dict_index(self) -> Dict[bytes, float]:
        return self._dict

    def zcard(self) -> int:
        return len(self._dict)

    def zscore(self, member: bytes) -> Optional[float]:
        return self._dict.get(member)

    def zadd(self, score_members: List[Tuple[float, bytes]], nx: bool = False, xx: bool = False, ch: bool = False) -> int:
        """
        Add elements with scores.
        nx: Only add new elements.
        xx: Only update existing elements.
        ch: Return count of changed elements (added + score updated).
        """
        added = 0
        changed = 0

        for score, member in score_members:
            exists = member in self._dict
            if nx and exists:
                continue
            if xx and not exists:
                continue

            if exists:
                old_score = self._dict[member]
                if old_score != score:
                    self._skiplist.delete(old_score, member)
                    self._skiplist.insert(score, member)
                    self._dict[member] = score
                    changed += 1
            else:
                self._skiplist.insert(score, member)
                self._dict[member] = score
                added += 1
                changed += 1

        return changed if ch else added

    def zincrby(self, delta: float, member: bytes) -> float:
        curr_score = self._dict.get(member, 0.0)
        new_score = curr_score + delta
        if member in self._dict:
            self._skiplist.delete(curr_score, member)
        self._skiplist.insert(new_score, member)
        self._dict[member] = new_score
        return new_score

    def zrem(self, members: List[bytes]) -> int:
        removed = 0
        for m in members:
            if m in self._dict:
                score = self._dict.pop(m)
                self._skiplist.delete(score, m)
                removed += 1
        return removed

    def zrank(self, member: bytes) -> Optional[int]:
        """0-based rank (lowest to highest)."""
        if member not in self._dict:
            return None
        score = self._dict[member]
        rank_1_based = self._skiplist.get_rank(score, member)
        return rank_1_based - 1 if rank_1_based > 0 else None

    def zrevrank(self, member: bytes) -> Optional[int]:
        """0-based reverse rank (highest to lowest)."""
        if member not in self._dict:
            return None
        rank = self.zrank(member)
        if rank is None:
            return None
        return len(self._dict) - 1 - rank

    def zrange(self, start: int, stop: int, with_scores: bool = False) -> List[Union[bytes, Tuple[bytes, float]]]:
        """Return range by 0-based index."""
        n = len(self._dict)
        if n == 0:
            return []
        if start < 0:
            start = max(0, n + start)
        if stop < 0:
            stop = max(0, n + stop)
        if start > stop or start >= n:
            return []
        stop = min(stop, n - 1)

        result: List[Any] = []
        node = self._skiplist.get_element_by_rank(start + 1)
        count = stop - start + 1
        while node is not None and count > 0:
            if with_scores:
                result.append((node.member, node.score))
            else:
                result.append(node.member)
            node = node.level[0][0]
            count -= 1

        return result

    def zrevrange(self, start: int, stop: int, with_scores: bool = False) -> List[Union[bytes, Tuple[bytes, float]]]:
        """Return reverse range by 0-based index."""
        n = len(self._dict)
        if n == 0:
            return []
        if start < 0:
            start = max(0, n + start)
        if stop < 0:
            stop = max(0, n + stop)
        if start > stop or start >= n:
            return []
        stop = min(stop, n - 1)

        result: List[Any] = []
        # Rank from end is (n - start)
        node = self._skiplist.get_element_by_rank(n - start)
        count = stop - start + 1
        while node is not None and count > 0:
            if with_scores:
                result.append((node.member, node.score))
            else:
                result.append(node.member)
            node = node.backward
            count -= 1

        return result

    def zcount(self, min_score: float, max_score: float) -> int:
        """Count elements with score between min_score and max_score inclusive."""
        count = 0
        for s in self._dict.values():
            if min_score <= s <= max_score:
                count += 1
        return count
