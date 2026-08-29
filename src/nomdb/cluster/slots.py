from __future__ import annotations
from nomdb.cluster.crc16 import crc16

TOTAL_SLOTS = 16384

def extract_hash_tag(key: bytes) -> bytes:
    start = key.find(b"{")
    if start != -1:
        end = key.find(b"}", start + 1)
        if end != -1 and end > start + 1:
            return key[start + 1 : end]
    return key

def key_to_slot(key: bytes) -> int:
    tag = extract_hash_tag(key)
    return crc16(tag) % TOTAL_SLOTS
