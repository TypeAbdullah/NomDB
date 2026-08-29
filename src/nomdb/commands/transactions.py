"""
Transaction commands (MULTI, EXEC, DISCARD, WATCH, UNWATCH) for NomDB.
"""

from __future__ import annotations
from typing import Any, List
from nomdb.commands.base import BaseCommand, CommandContext
from nomdb.protocol.exceptions import NomDBError
from nomdb.protocol.resp import OK, NULL, SimpleString


class MultiCommand(BaseCommand):
    name = "MULTI"
    arity = 1
    is_write = False
    complexity = "O(1)"
    description = "Mark the start of a transaction block."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        if ctx.connection.transaction.in_transaction:
            raise NomDBError("MULTI calls can not be nested")
        ctx.connection.transaction.multi()
        return OK


class ExecCommand(BaseCommand):
    name = "EXEC"
    arity = 1
    is_write = True
    complexity = "O(N)"
    description = "Execute all commands issued after MULTI."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        if not ctx.connection.transaction.in_transaction:
            raise NomDBError("EXEC without MULTI")

        # 1. Optimistic locking verification for watched keys
        if not ctx.connection.transaction.check_watched_keys(ctx.server.db_manager):
            ctx.connection.transaction.discard()
            ctx.connection.transaction.unwatch()
            return NULL  # Transaction aborted

        queued = list(ctx.connection.transaction.queued_commands)
        ctx.connection.transaction.discard()
        ctx.connection.transaction.unwatch()

        # 2. Execute queued commands atomically
        results = []
        for cmd_parts in queued:
            res = ctx.server.dispatcher.execute_single_command(ctx.connection, cmd_parts, is_queued_exec=True)
            results.append(res)

        return results


class DiscardCommand(BaseCommand):
    name = "DISCARD"
    arity = 1
    is_write = False
    complexity = "O(1)"
    description = "Discard all commands issued after MULTI."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        if not ctx.connection.transaction.in_transaction:
            raise NomDBError("DISCARD without MULTI")
        ctx.connection.transaction.discard()
        ctx.connection.transaction.unwatch()
        return OK


class WatchCommand(BaseCommand):
    name = "WATCH"
    arity = -2  # WATCH key [key ...]
    is_write = False
    complexity = "O(1)"
    description = "Watch the given keys to determine execution of the MULTI/EXEC block."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        if ctx.connection.transaction.in_transaction:
            raise NomDBError("WATCH inside MULTI is not allowed")

        for key in args:
            version = ctx.keyspace.get_version(key)
            ctx.connection.transaction.watch(ctx.db_id, key, version)
        return OK


class UnwatchCommand(BaseCommand):
    name = "UNWATCH"
    arity = 1
    is_write = False
    complexity = "O(1)"
    description = "Forget about all watched keys."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        ctx.connection.transaction.unwatch()
        return OK
