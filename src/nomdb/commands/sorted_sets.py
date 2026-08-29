"""
Sorted Set (ZSET) commands for NomDB.
"""

from __future__ import annotations
from typing import Any, List, Tuple
from nomdb.commands.base import BaseCommand, CommandContext
from nomdb.protocol.exceptions import NomDBError, SyntaxError, WrongTypeError
from nomdb.protocol.resp import OK, NULL
from nomdb.storage.entry import DataType
from nomdb.storage.datatypes.sorted_set_store import SortedSetStore


class ZAddCommand(BaseCommand):
    name = "ZADD"
    arity = -4  # ZADD key [NX|XX] [CH] score member [score member ...]
    is_write = True
    complexity = "O(M*log(N))"
    description = "Add one or more members to a sorted set, or update their score."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        nx = False
        xx = False
        ch = False

        i = 1
        while i < len(args):
            flag = args[i].decode("utf-8", errors="replace").upper()
            if flag == "NX":
                nx = True
                i += 1
            elif flag == "XX":
                xx = True
                i += 1
            elif flag == "CH":
                ch = True
                i += 1
            else:
                break

        if (len(args) - i) % 2 != 0 or (len(args) - i) == 0:
            raise SyntaxError("wrong number of arguments for ZADD")

        score_members: List[Tuple[float, bytes]] = []
        while i < len(args):
            try:
                score = float(args[i])
            except ValueError:
                raise NomDBError("value is not a valid float")
            member = args[i + 1]
            score_members.append((score, member))
            i += 2

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.ZSET)
        if entry is None:
            store = SortedSetStore()
            ctx.keyspace.set(key, DataType.ZSET, store)
        else:
            store = entry.value

        count = store.zadd(score_members, nx=nx, xx=xx, ch=ch)
        ctx.keyspace.mark_modified(key)
        return count


class ZRemCommand(BaseCommand):
    name = "ZREM"
    arity = -3
    is_write = True
    complexity = "O(M*log(N))"
    description = "Remove one or more members from a sorted set."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        members = args[1:]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.ZSET)
        if entry is None:
            return 0

        removed = entry.value.zrem(members)
        if entry.value.zcard() == 0:
            ctx.keyspace.delete(key)
        else:
            ctx.keyspace.mark_modified(key)
        return removed


class ZScoreCommand(BaseCommand):
    name = "ZSCORE"
    arity = 3
    is_write = False
    complexity = "O(1)"
    description = "Get the score associated with the given member in a sorted set."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        member = args[1]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.ZSET)
        if entry is None:
            return NULL
        score = entry.value.zscore(member)
        if score is None:
            return NULL
        if score.is_integer():
            formatted = f"{int(score)}"
        else:
            formatted = f"{score:g}"
        return formatted.encode("ascii")


class ZRankCommand(BaseCommand):
    name = "ZRANK"
    arity = 3
    is_write = False
    complexity = "O(log(N))"
    description = "Determine the index of a member in a sorted set, with scores ordered from low to high."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        member = args[1]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.ZSET)
        if entry is None:
            return NULL
        rank = entry.value.zrank(member)
        return rank if rank is not None else NULL


class ZRevRankCommand(BaseCommand):
    name = "ZREVRANK"
    arity = 3
    is_write = False
    complexity = "O(log(N))"
    description = "Determine the index of a member in a sorted set, with scores ordered from high to low."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        member = args[1]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.ZSET)
        if entry is None:
            return NULL
        rank = entry.value.zrevrank(member)
        return rank if rank is not None else NULL


class ZRangeCommand(BaseCommand):
    name = "ZRANGE"
    arity = -4  # ZRANGE key start stop [WITHSCORES]
    is_write = False
    complexity = "O(log(N)+M)"
    description = "Return a range of members in a sorted set, by index."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        try:
            start = int(args[1])
            stop = int(args[2])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        with_scores = False
        if len(args) > 3:
            if args[3].decode("utf-8", errors="replace").upper() == "WITHSCORES":
                with_scores = True
            else:
                raise SyntaxError()

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.ZSET)
        if entry is None:
            return []

        results = entry.value.zrange(start, stop, with_scores=with_scores)
        if with_scores:
            flattened = []
            for m, s in results:
                flattened.append(m)
                formatted = f"{int(s)}" if s.is_integer() else f"{s:g}"
                flattened.append(formatted.encode("ascii"))
            return flattened
        return results


class ZRevRangeCommand(BaseCommand):
    name = "ZREVRANGE"
    arity = -4  # ZREVRANGE key start stop [WITHSCORES]
    is_write = False
    complexity = "O(log(N)+M)"
    description = "Return a range of members in a sorted set, by index, with scores ordered from high to low."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        try:
            start = int(args[1])
            stop = int(args[2])
        except ValueError:
            raise NomDBError("value is not an integer or out of range")

        with_scores = False
        if len(args) > 3:
            if args[3].decode("utf-8", errors="replace").upper() == "WITHSCORES":
                with_scores = True
            else:
                raise SyntaxError()

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.ZSET)
        if entry is None:
            return []

        results = entry.value.zrevrange(start, stop, with_scores=with_scores)
        if with_scores:
            flattened = []
            for m, s in results:
                flattened.append(m)
                formatted = f"{int(s)}" if s.is_integer() else f"{s:g}"
                flattened.append(formatted.encode("ascii"))
            return flattened
        return results


class ZCardCommand(BaseCommand):
    name = "ZCARD"
    arity = 2
    is_write = False
    complexity = "O(1)"
    description = "Get the number of members in a sorted set."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.ZSET)
        if entry is None:
            return 0
        return entry.value.zcard()


class ZCountCommand(BaseCommand):
    name = "ZCOUNT"
    arity = 4
    is_write = False
    complexity = "O(log(N))"
    description = "Count the members in a sorted set with scores within the given values."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        try:
            min_score = float(args[1])
            max_score = float(args[2])
        except ValueError:
            raise NomDBError("min or max is not a float")

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.ZSET)
        if entry is None:
            return 0
        return entry.value.zcount(min_score, max_score)


class ZIncrByCommand(BaseCommand):
    name = "ZINCRBY"
    arity = 4
    is_write = True
    complexity = "O(log(N))"
    description = "Increment the score of a member in a sorted set."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        key = args[0]
        try:
            delta = float(args[1])
        except ValueError:
            raise NomDBError("value is not a valid float")
        member = args[2]

        ctx.server.cluster_manager.verify_key_route(key)
        entry = ctx.keyspace.get_typed_entry(key, DataType.ZSET)
        if entry is None:
            store = SortedSetStore()
            ctx.keyspace.set(key, DataType.ZSET, store)
        else:
            store = entry.value

        new_score = store.zincrby(delta, member)
        ctx.keyspace.mark_modified(key)
        formatted = f"{int(new_score)}" if new_score.is_integer() else f"{new_score:g}"
        return formatted.encode("ascii")
