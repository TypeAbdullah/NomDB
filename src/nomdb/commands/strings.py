"""
String and numeric commands for NomDB.
"""

from __future__ import annotations
import time
from typing import Any, List, Optional
from nomdb.commands.base import BaseCommand, CommandContext
from nomdb.protocol.exceptions import NomDBError, SyntaxError, WrongTypeError
from nomdb.protocol.resp import OK, NULL, SimpleString
from nomdb.storage.entry import DataType, StorageEntry
from nomdb.storage.datatypes.string_store import StringStore


class SetCommand(BaseCommand):
    name = "SET"
    arity = -3  # SET key value [EX|PX|NX|XX|KEEPTTL|GET]
    is_write = True
    complexity = "O(1)"
    description = "Set string value of a key with optional TTL and conditions."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        val = args[1]

        ctx.server.cluster_manager.verify_key_route(key)

        ex_sec: Optional[int] = None
        px_ms: Optional[int] = None
        nx = False
        xx = False
        get_old = False
        keep_ttl = False

        i = 2
        while i < len(args):
            opt = args[i].decode("utf-8", errors="replace").upper()
            if opt == "EX" and i + 1 < len(args):
                try:
                    ex_sec = int(args[i + 1])
                    if ex_sec <= 0:
                        raise NomDBError("invalid expire time in 'set' command")
                except ValueError:
                    raise NomDBError("value is not an integer or out of range")
                i += 2
            elif opt == "PX" and i + 1 < len(args):
                try:
                    px_ms = int(args[i + 1])
                    if px_ms <= 0:
                        raise NomDBError("invalid expire time in 'set' command")
                except ValueError:
                    raise NomDBError("value is not an integer or out of range")
                i += 2
            elif opt == "NX":
                nx = True
                i += 1
            elif opt == "XX":
                xx = True
                i += 1
            elif opt == "GET":
                get_old = True
                i += 1
            elif opt == "KEEPTTL":
                keep_ttl = True
                i += 1
            else:
                raise SyntaxError()

        if nx and xx:
            raise SyntaxError()

        existing = ctx.keyspace.get_entry(key, touch=False)
        old_val = None
        if existing is not None:
            if existing.data_type != DataType.STRING:
                if get_old:
                    raise WrongTypeError()
            else:
                old_val = existing.value

        if nx and existing is not None:
            return old_val if get_old else NULL

        if xx and existing is None:
            return old_val if get_old else NULL

        expire_at_ms = None
        now_ms = int(time.time() * 1000)
        if ex_sec is not None:
            expire_at_ms = now_ms + (ex_sec * 1000)
        elif px_ms is not None:
            expire_at_ms = now_ms + px_ms
        elif keep_ttl and existing is not None:
            expire_at_ms = existing.expire_at_ms

        ctx.server.memory_tracker.get_used_memory()
        ctx.keyspace.set(key, DataType.STRING, val, expire_at_ms=expire_at_ms)

        if expire_at_ms is not None:
            ctx.server.expiration_manager.register_expiration(ctx.db_id, key, expire_at_ms)

        if get_old:
            return old_val
        return OK


class GetCommand(BaseCommand):
    name = "GET"
    arity = 2
    is_write = False
    complexity = "O(1)"
    description = "Get the string value of a key."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.STRING)
        if entry is None:
            ctx.server.metrics.record_miss()
            return NULL
        ctx.server.metrics.record_hit()
        return entry.value


class GetDelCommand(BaseCommand):
    name = "GETDEL"
    arity = 2
    is_write = True
    complexity = "O(1)"
    description = "Get the value of key and delete the key."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.STRING)
        if entry is None:
            return NULL
        val = entry.value
        ctx.keyspace.delete(key)
        return val


class GetExCommand(BaseCommand):
    name = "GETEX"
    arity = -2
    is_write = True
    complexity = "O(1)"
    description = "Get the value of key and optionally set its expiration."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.STRING)
        if entry is None:
            return NULL

        if len(args) > 1:
            opt = args[1].decode("utf-8", errors="replace").upper()
            now_ms = int(time.time() * 1000)
            if opt == "EX" and len(args) > 2:
                sec = int(args[2])
                exp = now_ms + (sec * 1000)
                ctx.keyspace.expire_at(key, exp)
                ctx.server.expiration_manager.register_expiration(ctx.db_id, key, exp)
            elif opt == "PX" and len(args) > 2:
                ms = int(args[2])
                exp = now_ms + ms
                ctx.keyspace.expire_at(key, exp)
                ctx.server.expiration_manager.register_expiration(ctx.db_id, key, exp)
            elif opt == "PERSIST":
                ctx.keyspace.persist(key)
            else:
                raise SyntaxError()

        return entry.value


class GetSetCommand(BaseCommand):
    name = "GETSET"
    arity = 3
    is_write = True
    complexity = "O(1)"
    description = "Set string value of a key and return its old value."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        val = args[1]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.STRING)
        old_val = entry.value if entry is not None else NULL
        ctx.keyspace.set(key, DataType.STRING, val)
        return old_val


class MGetCommand(BaseCommand):
    name = "MGET"
    arity = -2
    is_write = False
    complexity = "O(N)"
    description = "Get values of all given keys."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        ctx.server.cluster_manager.verify_multi_key_route(args)
        results = []
        for key in args:
            entry = ctx.keyspace.get_entry(key)
            if entry is None or entry.data_type != DataType.STRING:
                results.append(NULL)
            else:
                results.append(entry.value)
        return results


