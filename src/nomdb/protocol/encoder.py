"""
RESP Protocol Encoder.
Serializes Python values into RESP2-compatible byte streams.
"""

from __future__ import annotations
from typing import Any, Sequence
from nomdb.protocol.resp import (
    CRLF,
    SimpleString,
    ErrorResponse,
    IntegerResponse,
    BulkString,
    ArrayResponse,
    NULL_BULK_STRING,
    NULL_ARRAY,
)
from nomdb.protocol.exceptions import NomDBError


class RESPEncoder:
    """High-performance RESP serializer."""

    @classmethod
    def encode(cls, value: Any) -> bytes:
        """Encode arbitrary Python value or RESP structure to bytes."""
        if value is None:
            return NULL_BULK_STRING

        if isinstance(value, SimpleString):
            return b"+" + value.value.encode("utf-8") + CRLF

        if isinstance(value, ErrorResponse):
            msg = str(value)
            return b"-" + msg.encode("utf-8") + CRLF

        if isinstance(value, NomDBError):
            return b"-" + str(value).encode("utf-8") + CRLF

        if isinstance(value, Exception):
            return b"-ERR " + str(value).encode("utf-8") + CRLF

        if isinstance(value, IntegerResponse):
            return b":" + str(value.value).encode("ascii") + CRLF

        if isinstance(value, bool):
            return b":1\r\n" if value else b":0\r\n"

        if isinstance(value, int):
            return b":" + str(value).encode("ascii") + CRLF

        if isinstance(value, float):
            # Redis standard: floats are sent as bulk strings (e.g. INCRBYFLOAT, ZSCORE)
            val_bytes = str(value).encode("ascii")
            return b"$" + str(len(val_bytes)).encode("ascii") + CRLF + val_bytes + CRLF

        if isinstance(value, bytes):
            return b"$" + str(len(value)).encode("ascii") + CRLF + value + CRLF

        if isinstance(value, str):
            encoded = value.encode("utf-8")
            return b"$" + str(len(encoded)).encode("ascii") + CRLF + encoded + CRLF

        if isinstance(value, BulkString):
            if value.value is None:
                return NULL_BULK_STRING
            return b"$" + str(len(value.value)).encode("ascii") + CRLF + value.value + CRLF

        if isinstance(value, ArrayResponse):
            if value.items is None:
                return NULL_ARRAY
            return cls._encode_sequence(value.items)

        if isinstance(value, (list, tuple)):
            return cls._encode_sequence(value)

        if isinstance(value, set):
            return cls._encode_sequence(list(value))

        if isinstance(value, dict):
            # Flatten dict to array of [k1, v1, k2, v2, ...]
            flattened = []
            for k, v in value.items():
                flattened.append(k)
                flattened.append(v)
            return cls._encode_sequence(flattened)

        # Fallback to string representation
        encoded_fallback = str(value).encode("utf-8")
        return b"$" + str(len(encoded_fallback)).encode("ascii") + CRLF + encoded_fallback + CRLF

    @classmethod
    def _encode_sequence(cls, items: Sequence[Any]) -> bytes:
        parts = [b"*" + str(len(items)).encode("ascii") + CRLF]
        for item in items:
            parts.append(cls.encode(item))
        return b"".join(parts)

    @classmethod
    def encode_command(cls, *args: str | bytes | int | float) -> bytes:
        """Helper to encode a client command into RESP array bytes."""
        parts = [b"*" + str(len(args)).encode("ascii") + CRLF]
        for arg in args:
            if isinstance(arg, bytes):
                parts.append(b"$" + str(len(arg)).encode("ascii") + CRLF + arg + CRLF)
            elif isinstance(arg, str):
                encoded = arg.encode("utf-8")
                parts.append(b"$" + str(len(encoded)).encode("ascii") + CRLF + encoded + CRLF)
            elif isinstance(arg, (int, float)):
                encoded = str(arg).encode("ascii")
                parts.append(b"$" + str(len(encoded)).encode("ascii") + CRLF + encoded + CRLF)
            else:
                encoded = str(arg).encode("utf-8")
                parts.append(b"$" + str(len(encoded)).encode("ascii") + CRLF + encoded + CRLF)
        return b"".join(parts)
