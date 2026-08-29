"""
Streaming RESP Protocol Parser.
Handles partial packets, pipelined commands, split chunks, inline commands, and malformed inputs.
"""

from __future__ import annotations
from typing import Any, List, Optional, Tuple, Union
from nomdb.protocol.resp import (
    CRLF,
    CRLF_LEN,
    PREFIX_SIMPLE_STRING,
    PREFIX_ERROR,
    PREFIX_INTEGER,
    PREFIX_BULK_STRING,
    PREFIX_ARRAY,
    SimpleString,
    ErrorResponse,
    IntegerResponse,
    BulkString,
    ArrayResponse,
)
from nomdb.protocol.exceptions import ProtocolError


class RESPParser:
    """
    Stateful, streaming RESP parser.
    Maintains internal byte buffer and yields completed parsed objects.
    """

    def __init__(self, max_buffer_size: int = 64 * 1024 * 1024):
        self._buffer = bytearray()
        self._pos = 0
        self._max_buffer_size = max_buffer_size

    def feed(self, data: bytes) -> None:
        """Feed raw bytes from socket into parser buffer."""
        if len(self._buffer) - self._pos + len(data) > self._max_buffer_size:
            raise ProtocolError("Max buffer size exceeded")
        # If consumed part is large, compact buffer
        if self._pos > 65536 and self._pos > len(self._buffer) // 2:
            self._buffer = self._buffer[self._pos:]
            self._pos = 0
        self._buffer.extend(data)

    def get_parsed_commands(self) -> List[Any]:
        """
        Parse and return all completely available commands/objects in the buffer.
        """
        results = []
        while True:
            saved_pos = self._pos
            try:
                obj, complete = self._parse_one()
                if not complete:
                    self._pos = saved_pos
                    break
                results.append(obj)
            except ProtocolError:
                # Re-raise protocol errors to caller for connection handling
                raise
            except Exception as e:
                self._pos = saved_pos
                raise ProtocolError(f"Protocol parsing error: {e}") from e

        # Compact buffer if exhausted
        if self._pos >= len(self._buffer):
            self._buffer.clear()
            self._pos = 0
        elif self._pos > 65536 and self._pos > len(self._buffer) // 2:
            self._buffer = self._buffer[self._pos:]
            self._pos = 0

        return results

    def _find_crlf(self) -> int:
        """Find index of next CRLF from current position."""
        idx = self._buffer.find(b"\r\n", self._pos)
        return idx

    def _read_line(self) -> Tuple[Optional[bytes], bool]:
        """Read bytes up to next CRLF without CRLF."""
        idx = self._find_crlf()
        if idx == -1:
            return None, False
        line = bytes(self._buffer[self._pos:idx])
        self._pos = idx + CRLF_LEN
        return line, True

    def _parse_one(self) -> Tuple[Any, bool]:
        """
        Parse a single RESP entity.
        Returns (result, is_complete).
        """
        if self._pos >= len(self._buffer):
            return None, False

        prefix = self._buffer[self._pos]

        # Simple String: +OK\r\n
        if prefix == PREFIX_SIMPLE_STRING:
            self._pos += 1
            line, complete = self._read_line()
            if not complete:
                return None, False
            return SimpleString(line.decode("utf-8", errors="replace")), True

        # Error: -ERR message\r\n
        if prefix == PREFIX_ERROR:
            self._pos += 1
            line, complete = self._read_line()
            if not complete:
                return None, False
            msg = line.decode("utf-8", errors="replace")
            parts = msg.split(" ", 1)
            prefix_str = parts[0] if len(parts) > 1 else "ERR"
            message_str = parts[1] if len(parts) > 1 else parts[0]
            return ErrorResponse(message=message_str, prefix=prefix_str), True

        # Integer: :1000\r\n
        if prefix == PREFIX_INTEGER:
            self._pos += 1
            line, complete = self._read_line()
            if not complete:
                return None, False
            try:
                val = int(line)
            except ValueError:
                raise ProtocolError(f"Invalid integer value: {line!r}")
            return val, True

        # Bulk String: $6\r\nfoobar\r\n
        if prefix == PREFIX_BULK_STRING:
            self._pos += 1
            line, complete = self._read_line()
            if not complete:
                return None, False
            try:
                length = int(line)
            except ValueError:
                raise ProtocolError(f"Invalid bulk string length: {line!r}")

            if length == -1:
                return None, True  # Null bulk string
            if length < -1:
                raise ProtocolError(f"Negative bulk string length: {length}")

            # Check if we have length + CRLF bytes available
            end_pos = self._pos + length
            if end_pos + CRLF_LEN > len(self._buffer):
                return None, False  # Partial payload

            # Verify terminating CRLF
            if self._buffer[end_pos:end_pos + CRLF_LEN] != b"\r\n":
                raise ProtocolError("Missing CRLF after bulk string payload")

            payload = bytes(self._buffer[self._pos:end_pos])
            self._pos = end_pos + CRLF_LEN
            return payload, True

        # Array: *2\r\n$3\r\nfoo\r\n$3\r\nbar\r\n
        if prefix == PREFIX_ARRAY:
            self._pos += 1
            line, complete = self._read_line()
            if not complete:
                return None, False
            try:
                count = int(line)
            except ValueError:
                raise ProtocolError(f"Invalid array length: {line!r}")

            if count == -1:
                return None, True  # Null array
            if count < -1:
                raise ProtocolError(f"Negative array count: {count}")

            elements = []
            for _ in range(count):
                elem, elem_complete = self._parse_one()
                if not elem_complete:
                    return None, False
                elements.append(elem)
            return elements, True

        # Inline command support (e.g. "PING\r\n" or "SET foo bar\r\n")
        line, complete = self._read_line()
        if not complete:
            return None, False

        # Split inline command by spaces
        raw_parts = line.strip().split()
        if not raw_parts:
            return [], True
        return [part for part in raw_parts], True

    def reset(self) -> None:
        """Reset parser buffer."""
        self._buffer.clear()
        self._pos = 0
