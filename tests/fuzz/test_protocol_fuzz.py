"""
Fuzz testing for RESP parser to ensure robust crash resilience against malformed inputs.
"""

import os
import random
import pytest
from nomdb.protocol.parser import RESPParser
from nomdb.protocol.exceptions import ProtocolError


def test_fuzz_random_bytes():
    parser = RESPParser()
    for _ in range(500):
        # Generate random bytes of varying lengths
        length = random.randint(1, 2048)
        rand_data = os.urandom(length)
        try:
            parser.feed(rand_data)
            parser.get_parsed_commands()
        except (ProtocolError, Exception):
            parser.reset()


def test_fuzz_malformed_lengths():
    parser = RESPParser()
    malformed_payloads = [
        b"$999999999999999999999999999999\r\n",
        b"$-999\r\n",
        b"*999999999999999999999999999999\r\n",
        b"*-500\r\n",
        b":not_a_number\r\n",
        b"$\r\n",
        b"*\r\n",
        b":\r\n",
        b"+\r\n",
        b"-\r\n",
        b"$5\r\n12345\r\x00\r\n",  # Bad CRLF
    ]

    for payload in malformed_payloads:
        try:
            parser.feed(payload)
            parser.get_parsed_commands()
        except ProtocolError:
            parser.reset()
        except Exception as e:
            pytest.fail(f"Unhandled exception on malformed payload {payload!r}: {e}")
