from __future__ import annotations
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from nomdb.storage.database import DatabaseManager
from nomdb.storage.entry import DataType
from nomdb.storage.datatypes import HashStore, ListStore, SetStore, SortedSetStore
from nomdb.persistence.snapshot import SnapshotManager
from nomdb.expiration.manager import ExpirationManager
from nomdb.memory.tracker import MemoryTracker
from nomdb.protocol.exceptions import NomDBError, WrongTypeError


class NomDB:
    def __init__(self, path: Optional[Union[str, Path]] = None, auto_save: bool = True):
        self.path = Path(path) if path else Path("./nomdb.nom")
        self.auto_save = auto_save
        self.db_manager = DatabaseManager(16)
        self.keyspace = self.db_manager.get_database(0)
        self.snapshot_manager = SnapshotManager(self.path, enabled=bool(path))
        self.expiration_manager = ExpirationManager(self.db_manager)
        self.memory_tracker = MemoryTracker(self.db_manager)

        if self.path and self.path.exists():
            try:
                self.snapshot_manager.load(self.db_manager)
            except Exception:
                pass

    def _maybe_save(self) -> None:
        if self.auto_save and self.path:
            self.snapshot_manager.save(self.db_manager)

    # String operations
    def set(self, key: str, value: Any, ex: Optional[int] = None, px: Optional[int] = None) -> bool:
        k = key.encode("utf-8") if isinstance(key, str) else key
        v = value.encode("utf-8") if isinstance(value, str) else (value if isinstance(value, bytes) else str(value).encode("utf-8"))
        exp_ms = None
        now_ms = int(time.time() * 1000)
        if ex:
            exp_ms = now_ms + (ex * 1000)
        elif px:
            exp_ms = now_ms + px

        self.keyspace.set(k, DataType.STRING, v, expire_at_ms=exp_ms)
        self._maybe_save()
        return True

    def get(self, key: str) -> Optional[bytes]:
        k = key.encode("utf-8") if isinstance(key, str) else key
        entry = self.keyspace.get_typed_entry(k, DataType.STRING)
        return entry.value if entry else None

    def get_str(self, key: str) -> Optional[str]:
        val = self.get(key)
        return val.decode("utf-8", errors="replace") if val is not None else None

    def delete(self, *keys: str) -> int:
        b_keys = [k.encode("utf-8") if isinstance(k, str) else k for k in keys]
        count = self.keyspace.delete(*b_keys)
        self._maybe_save()
        return count

    def exists(self, *keys: str) -> int:
        b_keys = [k.encode("utf-8") if isinstance(k, str) else k for k in keys]
        return sum(1 for k in b_keys if self.keyspace.exists(k))

    def incr(self, key: str, amount: int = 1) -> int:
        k = key.encode("utf-8") if isinstance(key, str) else key
        entry = self.keyspace.get_typed_entry(k, DataType.STRING)
        curr = entry.value if entry else None
        if curr is None:
            new_val = amount
        else:
            new_val = int(curr.decode("ascii")) + amount
        new_bytes = str(new_val).encode("ascii")
        self.keyspace.set(k, DataType.STRING, new_bytes, expire_at_ms=entry.expire_at_ms if entry else None)
        self._maybe_save()
        return new_val

    def decr(self, key: str, amount: int = 1) -> int:
        return self.incr(key, -amount)

    # Hash operations
    def hset(self, key: str, field: Optional[str] = None, value: Optional[Any] = None, mapping: Optional[Dict[str, Any]] = None) -> int:
        k = key.encode("utf-8") if isinstance(key, str) else key
        entry = self.keyspace.get_typed_entry(k, DataType.HASH)
        if entry is None:
            store = HashStore()
            self.keyspace.set(k, DataType.HASH, store)
        else:
            store = entry.value

        pairs = []
        if mapping:
            for f, v in mapping.items():
                bf = f.encode("utf-8") if isinstance(f, str) else f
                bv = v.encode("utf-8") if isinstance(v, str) else (v if isinstance(v, bytes) else str(v).encode("utf-8"))
                pairs.append((bf, bv))
        elif field is not None and value is not None:
            bf = field.encode("utf-8") if isinstance(field, str) else field
            bv = value.encode("utf-8") if isinstance(value, str) else (value if isinstance(value, bytes) else str(value).encode("utf-8"))
            pairs.append((bf, bv))

        res = store.hset(pairs)
        self._maybe_save()
        return res

    def hget(self, key: str, field: str) -> Optional[bytes]:
        k = key.encode("utf-8") if isinstance(key, str) else key
        bf = field.encode("utf-8") if isinstance(field, str) else field
        entry = self.keyspace.get_typed_entry(k, DataType.HASH)
        if entry is None:
            return None
        return entry.value.hget(bf)

    def hgetall(self, key: str) -> Dict[str, str]:
        k = key.encode("utf-8") if isinstance(key, str) else key
        entry = self.keyspace.get_typed_entry(k, DataType.HASH)
        if entry is None:
            return {}
        return {f.decode("utf-8", errors="replace"): v.decode("utf-8", errors="replace") for f, v in entry.value.fields.items()}

    def hdel(self, key: str, *fields: str) -> int:
        k = key.encode("utf-8") if isinstance(key, str) else key
        b_fields = [f.encode("utf-8") if isinstance(f, str) else f for f in fields]
        entry = self.keyspace.get_typed_entry(k, DataType.HASH)
        if entry is None:
            return 0
        res = entry.value.hdel(b_fields)
        self._maybe_save()
        return res

    # List operations
    def lpush(self, key: str, *values: Any) -> int:
        k = key.encode("utf-8") if isinstance(key, str) else key
        b_vals = [v.encode("utf-8") if isinstance(v, str) else (v if isinstance(v, bytes) else str(v).encode("utf-8")) for v in values]
        entry = self.keyspace.get_typed_entry(k, DataType.LIST)
        if entry is None:
            store = ListStore()
            self.keyspace.set(k, DataType.LIST, store)
        else:
            store = entry.value
        res = store.lpush(b_vals)
        self._maybe_save()
        return res

    def rpush(self, key: str, *values: Any) -> int:
        k = key.encode("utf-8") if isinstance(key, str) else key
        b_vals = [v.encode("utf-8") if isinstance(v, str) else (v if isinstance(v, bytes) else str(v).encode("utf-8")) for v in values]
        entry = self.keyspace.get_typed_entry(k, DataType.LIST)
        if entry is None:
            store = ListStore()
            self.keyspace.set(k, DataType.LIST, store)
        else:
            store = entry.value
        res = store.rpush(b_vals)
        self._maybe_save()
        return res

    def lpop(self, key: str) -> Optional[bytes]:
        k = key.encode("utf-8") if isinstance(key, str) else key
        entry = self.keyspace.get_typed_entry(k, DataType.LIST)
        if entry is None:
            return None
        popped = entry.value.lpop(1)
        self._maybe_save()
        return popped[0] if popped else None

    def rpop(self, key: str) -> Optional[bytes]:
        k = key.encode("utf-8") if isinstance(key, str) else key
        entry = self.keyspace.get_typed_entry(k, DataType.LIST)
        if entry is None:
            return None
        popped = entry.value.rpop(1)
        self._maybe_save()
        return popped[0] if popped else None

    def lrange(self, key: str, start: int = 0, stop: int = -1) -> List[str]:
        k = key.encode("utf-8") if isinstance(key, str) else key
        entry = self.keyspace.get_typed_entry(k, DataType.LIST)
        if entry is None:
            return []
        items = entry.value.lrange(start, stop)
        return [item.decode("utf-8", errors="replace") for item in items]

    # Set operations
    def sadd(self, key: str, *members: Any) -> int:
        k = key.encode("utf-8") if isinstance(key, str) else key
        b_mems = [m.encode("utf-8") if isinstance(m, str) else (m if isinstance(m, bytes) else str(m).encode("utf-8")) for m in members]
        entry = self.keyspace.get_typed_entry(k, DataType.SET)
        if entry is None:
            store = SetStore()
            self.keyspace.set(k, DataType.SET, store)
        else:
            store = entry.value
        res = store.sadd(b_mems)
        self._maybe_save()
        return res

    def smembers(self, key: str) -> List[str]:
        k = key.encode("utf-8") if isinstance(key, str) else key
        entry = self.keyspace.get_typed_entry(k, DataType.SET)
        if entry is None:
            return []
        return [m.decode("utf-8", errors="replace") for m in entry.value.smembers()]

    def sismember(self, key: str, member: Any) -> bool:
        k = key.encode("utf-8") if isinstance(key, str) else key
        bm = member.encode("utf-8") if isinstance(member, str) else member
        entry = self.keyspace.get_typed_entry(k, DataType.SET)
        if entry is None:
            return False
        return entry.value.sismember(bm)

    # Sorted Set operations
    def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        k = key.encode("utf-8") if isinstance(key, str) else key
        pairs = [(float(score), m.encode("utf-8") if isinstance(m, str) else m) for m, score in mapping.items()]
        entry = self.keyspace.get_typed_entry(k, DataType.ZSET)
        if entry is None:
            store = SortedSetStore()
            self.keyspace.set(k, DataType.ZSET, store)
        else:
            store = entry.value
        res = store.zadd(pairs)
        self._maybe_save()
        return res

    def zrange(self, key: str, start: int = 0, stop: int = -1, with_scores: bool = False) -> List[Any]:
        k = key.encode("utf-8") if isinstance(key, str) else key
        entry = self.keyspace.get_typed_entry(k, DataType.ZSET)
        if entry is None:
            return []
        items = entry.value.zrange(start, stop, with_scores=with_scores)
        if with_scores:
            return [(m.decode("utf-8", errors="replace"), score) for m, score in items]
        return [m.decode("utf-8", errors="replace") for m in items]

    def zscore(self, key: str, member: str) -> Optional[float]:
        k = key.encode("utf-8") if isinstance(key, str) else key
        bm = member.encode("utf-8") if isinstance(member, str) else member
        entry = self.keyspace.get_typed_entry(k, DataType.ZSET)
        if entry is None:
            return None
        return entry.value.zscore(bm)

    # General
    def keys(self, pattern: str = "*") -> List[str]:
        b_pat = pattern.encode("utf-8")
        return [k.decode("utf-8", errors="replace") for k in self.keyspace.keys(b_pat)]

    def dbsize(self) -> int:
        return self.keyspace.size()

    def flushdb(self) -> None:
        self.keyspace.flush()
        self._maybe_save()

    def save(self) -> None:
        if self.path:
            self.snapshot_manager.save(self.db_manager)

    def close(self) -> None:
        self.save()


def open_db(path: Optional[Union[str, Path]] = None, auto_save: bool = True) -> NomDB:
    return NomDB(path=path, auto_save=auto_save)
