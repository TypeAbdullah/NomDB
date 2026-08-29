"""
Keyspace management, TTL, scan, and database selection commands for NomDB.
"""

from __future__ import annotations
import time
from typing import Any, List
from nomdb.commands.base import BaseCommand, CommandContext
from nomdb.protocol.exceptions import NomDBError, SyntaxError, NoSuchKeyError
from nomdb.protocol.resp import OK, NULL, SimpleString


class DelCommand(BaseCommand):
    name = "DEL"
    arity = -2
    is_write = True
    complexity = "O(N)"
    description = "Delete a key."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        ctx.server.cluster_manager.verify_multi_key_route(args)
        return ctx.keyspace.delete(*args)


class ExistsCommand(BaseCommand):
    name = "EXISTS"
    arity = -2
    is_write = False
    complexity = "O(N)"
    description = "Determine if a key exists."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        ctx.server.cluster_manager.verify_multi_key_route(args)
        count = 0
        for k in args:
            if ctx.keyspace.exists(k):
                count += 1
        return count


class ExpireCommand(BaseCommand):
    name = "EXPIRE"
    arity = 3
    is_write = True
    complexity = "O(1)"
    description = "Set a key's time to live in seconds."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        try:
            seconds = int(args[1])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        ctx.server.cluster_manager.verify_key_route(key)
        expire_at_ms = int(time.time() * 1000) + (seconds * 1000)
        success = ctx.keyspace.expire_at(key, expire_at_ms)
        if success:
            ctx.server.expiration_manager.register_expiration(ctx.db_id, key, expire_at_ms)
            return 1
        return 0


class PExpireCommand(BaseCommand):
    name = "PEXPIRE"
    arity = 3
    is_write = True
    complexity = "O(1)"
    description = "Set a key's time to live in milliseconds."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        try:
            ms = int(args[1])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        ctx.server.cluster_manager.verify_key_route(key)
        expire_at_ms = int(time.time() * 1000) + ms
        success = ctx.keyspace.expire_at(key, expire_at_ms)
        if success:
            ctx.server.expiration_manager.register_expiration(ctx.db_id, key, expire_at_ms)
            return 1
        return 0


class ExpireAtCommand(BaseCommand):
    name = "EXPIREAT"
    arity = 3
    is_write = True
    complexity = "O(1)"
    description = "Set the expiration for a key as a UNIX timestamp in seconds."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        try:
            unix_sec = int(args[1])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        ctx.server.cluster_manager.verify_key_route(key)
        expire_at_ms = unix_sec * 1000
        success = ctx.keyspace.expire_at(key, expire_at_ms)
        if success:
            ctx.server.expiration_manager.register_expiration(ctx.db_id, key, expire_at_ms)
            return 1
        return 0


class PExpireAtCommand(BaseCommand):
    name = "PEXPIREAT"
    arity = 3
    is_write = True
    complexity = "O(1)"
    description = "Set the expiration for a key as a UNIX timestamp in milliseconds."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        try:
            unix_ms = int(args[1])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        ctx.server.cluster_manager.verify_key_route(key)
        success = ctx.keyspace.expire_at(key, unix_ms)
        if success:
            ctx.server.expiration_manager.register_expiration(ctx.db_id, key, unix_ms)
            return 1
        return 0


class TtlCommand(BaseCommand):
    name = "TTL"
    arity = 2
    is_write = False
    complexity = "O(1)"
    description = "Get the time to live for a key in seconds."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        return ctx.keyspace.ttl(key)


class PTtlCommand(BaseCommand):
    name = "PTTL"
    arity = 2
    is_write = False
    complexity = "O(1)"
    description = "Get the time to live for a key in milliseconds."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        return ctx.keyspace.pttl(key)


class PersistCommand(BaseCommand):
    name = "PERSIST"
    arity = 2
    is_write = True
    complexity = "O(1)"
    description = "Remove the expiration from a key."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        return 1 if ctx.keyspace.persist(key) else 0


class TypeCommand(BaseCommand):
    name = "TYPE"
    arity = 2
    is_write = False
    complexity = "O(1)"
    description = "Determine the type stored at key."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        return SimpleString(ctx.keyspace.type_str(key))


class RenameCommand(BaseCommand):
    name = "RENAME"
    arity = 3
    is_write = True
    complexity = "O(1)"
    description = "Rename a key."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        src = args[0]
        dst = args[1]
        ctx.server.cluster_manager.verify_multi_key_route([src, dst])
        try:
            ctx.keyspace.rename(src, dst)
        except NoSuchKeyError:
            raise NomDBError("no such key")
        return OK


class RenameNxCommand(BaseCommand):
    name = "RENAMENX"
    arity = 3
    is_write = True
    complexity = "O(1)"
    description = "Rename a key, only if the new key does not exist."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        src = args[0]
        dst = args[1]
        ctx.server.cluster_manager.verify_multi_key_route([src, dst])
        try:
            success = ctx.keyspace.renamenx(src, dst)
            return 1 if success else 0
        except NoSuchKeyError:
            raise NomDBError("no such key")


class KeysCommand(BaseCommand):
    name = "KEYS"
    arity = 2
    is_write = False
    complexity = "O(N)"
    description = "Find all keys matching the given pattern."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        pattern = args[0]
        return ctx.keyspace.keys(pattern)


class ScanCommand(BaseCommand):
    name = "SCAN"
    arity = -2  # SCAN cursor [MATCH pattern] [COUNT count]
    is_write = False
    complexity = "O(1) for every call. O(N) for a complete iteration."
    description = "Incrementally iterate the keys space."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        try:
            cursor = int(args[0])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        pattern = None
        count = 10

        i = 1
        while i < len(args):
            opt = args[i].decode("utf-8", errors="replace").upper()
            if opt == "MATCH" and i + 1 < len(args):
                pattern = args[i + 1]
                i += 2
            elif opt == "COUNT" and i + 1 < len(args):
                try:
                    count = int(args[i + 1])
                except ValueError:
                    raise NomDBError("value is not an integer or out of range")
                i += 2
            else:
                raise SyntaxError()

        next_cursor, keys = ctx.keyspace.scan(cursor, pattern=pattern, count=count)
        return [str(next_cursor).encode("ascii"), keys]


class DBSizeCommand(BaseCommand):
    name = "DBSIZE"
    arity = 1
    is_write = False
    complexity = "O(1)"
    description = "Return the number of keys in the selected database."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        return ctx.keyspace.size()


class RandomKeyCommand(BaseCommand):
    name = "RANDOMKEY"
    arity = 1
    is_write = False
    complexity = "O(1)"
    description = "Return a random key from the keyspace."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        k = ctx.keyspace.random_key()
        return k if k is not None else NULL


class FlushDBCommand(BaseCommand):
    name = "FLUSHDB"
    arity = -1
    is_write = True
    complexity = "O(N)"
    description = "Remove all keys from the current database."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        ctx.keyspace.flush()
        return OK


class FlushAllCommand(BaseCommand):
    name = "FLUSHALL"
    arity = -1
    is_write = True
    complexity = "O(N)"
    description = "Remove all keys from all databases."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        ctx.server.db_manager.flush_all()
        return OK


class SelectCommand(BaseCommand):
    name = "SELECT"
    arity = 2
    is_write = False
    complexity = "O(1)"
    description = "Change the selected database for the current connection."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        try:
            db_id = int(args[0])
            if db_id < 0 or db_id >= ctx.server.settings.databases:
                raise NomDBError("DB index is out of range")
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        ctx.connection.db_id = db_id
        return OK
