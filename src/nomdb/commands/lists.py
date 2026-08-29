"""
List data type commands for NomDB.
"""

from __future__ import annotations
from typing import Any, List
from nomdb.commands.base import BaseCommand, CommandContext
from nomdb.protocol.exceptions import NomDBError, SyntaxError, WrongTypeError
from nomdb.protocol.resp import OK, NULL
from nomdb.storage.entry import DataType
from nomdb.storage.datatypes.list_store import ListStore


class LPushCommand(BaseCommand):
    name = "LPUSH"
    arity = -3
    is_write = True
    complexity = "O(1)"
    description = "Prepend one or multiple elements to a list."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        elements = args[1:]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.LIST)
        if entry is None:
            store = ListStore()
            ctx.keyspace.set(key, DataType.LIST, store)
        else:
            store = entry.value

        count = store.lpush(elements)
        ctx.keyspace.mark_modified(key)
        return count


class RPushCommand(BaseCommand):
    name = "RPUSH"
    arity = -3
    is_write = True
    complexity = "O(1)"
    description = "Append one or multiple elements to a list."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        elements = args[1:]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.LIST)
        if entry is None:
            store = ListStore()
            ctx.keyspace.set(key, DataType.LIST, store)
        else:
            store = entry.value

        count = store.rpush(elements)
        ctx.keyspace.mark_modified(key)
        return count


class LPopCommand(BaseCommand):
    name = "LPOP"
    arity = -2  # LPOP key [count]
    is_write = True
    complexity = "O(N)"
    description = "Remove and return the first element(s) of a list."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        count = 1
        has_count_arg = False
        if len(args) > 1:
            try:
                count = int(args[1])
                has_count_arg = True
                if count < 0:
                    raise NomDBError("value is out of range")
            except ValueError:
                raise NomDBError("value is not an integer or out of range")

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.LIST)
        if entry is None:
            return [] if has_count_arg else NULL

        popped = entry.value.lpop(count)
        if entry.value.llen() == 0:
            ctx.keyspace.delete(key)
        else:
            ctx.keyspace.mark_modified(key)

        if not has_count_arg:
            return popped[0] if popped else NULL
        return popped


class RPopCommand(BaseCommand):
    name = "RPOP"
    arity = -2  # RPOP key [count]
    is_write = True
    complexity = "O(N)"
    description = "Remove and return the last element(s) of a list."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        count = 1
        has_count_arg = False
        if len(args) > 1:
            try:
                count = int(args[1])
                has_count_arg = True
                if count < 0:
                    raise NomDBError("value is out of range")
            except ValueError:
                raise NomDBError("value is not an integer or out of range")

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.LIST)
        if entry is None:
            return [] if has_count_arg else NULL

        popped = entry.value.rpop(count)
        if entry.value.llen() == 0:
            ctx.keyspace.delete(key)
        else:
            ctx.keyspace.mark_modified(key)

        if not has_count_arg:
            return popped[0] if popped else NULL
        return popped


class LRangeCommand(BaseCommand):
    name = "LRANGE"
    arity = 4
    is_write = False
    complexity = "O(S+N)"
    description = "Get a range of elements from a list."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        try:
            start = int(args[1])
            stop = int(args[2])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.LIST)
        if entry is None:
            return []
        return entry.value.lrange(start, stop)


class LLenCommand(BaseCommand):
    name = "LLEN"
    arity = 2
    is_write = False
    complexity = "O(1)"
    description = "Get the length of a list."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.LIST)
        if entry is None:
            return 0
        return entry.value.llen()


class LIndexCommand(BaseCommand):
    name = "LINDEX"
    arity = 3
    is_write = False
    complexity = "O(N)"
    description = "Get an element from a list by its index."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        try:
            index = int(args[1])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.LIST)
        if entry is None:
            return NULL
        val = entry.value.lindex(index)
        return val if val is not None else NULL


class LSetCommand(BaseCommand):
    name = "LSET"
    arity = 4
    is_write = True
    complexity = "O(N)"
    description = "Set the value of an element in a list by its index."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        try:
            index = int(args[1])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")
        element = args[2]

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.LIST)
        if entry is None:
            raise NomDBError("no such key")

        entry.value.lset(index, element)
        ctx.keyspace.mark_modified(key)
        return OK


class LInsertCommand(BaseCommand):
    name = "LINSERT"
    arity = 5
    is_write = True
    complexity = "O(N)"
    description = "Insert an element before or after another element in a list."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        where = args[1].decode("utf-8", errors="replace")
        pivot = args[2]
        value = args[3]

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.LIST)
        if entry is None:
            return 0

        length = entry.value.linsert(where, pivot, value)
        if length != -1:
            ctx.keyspace.mark_modified(key)
        return length


class LTrimCommand(BaseCommand):
    name = "LTRIM"
    arity = 4
    is_write = True
    complexity = "O(N)"
    description = "Trim a list to the specified range."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        try:
            start = int(args[1])
            stop = int(args[2])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.LIST)
        if entry is None:
            return OK

        entry.value.ltrim(start, stop)
        if entry.value.llen() == 0:
            ctx.keyspace.delete(key)
        else:
            ctx.keyspace.mark_modified(key)
        return OK


class LRemCommand(BaseCommand):
    name = "LREM"
    arity = 4
    is_write = True
    complexity = "O(N)"
    description = "Remove elements from a list."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        try:
            count = int(args[1])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")
        element = args[2]

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.LIST)
        if entry is None:
            return 0

        removed = entry.value.lrem(count, element)
        if entry.value.llen() == 0:
            ctx.keyspace.delete(key)
        else:
            ctx.keyspace.mark_modified(key)
        return removed
