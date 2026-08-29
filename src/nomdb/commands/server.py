"""
Server administration, configuration, authentication, and diagnostic commands for NomDB.
"""

from __future__ import annotations
import asyncio
import time
from typing import Any, List
from nomdb.commands.base import BaseCommand, CommandContext
from nomdb.protocol.exceptions import AuthenticationError, NomDBError, SyntaxError
from nomdb.protocol.resp import OK, PONG, NULL, SimpleString


class PingCommand(BaseCommand):
    name = "PING"
    arity = -1  # PING [message]
    is_write = False
    complexity = "O(1)"
    description = "Ping the server."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        if args:
            return args[0]
        return PONG


class EchoCommand(BaseCommand):
    name = "ECHO"
    arity = 2
    is_write = False
    complexity = "O(1)"
    description = "Echo the given string."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        return args[0]


class InfoCommand(BaseCommand):
    name = "INFO"
    arity = -1  # INFO [section]
    is_write = False
    complexity = "O(1)"
    description = "Get information and statistics about the server."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        section = args[0].decode("utf-8", errors="replace") if args else None
        info_str = ctx.server.metrics.get_info(ctx.server, section)
        return info_str.encode("utf-8")


class ConfigGetCommand(BaseCommand):
    name = "CONFIG"
    arity = -2  # CONFIG GET|SET parameter [value]
    is_write = False
    complexity = "O(N)"
    description = "Get or set NomDB configuration parameters."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        subcmd = args[0].decode("utf-8", errors="replace").upper()
        if subcmd == "GET" and len(args) > 1:
            param = args[1].decode("utf-8", errors="replace").lower()
            if param in ("maxmemory", "*"):
                return [b"maxmemory", str(ctx.server.settings.max_memory_bytes).encode("ascii")]
            if param in ("maxmemory-policy", "*"):
                return [b"maxmemory-policy", ctx.server.settings.max_memory_policy.encode("ascii")]
            if param in ("timeout", "*"):
                return [b"timeout", str(int(ctx.server.settings.timeout_seconds)).encode("ascii")]
            return []
        elif subcmd == "SET" and len(args) > 2:
            param = args[1].decode("utf-8", errors="replace").lower()
            val = args[2].decode("utf-8", errors="replace")
            if param == "maxmemory":
                ctx.server.settings.max_memory_bytes = int(val)
                ctx.server.eviction_manager.max_memory_bytes = int(val)
            elif param == "maxmemory-policy":
                ctx.server.settings.max_memory_policy = val
                ctx.server.eviction_manager.policy = val.lower()
            elif param == "timeout":
                ctx.server.settings.timeout_seconds = float(val)
            return OK
        else:
            raise SyntaxError()


class TimeCommand(BaseCommand):
    name = "TIME"
    arity = 1
    is_write = False
    complexity = "O(1)"
    description = "Return the current server time."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        now = time.time()
        sec = int(now)
        microsec = int((now - sec) * 1_000_000)
        return [str(sec).encode("ascii"), str(microsec).encode("ascii")]


class CommandCommand(BaseCommand):
    name = "COMMAND"
    arity = -1
    is_write = False
    complexity = "O(N)"
    description = "Get array of Redis/NomDB command details."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        if args and args[0].decode("utf-8", errors="replace").upper() == "COUNT":
            return len(ctx.server.registry.all_commands())
        if args and args[0].decode("utf-8", errors="replace").upper() == "DOCS":
            return []
        # Return basic list of registered command names
        return [cmd.name.encode("ascii") for cmd in ctx.server.registry.all_commands()]


class SaveCommand(BaseCommand):
    name = "SAVE"
    arity = 1
    is_write = False
    complexity = "O(N)"
    description = "Synchronously save the dataset to disk (RDB format)."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        ctx.server.snapshot_manager.save(ctx.server.db_manager)
        return OK


class BgSaveCommand(BaseCommand):
    name = "BGSAVE"
    arity = 1
    is_write = False
    complexity = "O(1)"
    description = "Asynchronously save the dataset to disk (RDB format)."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        asyncio.create_task(ctx.server.snapshot_manager.bgsave(ctx.server.db_manager))
        return SimpleString("Background saving started")


class ShutdownCommand(BaseCommand):
    name = "SHUTDOWN"
    arity = -1
    is_write = False
    is_admin = True
    complexity = "O(N)"
    description = "Synchronously save the dataset to disk and then shut down the server."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        # Schedule server shutdown
        asyncio.create_task(ctx.server.shutdown())
        return OK


class AuthCommand(BaseCommand):
    name = "AUTH"
    arity = -2  # AUTH password or AUTH username password
    is_write = False
    complexity = "O(1)"
    description = "Authenticate to the server."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        if not ctx.server.settings.require_auth:
            return OK

        password = args[-1].decode("utf-8", errors="replace")
        if password == ctx.server.settings.password:
            ctx.connection.authenticated = True
            return OK
        else:
            raise NomDBError("invalid password", prefix="ERR")


class MemoryCommand(BaseCommand):
    name = "MEMORY"
    arity = -2  # MEMORY USAGE key | MEMORY STATS
    is_write = False
    complexity = "O(1)"
    description = "Inspect memory usage of keys or the database."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        subcmd = args[0].decode("utf-8", errors="replace").upper()
        if subcmd == "USAGE" and len(args) > 1:
            key = args[1]
            entry = ctx.keyspace.get_entry(key, touch=False)
            if entry is None:
                return NULL
            return ctx.server.memory_tracker.estimate_entry_bytes(key, entry)
        elif subcmd == "STATS":
            stats = ctx.server.memory_tracker.get_memory_stats()
            res = []
            for k, v in stats.items():
                if isinstance(v, (int, str)):
                    res.append(k.encode("utf-8"))
                    res.append(str(v).encode("utf-8"))
            return res
        else:
            raise SyntaxError()


class QuitCommand(BaseCommand):
    name = "QUIT"
    arity = 1
    is_write = False
    complexity = "O(1)"
    description = "Close the connection."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        ctx.connection.should_close = True
        return OK
