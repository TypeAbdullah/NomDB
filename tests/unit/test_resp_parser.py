"""
Unit tests for streaming RESP protocol parser.
"""

import pytest
from nomdb.protocol.parser import RESPParser
from nomdb.protocol.resp import SimpleString, ErrorResponse, BulkString
from nomdb.protocol.exceptions import ProtocolError


def test_parse_simple_string():
    parser = RESPParser()
    parser.feed(b"+OK\r\n")
    cmds = parser.get_parsed_commands()
    assert len(cmds) == 1
    assert isinstance(cmds[0], SimpleString)
    assert cmds[0].value == "OK"


def test_parse_error():
    parser = RESPParser()
    parser.feed(b"-ERR unknown command 'FOO'\r\n")
    cmds = parser.get_parsed_commands()
    assert len(cmds) == 1
    assert isinstance(cmds[0], ErrorResponse)
    assert cmds[0].message == "unknown command 'FOO'"


def test_parse_integer():
    parser = RESPParser()
    parser.feed(b":1000\r\n:-42\r\n")
    cmds = parser.get_parsed_commands()
    assert cmds == [1000, -42]


def test_parse_bulk_string():
    parser = RESPParser()
    parser.feed(b"$6\r\nfoobar\r\n$-1\r\n")
    cmds = parser.get_parsed_commands()
    assert cmds == [b"foobar", None]


def test_parse_array():
    parser = RESPParser()
    parser.feed(b"*2\r\n$3\r\nGET\r\n$3\r\nfoo\r\n")
    cmds = parser.get_parsed_commands()
    assert cmds == [[b"GET", b"foo"]]


def test_parse_partial_packet():
    parser = RESPParser()
    # Feed partial bulk string
    parser.feed(b"*2\r\n$3\r\nSET\r\n$5\r\nhe")
    assert parser.get_parsed_commands() == []

    # Feed remainder
    parser.feed(b"llo\r\n")
    cmds = parser.get_parsed_commands()
    assert cmds == [[b"SET", b"hello"]]


def test_parse_pipelined_commands():
    parser = RESPParser()
    # Multiple commands in one TCP chunk
    parser.feed(
        b"*2\r\n$3\r\nGET\r\n$1\r\na\r\n"
        b"*2\r\n$3\r\nGET\r\n$1\r\nb\r\n"
        b"+PONG\r\n"
    )
    cmds = parser.get_parsed_commands()
    assert len(cmds) == 3
    assert cmds[0] == [b"GET", b"a"]
    assert cmds[1] == [b"GET", b"b"]
    assert isinstance(cmds[2], SimpleString)
    assert cmds[2].value == "PONG"


def test_parse_inline_command():
    parser = RESPParser()
    parser.feed(b"PING\r\n")
    cmds = parser.get_parsed_commands()
    assert cmds == [[b"PING"]]
