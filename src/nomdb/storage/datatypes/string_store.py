"""
String data type operations.
Stores raw binary bytes and supports string manipulation and atomic numeric increments.
"""

from __future__ import annotations
from typing import Tuple
from nomdb.protocol.exceptions import NomDBError


class StringStore:
    """Operations on binary/string values."""

    @staticmethod
    def incrby(current: bytes | None, delta: int) -> Tuple[bytes, int]:
        """Atomically increment integer value. Returns (new_bytes, new_int_val)."""
        if current is None:
            new_val = delta
        else:
            try:
                # Must be a valid 64-bit integer
                val_str = current.decode("ascii")
                new_val = int(val_str) + delta
            except (ValueError, UnicodeDecodeError):
                raise NomDBError("value is not an integer or out of range")

        new_bytes = str(new_val).encode("ascii")
        return new_bytes, new_val

    @staticmethod
    def incrbyfloat(current: bytes | None, delta: float) -> Tuple[bytes, float]:
        """Atomically increment float value. Returns (new_bytes, new_float_val)."""
        if current is None:
            new_val = delta
        else:
            try:
                val_str = current.decode("ascii")
                new_val = float(val_str) + delta
            except (ValueError, UnicodeDecodeError):
                raise NomDBError("value is not a valid float")

        # Format float nicely without trailing unnecessary zeros if int-like
        if new_val.is_integer():
            formatted = f"{int(new_val)}"
        else:
            formatted = f"{new_val:g}"
        new_bytes = formatted.encode("ascii")
        return new_bytes, new_val

    @staticmethod
    def append(current: bytes | None, value: bytes) -> Tuple[bytes, int]:
        """Append bytes to current value. Returns (new_bytes, new_length)."""
        if current is None:
            new_bytes = value
        else:
            new_bytes = current + value
        return new_bytes, len(new_bytes)

    @staticmethod
    def getrange(current: bytes | None, start: int, end: int) -> bytes:
        """Get substring slice with negative index support."""
        if current is None or len(current) == 0:
            return b""
        n = len(current)
        if start < 0:
            start = max(0, n + start)
        if end < 0:
            end = max(0, n + end)
        if start > end or start >= n:
            return b""
        return current[start : end + 1]

    @staticmethod
    def setrange(current: bytes | None, offset: int, value: bytes) -> Tuple[bytes, int]:
        """Overwrite part of string starting at offset. Returns (new_bytes, new_length)."""
        if offset < 0:
            raise NomDBError("offset is out of range")
        curr = current or b""
        if offset > len(curr):
            # Pad with null bytes
            curr = curr + (b"\x00" * (offset - len(curr)))
        new_bytes = curr[:offset] + value + curr[offset + len(value):]
        return new_bytes, len(new_bytes)
