"""
Hash Slot calculator and Hash Tag extractor for Cluster Mode.
"""

from __future__ import annotations
from nomdb.cluster.crc16 import crc16

TOTAL_SLOTS = 16384


def extract_hash_tag(key: bytes) -> bytes:
    """
    Extract Redis hash tag from key.
    If key contains '{' and '}' and non-empty content between them, returns content.
    Otherwise returns full key.
    """
    start = key.find(b"{")
    if start != -1:
        end = key.find(b"}", start + 1)
        if end != -1 and end > start + 1:
            return key[start + 1 : end]
    return key


def key_to_slot(key: bytes) -> int:
    """Map key (considering hash tags) to 0..16383 hash slot."""
    tag = extract_hash_tag(key)
    return crc16(tag) % TOTAL_SLOTS
