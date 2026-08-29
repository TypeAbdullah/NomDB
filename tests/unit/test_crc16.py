"""
Unit tests for CRC16 hash slot algorithm and hash tag extraction.
"""

from nomdb.cluster.crc16 import crc16
from nomdb.cluster.slots import extract_hash_tag, key_to_slot, TOTAL_SLOTS


def test_crc16_known_values():
    assert crc16(b"123456789") == 0x31C3
    assert crc16(b"") == 0x0000


def test_hash_tag_extraction():
    assert extract_hash_tag(b"user:{1000}:profile") == b"1000"
    assert extract_hash_tag(b"user:{1000}:settings") == b"1000"
    assert extract_hash_tag(b"no_tags_here") == b"no_tags_here"
    assert extract_hash_tag(b"empty:{}tag") == b"empty:{}tag"


def test_key_to_slot_colocation():
    slot1 = key_to_slot(b"user:{1000}:profile")
    slot2 = key_to_slot(b"user:{1000}:settings")
    assert 0 <= slot1 < TOTAL_SLOTS
    assert slot1 == slot2
