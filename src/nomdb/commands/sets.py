"""
Set data type commands for NomDB.
"""

from __future__ import annotations
from typing import Any, List
from nomdb.commands.base import BaseCommand, CommandContext
from nomdb.protocol.exceptions import NomDBError, SyntaxError, WrongTypeError
from nomdb.protocol.resp import OK, NULL
from nomdb.storage.entry import DataType
from nomdb.storage.datatypes.set_store import SetStore


class SAddCommand(BaseCommand):
    name = "SADD"
    arity = -3
    is_write = True
    complexity = "O(N)"
    description = "Add one or more members to a set."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        members = args[1:]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.SET)
        if entry is None:
            store = SetStore()
            ctx.keyspace.set(key, DataType.SET, store)
        else:
            store = entry.value

        added = store.sadd(members)
        ctx.keyspace.mark_modified(key)
        return added


class SRemCommand(BaseCommand):
    name = "SREM"
    arity = -3
    is_write = True
    complexity = "O(N)"
    description = "Remove one or more members from a set."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        members = args[1:]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.SET)
        if entry is None:
            return 0

        removed = entry.value.srem(members)
        if entry.value.scard() == 0:
            ctx.keyspace.delete(key)
        else:
            ctx.keyspace.mark_modified(key)
        return removed


class SIsMemberCommand(BaseCommand):
    name = "SISMEMBER"
    arity = 3
    is_write = False
    complexity = "O(1)"
    description = "Determine if a given value is a member of a set."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        member = args[1]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.SET)
        if entry is None:
            return 0
        return 1 if entry.value.sismember(member) else 0


class SMIsMemberCommand(BaseCommand):
    name = "SMISMEMBER"
    arity = -3
    is_write = False
    complexity = "O(N)"
    description = "Returns whether each member is a member of the set."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        members = args[1:]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.SET)
        if entry is None:
            return [0] * len(members)
        return entry.value.smismember(members)


class SMembersCommand(BaseCommand):
    name = "SMEMBERS"
    arity = 2
    is_write = False
    complexity = "O(N)"
    description = "Get all the members in a set."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.SET)
        if entry is None:
            return []
        return entry.value.smembers()


class SCardCommand(BaseCommand):
    name = "SCARD"
    arity = 2
    is_write = False
    complexity = "O(1)"
    description = "Get the number of members in a set."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.SET)
        if entry is None:
            return 0
        return entry.value.scard()


class SPopCommand(BaseCommand):
    name = "SPOP"
    arity = -2  # SPOP key [count]
    is_write = True
    complexity = "O(N)"
    description = "Remove and return one or multiple random members from a set."

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
        entry = ctx.keyspace.get_typed_entry(key, DataType.SET)
        if entry is None:
            return [] if has_count_arg else NULL

        popped = entry.value.spop(count)
        if entry.value.scard() == 0:
            ctx.keyspace.delete(key)
        else:
            ctx.keyspace.mark_modified(key)

        if not has_count_arg:
            return popped[0] if popped else NULL
        return popped


class SRandMemberCommand(BaseCommand):
    name = "SRANDMEMBER"
    arity = -2  # SRANDMEMBER key [count]
    is_write = False
    complexity = "O(N)"
    description = "Get one or multiple random members from a set."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        count = 1
        has_count_arg = False
        if len(args) > 1:
            try:
                count = int(args[1])
                has_count_arg = True
            except ValueError:
                raise NomDBError("value is not an integer or out of range")

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.SET)
        if entry is None:
            return [] if has_count_arg else NULL

        members = entry.value.srandmember(count)
        if not has_count_arg:
            return members[0] if members else NULL
        return members


class SUnionCommand(BaseCommand):
    name = "SUNION"
    arity = -2
    is_write = False
    complexity = "O(N)"
    description = "Add multiple sets."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        ctx.server.cluster_manager.verify_multi_key_route(args)
        sets = []
        for k in args:
            entry = ctx.keyspace.get_typed_entry(k, DataType.SET)
            if entry is not None:
                sets.append(entry.value)
        return list(SetStore.sunion(sets))


class SInterCommand(BaseCommand):
    name = "SINTER"
    arity = -2
    is_write = False
    complexity = "O(N*M)"
    description = "Intersect multiple sets."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        ctx.server.cluster_manager.verify_multi_key_route(args)
        sets = []
        for k in args:
            entry = ctx.keyspace.get_typed_entry(k, DataType.SET)
            if entry is None:
                return []
            sets.append(entry.value)
        return list(SetStore.sinter(sets))


class SDiffCommand(BaseCommand):
    name = "SDIFF"
    arity = -2
    is_write = False
    complexity = "O(N)"
    description = "Subtract multiple sets."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        ctx.server.cluster_manager.verify_multi_key_route(args)
        first_entry = ctx.keyspace.get_typed_entry(args[0], DataType.SET)
        if first_entry is None:
            return []
        sets = [first_entry.value]
        for k in args[1:]:
            entry = ctx.keyspace.get_typed_entry(k, DataType.SET)
            if entry is not None:
                sets.append(entry.value)
        return list(SetStore.sdiff(sets))