class MSetCommand(BaseCommand):
    name = "MSET"
    arity = -3
    is_write = True
    complexity = "O(N)"
    description = "Set multiple keys to multiple values."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        if len(args) % 2 != 0:
            raise SyntaxError("wrong number of arguments for MSET")
        keys = [args[i] for i in range(0, len(args), 2)]
        ctx.server.cluster_manager.verify_multi_key_route(keys)
        for i in range(0, len(args), 2):
            ctx.keyspace.set(args[i], DataType.STRING, args[i + 1])
        return OK


class SetNxCommand(BaseCommand):
    name = "SETNX"
    arity = 3
    is_write = True
    complexity = "O(1)"
    description = "Set key value if key does not exist."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        val = args[1]
        ctx.server.cluster_manager.verify_key_route(key)
        if ctx.keyspace.exists(key):
            return 0
        ctx.keyspace.set(key, DataType.STRING, val)
        return 1


class IncrCommand(BaseCommand):
    name = "INCR"
    arity = 2
    is_write = True
    complexity = "O(1)"
    description = "Increment integer value of a key by one."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.STRING)
        curr = entry.value if entry is not None else None
        new_bytes, new_int = StringStore.incrby(curr, 1)
        ctx.keyspace.set(key, DataType.STRING, new_bytes, expire_at_ms=entry.expire_at_ms if entry else None)
        return new_int


class IncrByCommand(BaseCommand):
    name = "INCRBY"
    arity = 3
    is_write = True
    complexity = "O(1)"
    description = "Increment integer value of a key by given amount."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        try:
            delta = int(args[1])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        entry = ctx.keyspace.get_typed_entry(key, DataType.STRING)
        curr = entry.value if entry is not None else None
        new_bytes, new_int = StringStore.incrby(curr, delta)
        ctx.keyspace.set(key, DataType.STRING, new_bytes, expire_at_ms=entry.expire_at_ms if entry else None)
        return new_int


class IncrByFloatCommand(BaseCommand):
    name = "INCRBYFLOAT"
    arity = 3
    is_write = True
    complexity = "O(1)"
    description = "Increment float value of a key by given amount."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        try:
            delta = float(args[1])
        except ValueError:
            raise NomDBError("value is not a valid float")

        entry = ctx.keyspace.get_typed_entry(key, DataType.STRING)
        curr = entry.value if entry is not None else None
        new_bytes, new_float = StringStore.incrbyfloat(curr, delta)
        ctx.keyspace.set(key, DataType.STRING, new_bytes, expire_at_ms=entry.expire_at_ms if entry else None)
        return new_bytes


class DecrCommand(BaseCommand):
    name = "DECR"
    arity = 2
    is_write = True
    complexity = "O(1)"
    description = "Decrement integer value of a key by one."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.STRING)
        curr = entry.value if entry is not None else None
        new_bytes, new_int = StringStore.incrby(curr, -1)
        ctx.keyspace.set(key, DataType.STRING, new_bytes, expire_at_ms=entry.expire_at_ms if entry else None)
        return new_int


class DecrByCommand(BaseCommand):
    name = "DECRBY"
    arity = 3
    is_write = True
    complexity = "O(1)"
    description = "Decrement integer value of a key by given amount."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        try:
            delta = int(args[1])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        entry = ctx.keyspace.get_typed_entry(key, DataType.STRING)
        curr = entry.value if entry is not None else None
        new_bytes, new_int = StringStore.incrby(curr, -delta)
        ctx.keyspace.set(key, DataType.STRING, new_bytes, expire_at_ms=entry.expire_at_ms if entry else None)
        return new_int


class AppendCommand(BaseCommand):
    name = "APPEND"
    arity = 3
    is_write = True
    complexity = "O(1)"
    description = "Append value to a key."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        val = args[1]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.STRING)
        curr = entry.value if entry is not None else None
        new_bytes, length = StringStore.append(curr, val)
        ctx.keyspace.set(key, DataType.STRING, new_bytes, expire_at_ms=entry.expire_at_ms if entry else None)
        return length


class StrLenCommand(BaseCommand):
    name = "STRLEN"
    arity = 2
    is_write = False
    complexity = "O(1)"
    description = "Get length of the value stored in a key."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.STRING)
        if entry is None:
            return 0
        return len(entry.value)


class SetRangeCommand(BaseCommand):
    name = "SETRANGE"
    arity = 4
    is_write = True
    complexity = "O(1)"
    description = "Overwrite part of a string at key starting at the specified offset."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        offset = int(args[1])
        val = args[2]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.STRING)
        curr = entry.value if entry is not None else None
        new_bytes, length = StringStore.setrange(curr, offset, val)
        ctx.keyspace.set(key, DataType.STRING, new_bytes, expire_at_ms=entry.expire_at_ms if entry else None)
        return length


class GetRangeCommand(BaseCommand):
    name = "GETRANGE"
    arity = 4
    is_write = False
    complexity = "O(N)"
    description = "Get a substring of the string stored at a key."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        start = int(args[1])
        end = int(args[2])
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.STRING)
        curr = entry.value if entry is not None else None
        return StringStore.getrange(curr, start, end)
