"""
Binary Snapshot (RDB-style) Persistence Engine.
Serializes database state into a compact file with checksum verification.
"""

from __future__ import annotations
import asyncio
import hashlib
import io
import json
import logging
import os
import struct
import time
from pathlib import Path
from typing import Optional
from nomdb.storage.database import DatabaseManager
from nomdb.storage.entry import DataType, StorageEntry
from nomdb.storage.datatypes import HashStore, ListStore, SetStore, SortedSetStore

logger = logging.getLogger("nomdb.persistence.snapshot")

MAGIC_HEADER = b"NOMDB"
VERSION = 1

# Record Type Identifiers
TYPE_STRING = 0
TYPE_HASH = 1
TYPE_LIST = 2
TYPE_SET = 3
TYPE_ZSET = 4

OP_SELECTDB = 254
OP_EXPIRETIME_MS = 253
OP_EOF = 255


class SnapshotManager:
    """Manages creation, background dumping, and loading of snapshots."""

    def __init__(
        self,
        filepath: Path,
        enabled: bool = True,
    ):
        self.filepath = filepath
        self.enabled = enabled
        self.last_save_time = 0.0
        self.is_saving = False

    def save(self, db_manager: DatabaseManager) -> None:
        """Create a point-in-time snapshot synchronously."""
        if not self.enabled:
            return

        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.filepath.with_suffix(".rdb.tmp")

        buf = io.BytesIO()
        # Header: MAGIC + Version (5 + 2 bytes)
        buf.write(MAGIC_HEADER)
        buf.write(struct.pack(">H", VERSION))

        for db_id in range(db_manager._num_databases):
            keyspace = db_manager.get_database(db_id)
            if not keyspace.entries:
                continue

            # Select DB opcode + db_id
            buf.write(struct.pack("B", OP_SELECTDB))
            buf.write(struct.pack(">H", db_id))

            for key, entry in keyspace.entries.items():
                if entry.is_expired():
                    continue

                # Optional Expiration opcode + 8-byte timestamp
                if entry.expire_at_ms is not None:
                    buf.write(struct.pack("B", OP_EXPIRETIME_MS))
                    buf.write(struct.pack(">Q", entry.expire_at_ms))

                # Data type byte + key length + key bytes
                type_byte = self._get_type_byte(entry.data_type)
                buf.write(struct.pack("B", type_byte))
                buf.write(struct.pack(">I", len(key)))
                buf.write(key)

                # Value serialization
                val_bytes = self._serialize_value(entry.data_type, entry.value)
                buf.write(struct.pack(">I", len(val_bytes)))
                buf.write(val_bytes)

        # EOF opcode
        buf.write(struct.pack("B", OP_EOF))

        data = buf.getvalue()
        # Append 32-byte SHA256 checksum
        checksum = hashlib.sha256(data).digest()

        with open(tmp_path, "wb") as f:
            f.write(data)
            f.write(checksum)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, self.filepath)
        self.last_save_time = time.time()

    async def bgsave(self, db_manager: DatabaseManager) -> None:
        """Asynchronously trigger background snapshot creation."""
        if self.is_saving:
            logger.warning("BGSAVE already in progress")
            return

        self.is_saving = True
        try:
            # Run save in asyncio thread pool executor so event loop is not blocked
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.save, db_manager)
            logger.info("Background snapshot (BGSAVE) completed successfully")
        finally:
            self.is_saving = False

    def load(self, db_manager: DatabaseManager) -> bool:
        """Load snapshot file into db_manager. Returns True if loaded, False if not found."""
        if not self.filepath.exists():
            return False

        with open(self.filepath, "rb") as f:
            content = f.read()

        if len(content) < len(MAGIC_HEADER) + 2 + 32:
            raise ValueError("Snapshot file too small or corrupted")

        data, checksum = content[:-32], content[-32:]
        expected_checksum = hashlib.sha256(data).digest()
        if checksum != expected_checksum:
            raise ValueError("Snapshot checksum mismatch - file corrupted")

        buf = io.BytesIO(data)
        magic = buf.read(len(MAGIC_HEADER))
        if magic != MAGIC_HEADER:
            raise ValueError(f"Invalid snapshot magic header: {magic!r}")

        version = struct.unpack(">H", buf.read(2))[0]
        if version > VERSION:
            raise ValueError(f"Unsupported snapshot version: {version}")

        current_db_id = 0
        now = int(time.time() * 1000)

        while True:
            opcode_byte = buf.read(1)
            if not opcode_byte:
                break
            opcode = struct.unpack("B", opcode_byte)[0]

            if opcode == OP_EOF:
                break

            if opcode == OP_SELECTDB:
                current_db_id = struct.unpack(">H", buf.read(2))[0]
                continue

            expire_at_ms = None
            if opcode == OP_EXPIRETIME_MS:
                expire_at_ms = struct.unpack(">Q", buf.read(8))[0]
                type_byte = struct.unpack("B", buf.read(1))[0]
            else:
                type_byte = opcode

            key_len = struct.unpack(">I", buf.read(4))[0]
            key = buf.read(key_len)

            val_len = struct.unpack(">I", buf.read(4))[0]
            val_bytes = buf.read(val_len)

            if expire_at_ms is not None and expire_at_ms <= now:
                continue  # Skip expired entry

            data_type, val_obj = self._deserialize_value(type_byte, val_bytes)
            keyspace = db_manager.get_database(current_db_id)
            keyspace.set(key, data_type, val_obj, expire_at_ms=expire_at_ms)

        self.last_save_time = time.time()
        return True

    @staticmethod
    def _get_type_byte(data_type: DataType) -> int:
        if data_type == DataType.STRING:
            return TYPE_STRING
        if data_type == DataType.HASH:
            return TYPE_HASH
        if data_type == DataType.LIST:
            return TYPE_LIST
        if data_type == DataType.SET:
            return TYPE_SET
        if data_type == DataType.ZSET:
            return TYPE_ZSET
        raise ValueError(f"Unknown data type {data_type}")

    @staticmethod
    def _serialize_value(data_type: DataType, value: Any) -> bytes:
        if data_type == DataType.STRING:
            return value if isinstance(value, bytes) else str(value).encode("utf-8")

        elif data_type == DataType.HASH:
            # JSON-encoded array of [k, v] pairs
            items = [[k.decode("latin1"), v.decode("latin1")] for k, v in value.fields.items()]
            return json.dumps(items).encode("utf-8")

        elif data_type == DataType.LIST:
            items = [item.decode("latin1") for item in value.items]
            return json.dumps(items).encode("utf-8")

        elif data_type == DataType.SET:
            items = [item.decode("latin1") for item in value.members]
            return json.dumps(items).encode("utf-8")

        elif data_type == DataType.ZSET:
            items = [[m.decode("latin1"), s] for m, s in value.dict_index.items()]
            return json.dumps(items).encode("utf-8")

        return b""

    @staticmethod
    def _deserialize_value(type_byte: int, val_bytes: bytes) -> tuple[DataType, Any]:
        if type_byte == TYPE_STRING:
            return DataType.STRING, val_bytes

        elif type_byte == TYPE_HASH:
            items = json.loads(val_bytes.decode("utf-8"))
            store = HashStore({k.encode("latin1"): v.encode("latin1") for k, v in items})
            return DataType.HASH, store

        elif type_byte == TYPE_LIST:
            items = json.loads(val_bytes.decode("utf-8"))
            store = ListStore([x.encode("latin1") for x in items])
            return DataType.LIST, store

        elif type_byte == TYPE_SET:
            items = json.loads(val_bytes.decode("utf-8"))
            store = SetStore({x.encode("latin1") for x in items})
            return DataType.SET, store

        elif type_byte == TYPE_ZSET:
            items = json.loads(val_bytes.decode("utf-8"))
            store = SortedSetStore()
            store.zadd([(score, member.encode("latin1")) for member, score in items])
            return DataType.ZSET, store

        raise ValueError(f"Unknown type byte {type_byte}")
