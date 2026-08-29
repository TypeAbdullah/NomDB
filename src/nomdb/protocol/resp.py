"""
RESP (Redis Serialization Protocol) data types and constants.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Sequence, Union

CRLF = b"\r\n"
CRLF_LEN = 2

# RESP Type Prefixes
PREFIX_SIMPLE_STRING = ord(b"+")
PREFIX_ERROR = ord(b"-")
PREFIX_INTEGER = ord(b":")
PREFIX_BULK_STRING = ord(b"$")
PREFIX_ARRAY = ord(b"*")
PREFIX_NULL = ord(b"_")
PREFIX_BOOLEAN = ord(b"#")
PREFIX_DOUBLE = ord(b",")
PREFIX_MAP = ord(b"%")
PREFIX_SET = ord(b"~")


@dataclass(frozen=True, slots=True)
class SimpleString:
    value: str

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SimpleString):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        if isinstance(other, bytes):
            return self.value.encode("utf-8") == other
        return False


@dataclass(frozen=True, slots=True)
class ErrorResponse:
    message: str
    prefix: str = "ERR"

    def __str__(self) -> str:
        if self.prefix and not self.message.startswith(self.prefix):
            return f"{self.prefix} {self.message}"
        return self.message

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ErrorResponse):
            return self.message == other.message and self.prefix == other.prefix
        if isinstance(other, str):
            return str(self) == other or self.message == other
        if isinstance(other, bytes):
            return str(self).encode("utf-8") == other or self.message.encode("utf-8") == other
        return False


@dataclass(frozen=True, slots=True)
class IntegerResponse:
    value: int

    def __int__(self) -> int:
        return self.value

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, IntegerResponse):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        return False


@dataclass(frozen=True, slots=True)
class BulkString:
    value: bytes | None

    def __bytes__(self) -> bytes:
        return self.value or b""

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, BulkString):
            return self.value == other.value
        if isinstance(other, bytes):
            return self.value == other
        if isinstance(other, str) and self.value is not None:
            return self.value.decode("utf-8", errors="replace") == other
        return False


@dataclass(frozen=True, slots=True)
class ArrayResponse:
    items: Sequence[Any] | None


class _NoReplySentinel:
    """Sentinel indicating no response should be sent over socket."""
    pass


NO_REPLY = _NoReplySentinel()

# Null sentinel
NULL = None
NULL_BULK_STRING = b"$-1\r\n"
NULL_ARRAY = b"*-1\r\n"
OK = SimpleString("OK")
PONG = SimpleString("PONG")
QUEUED = SimpleString("QUEUED")
