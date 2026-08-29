"""
Hash data type operations.
Maps string fields to string values within a key.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from nomdb.protocol.exceptions import NomDBError


class HashStore:
    """Internal dictionary wrapper for hash structures."""

    def __init__(self, initial_data: Optional[Dict[bytes, bytes]] = None):
        self._fields: Dict[bytes, bytes] = dict(initial_data) if initial_data else {}

    @property
    def fields(self) -> Dict[bytes, bytes]:
        return self._fields

    def hset(self, field_values: List[Tuple[bytes, bytes]]) -> int:
        """Set field(s) in hash. Returns count of newly added fields."""
        added = 0
        for f, v in field_values:
            if f not in self._fields:
                added += 1
            self._fields[f] = v
        return added

    def hget(self, field: bytes) -> Optional[bytes]:
        return self._fields.get(field)

    def hmget(self, fields: List[bytes]) -> List[Optional[bytes]]:
        return [self._fields.get(f) for f in fields]

    def hdel(self, fields: List[bytes]) -> int:
        deleted = 0
        for f in fields:
            if f in self._fields:
                del self._fields[f]
                deleted += 1
        return deleted

    def hexists(self, field: bytes) -> bool:
        return field in self._fields

    def hgetall(self) -> Dict[bytes, bytes]:
        return self._fields.copy()

    def hkeys(self) -> List[bytes]:
        return list(self._fields.keys())

    def hvals(self) -> List[bytes]:
        return list(self._fields.values())

    def hlen(self) -> int:
        return len(self._fields)

    def hincrby(self, field: bytes, delta: int) -> int:
        curr = self._fields.get(field)
        if curr is None:
            new_val = delta
        else:
            try:
                new_val = int(curr.decode("ascii")) + delta
            except (ValueError, UnicodeDecodeError):
                raise NomDBError("hash value is not an integer")
        self._fields[field] = str(new_val).encode("ascii")
        return new_val

    def hincrbyfloat(self, field: bytes, delta: float) -> float:
        curr = self._fields.get(field)
        if curr is None:
            new_val = delta
        else:
            try:
                new_val = float(curr.decode("ascii")) + delta
            except (ValueError, UnicodeDecodeError):
                raise NomDBError("hash value is not a valid float")
        if new_val.is_integer():
            formatted = f"{int(new_val)}"
        else:
            formatted = f"{new_val:g}"
        self._fields[field] = formatted.encode("ascii")
        return new_val
