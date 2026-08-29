"""
Replication Backlog Buffer.
Circular memory buffer holding recent write commands for partial resynchronization (PSYNC).
"""

from __future__ import annotations
import io
from typing import Optional, Tuple


class ReplicationBacklog:
    """Fixed-size circular replication ring buffer."""

    def __init__(self, size: int = 1024 * 1024):
        self.max_size = size
        self._buffer = bytearray(size)
        self.master_offset: int = 0  # Total cumulative bytes written
        self.first_byte_offset: int = 0  # Earliest available byte offset in backlog

    def feed(self, data: bytes) -> None:
        """Write raw RESP command stream into circular buffer."""
        if not data:
            return

        data_len = len(data)
        if data_len >= self.max_size:
            # Data larger than entire backlog; take latest slice
            data = data[-self.max_size:]
            data_len = len(data)
            self._buffer[:data_len] = data
            self.master_offset += data_len
            self.first_byte_offset = self.master_offset - data_len
            return

        idx = self.master_offset % self.max_size
        part1_len = min(data_len, self.max_size - idx)
        part2_len = data_len - part1_len

        self._buffer[idx : idx + part1_len] = data[:part1_len]
        if part2_len > 0:
            self._buffer[:part2_len] = data[part1_len:]

        self.master_offset += data_len
        if self.master_offset - self.first_byte_offset > self.max_size:
            self.first_byte_offset = self.master_offset - self.max_size

    def is_offset_in_backlog(self, offset: int) -> bool:
        """Check if replica's requested offset is still present in backlog."""
        if self.master_offset == 0 and offset == 0:
            return True
        return self.first_byte_offset <= offset <= self.master_offset

    def get_data_since_offset(self, offset: int) -> Optional[bytes]:
        """
        Get all accumulated command bytes from offset up to master_offset.
        Returns None if offset is out of backlog window.
        """
        if not self.is_offset_in_backlog(offset):
            return None

        bytes_needed = self.master_offset - offset
        if bytes_needed == 0:
            return b""

        idx = offset % self.max_size
        part1_len = min(bytes_needed, self.max_size - idx)
        part2_len = bytes_needed - part1_len

        res = bytes(self._buffer[idx : idx + part1_len])
        if part2_len > 0:
            res += bytes(self._buffer[:part2_len])

        return res
