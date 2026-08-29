"""
Hash data type commands for NomDB.
"""

from __future__ import annotations
from typing import Any, List
from nomdb.commands.base import BaseCommand, CommandContext
from nomdb.protocol.exceptions import NomDBError, SyntaxError, WrongTypeError
from nomdb.protocol.resp import OK, NULL
from nomdb.storage.entry import DataType
from nomdb.storage.datatypes.hash_store import HashStore


class HSetCommand(BaseCommand):
    name = "HSET"
    arity = -4  # HSET key field value [field value ...]
    is_write = True
    complexity = "O(N)"
    description = "Set string value of a hash field."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        field_args = args[1:]
        if len(field_args) % 2 != 0:
            raise SyntaxError("wrong number of arguments for HSET")

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.HASH)
        if entry is None:
            store = HashStore()
            ctx.keyspace.set(key, DataType.HASH, store)
        else:
            store = entry.value

        pairs = [(field_args[i], field_args[i + 1]) for i in range(0, len(field_args), 2)]
        added = store.hset(pairs)
        ctx.keyspace.mark_modified(key)
        return added


class HGetCommand(BaseCommand):
    name = "HGET"
    arity = 3
    is_write = False
    complexity = "O(1)"
    description = "Get value of a hash field."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        field = args[1]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.HASH)
        if entry is None:
            ctx.server.metrics.record_miss()
            return NULL
        val = entry.value.hget(field)
        if val is None:
            ctx.server.metrics.record_miss()
            return NULL
        ctx.server.metrics.record_hit()
        return val


class HMGetCommand(BaseCommand):
    name = "HMGET"
    arity = -3
    is_write = False
    complexity = "O(N)"
    description = "Get values of all given hash fields."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        fields = args[1:]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.HASH)
        if entry is None:
            return [NULL] * len(fields)
        return [entry.value.hget(f) if entry.value.hget(f) is not None else NULL for f in fields]


class HDelCommand(BaseCommand):
    name = "HDEL"
    arity = -3
    is_write = True
    complexity = "O(N)"
    description = "Delete one or more hash fields."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        fields = args[1:]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.HASH)
        if entry is None:
            return 0
        deleted = entry.value.hdel(fields)
        if entry.value.hlen() == 0:
            ctx.keyspace.delete(key)
        else:
            ctx.keyspace.mark_modified(key)
        return deleted


class HExistsCommand(BaseCommand):
    name = "HEXISTS"
    arity = 3
    is_write = False
    complexity = "O(1)"
    description = "Determine if a hash field exists."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        field = args[1]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.HASH)
        if entry is None:
            return 0
        return 1 if entry.value.hexists(field) else 0


class HGetAllCommand(BaseCommand):
    name = "HGETALL"
    arity = 2
    is_write = False
    complexity = "O(N)"
    description = "Get all fields and values in a hash."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.HASH)
        if entry is None:
            return []
        items = []
        for f, v in entry.value.fields.items():
            items.append(f)
            items.append(v)
        return items


class HKeysCommand(BaseCommand):
    name = "HKEYS"
    arity = 2
    is_write = False
    complexity = "O(N)"
    description = "Get all fields in a hash."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.HASH)
        if entry is None:
            return []
        return entry.value.hkeys()


class HValsCommand(BaseCommand):
    name = "HVALS"
    arity = 2
    is_write = False
    complexity = "O(N)"
    description = "Get all values in a hash."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.HASH)
        if entry is None:
            return []
        return entry.value.hvals()


class HLenCommand(BaseCommand):
    name = "HLEN"
    arity = 2
    is_write = False
    complexity = "O(1)"
    description = "Get number of fields in a hash."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.HASH)
        if entry is None:
            return 0
        return entry.value.hlen()


class HIncrByCommand(BaseCommand):
    name = "HINCRBY"
    arity = 4
    is_write = True
    complexity = "O(1)"
    description = "Increment integer value of a hash field."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        field = args[1]
        try:
            delta = int(args[2])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.HASH)
        if entry is None:
            store = HashStore()
            ctx.keyspace.set(key, DataType.HASH, store)
        else:
            store = entry.value

        new_val = store.hincrby(field, delta)
        ctx.keyspace.mark_modified(key)
        return new_val


class HIncrByFloatCommand(BaseCommand):
    name = "HINCRBYFLOAT"
    arity = 4
    is_write = True
    complexity = "O(1)"
    description = "Increment float value of a hash field."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        field = args[1]
        try:
            delta = float(args[2])
        except ValueError:
            raise NomDBError("value is not a valid float")

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.HASH)
        if entry is None:
            store = HashStore()
            ctx.keyspace.set(key, DataType.HASH, store)
        else:
            store = entry.value

        new_val = store.hincrbyfloat(field, delta)
        ctx.keyspace.mark_modified(key)
        return str(new_val).encode("ascii")


class HSetNxCommand(BaseCommand):
    name = "HSETNX"
    arity = 4
    is_write = True
    complexity = "O(1)"
    description = "Set string value of a hash field, only if the field does not exist."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        field = args[1]
        val = args[2]

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.HASH)
        if entry is None:
            store = HashStore()
            ctx.keyspace.set(key, DataType.HASH, store)
        else:
            store = entry.value

        if store.hexists(field):
            return 0

        store.hset([(field, val)])
        ctx.keyspace.mark_modified(key)
        return 1
