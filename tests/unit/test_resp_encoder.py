"""
Unit tests for RESP serializer / encoder.
"""

from nomdb.protocol.encoder import RESPEncoder
from nomdb.protocol.resp import SimpleString, ErrorResponse, OK, PONG, NULL_BULK_STRING, NULL_ARRAY


def test_encode_simple_string():
    assert RESPEncoder.encode(SimpleString("OK")) == b"+OK\r\n"
    assert RESPEncoder.encode(OK) == b"+OK\r\n"
    assert RESPEncoder.encode(PONG) == b"+PONG\r\n"


def test_encode_error():
    assert RESPEncoder.encode(ErrorResponse("unknown command")) == b"-ERR unknown command\r\n"


def test_encode_integer():
    assert RESPEncoder.encode(100) == b":100\r\n"
    assert RESPEncoder.encode(-42) == b":-42\r\n"
    assert RESPEncoder.encode(True) == b":1\r\n"
    assert RESPEncoder.encode(False) == b":0\r\n"


def test_encode_bulk_string():
    assert RESPEncoder.encode(b"hello") == b"$5\r\nhello\r\n"
    assert RESPEncoder.encode("world") == b"$5\r\nworld\r\n"
    assert RESPEncoder.encode(None) == NULL_BULK_STRING


def test_encode_array():
    assert RESPEncoder.encode(["SET", "foo", "bar"]) == (
        b"*3\r\n"
        b"$3\r\nSET\r\n"
        b"$3\r\nfoo\r\n"
        b"$3\r\nbar\r\n"
    )
    assert RESPEncoder.encode([]) == b"*0\r\n"


def test_encode_nested():
    nested = ["parent", ["child1", "child2"]]
    encoded = RESPEncoder.encode(nested)
    assert encoded == (
        b"*2\r\n"
        b"$6\r\nparent\r\n"
        b"*2\r\n"
        b"$6\r\nchild1\r\n"
        b"$6\r\nchild2\r\n"
    )
