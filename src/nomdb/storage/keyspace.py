"""
Keyspace engine for storing, indexing, expiring, and querying key-value entries.
"""

from __future__ import annotations
import fnmatch
import random
import time
from typing import Dict, Iterator, List, Optional, Set, Tuple
from nomdb.protocol.exceptions import WrongTypeError, NoSuchKeyError
from nomdb.storage.entry import DataType, StorageEntry


class Keyspace:
    """Dictionary store of key -> StorageEntry with type enforcement and versioning."""

    def __init__(self):
        self._entries: Dict[bytes, StorageEntry] = {}
        # Version counter per key for optimistic locking (WATCH/EXEC)
        self._key_versions: Dict[bytes, int] = {}
        self._global_version: int = 0

    @property
    def entries(self) -> Dict[bytes, StorageEntry]:
        return self._entries

    def size(self) -> int:
        """Return total active key count."""
        return len(self._entries)

    def mark_modified(self, key: bytes) -> None:
        """Bump modification version for a key."""
        self._global_version += 1
        self._key_versions[key] = self._global_version

    def get_version(self, key: bytes) -> int:
        """Get version of key."""
        return self._key_versions.get(key, 0)

    def exists(self, key: bytes) -> bool:
        entry = self.get_entry(key)
        return entry is not None

    def get_entry(self, key: bytes, touch: bool = True) -> Optional[StorageEntry]:
        """
        Retrieve entry if active. Lazy expires if TTL has passed.
        """
        entry = self._entries.get(key)
        if entry is None:
            return None

        if entry.is_expired():
            self.delete(key)
            return None

        if touch:
            entry.touch()
        return entry

    def get_typed_entry(self, key: bytes, expected_type: DataType, touch: bool = True) -> Optional[StorageEntry]:
        """Get entry verifying that its data_type matches expected_type."""
        entry = self.get_entry(key, touch=touch)
        if entry is None:
            return None
        if entry.data_type != expected_type:
            raise WrongTypeError()
        return entry

    def set(
        self,
        key: bytes,
        data_type: DataType,
        value: Any,
        expire_at_ms: Optional[int] = None,
    ) -> StorageEntry:
        """Set or update key entry."""
        entry = StorageEntry(
            data_type=data_type,
            value=value,
            expire_at_ms=expire_at_ms,
        )
        self._entries[key] = entry
        self.mark_modified(key)
        return entry

    def delete(self, *keys: bytes) -> int:
        """Delete keys. Returns count of deleted keys."""
        deleted = 0
        for k in keys:
            if k in self._entries:
                del self._entries[k]
                self.mark_modified(k)
                deleted += 1
        return deleted

    def expire_at(self, key: bytes, expire_at_ms: int) -> bool:
        """Set absolute expiration time in epoch milliseconds."""
        entry = self.get_entry(key, touch=False)
        if entry is None:
            return False
        if expire_at_ms <= int(time.time() * 1000):
            self.delete(key)
        else:
            entry.expire_at_ms = expire_at_ms
            self.mark_modified(key)
        return True

    def persist(self, key: bytes) -> bool:
        """Remove TTL from key."""
        entry = self.get_entry(key, touch=False)
        if entry is None or entry.expire_at_ms is None:
            return False
        entry.expire_at_ms = None
        self.mark_modified(key)
        return True

    def ttl(self, key: bytes) -> int:
        """Return TTL in seconds (-1 no TTL, -2 non-existent/expired)."""
        entry = self.get_entry(key, touch=False)
        if entry is None:
            return -2
        return entry.ttl_seconds

    def pttl(self, key: bytes) -> int:
        """Return TTL in milliseconds (-1 no TTL, -2 non-existent/expired)."""
        entry = self.get_entry(key, touch=False)
        if entry is None:
            return -2
        return entry.ttl_ms

    def type_str(self, key: bytes) -> str:
        """Return Redis type string or 'none'."""
        entry = self.get_entry(key, touch=False)
        if entry is None:
            return "none"
        return entry.data_type.value

    def rename(self, source: bytes, destination: bytes) -> None:
        """Rename key source to destination."""
        entry = self.get_entry(source, touch=False)
        if entry is None:
            raise NoSuchKeyError()
        self._entries[destination] = entry
        del self._entries[source]
        self.mark_modified(source)
        self.mark_modified(destination)

    def renamenx(self, source: bytes, destination: bytes) -> bool:
        """Rename key if destination does not exist."""
        if self.exists(destination):
            return False
        self.rename(source, destination)
        return True

    def keys(self, pattern: bytes = b"*") -> List[bytes]:
        """Find all keys matching glob pattern (O(N))."""
        pat = pattern.decode("utf-8", errors="replace")
        matched = []
        # Lazy check during iteration
        for k in list(self._entries.keys()):
            if self.get_entry(k, touch=False) is not None:
                if fnmatch.fnmatch(k.decode("utf-8", errors="replace"), pat):
                    matched.append(k)
        return matched

    def scan(self, cursor: int, pattern: Optional[bytes] = None, count: int = 10) -> Tuple[int, List[bytes]]:
        """Cursor-based scan iteration over keyspace."""
        all_keys = list(self._entries.keys())
        total = len(all_keys)
        if total == 0 or cursor >= total:
            return 0, []

        end = min(cursor + count, total)
        batch = all_keys[cursor:end]
        next_cursor = end if end < total else 0

        pat = pattern.decode("utf-8", errors="replace") if pattern else None
        results = []
        for k in batch:
            if self.get_entry(k, touch=False) is not None:
                if pat is None or fnmatch.fnmatch(k.decode("utf-8", errors="replace"), pat):
                    results.append(k)

        return next_cursor, results

    def random_key(self) -> Optional[bytes]:
        """Return a random active key."""
        while self._entries:
            k = random.choice(list(self._entries.keys()))
            if self.get_entry(k, touch=False) is not None:
                return k
        return None

    def flush(self) -> None:
        """Clear all entries."""
        for k in list(self._entries.keys()):
            self.mark_modified(k)
        self._entries.clear()
