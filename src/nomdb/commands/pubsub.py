"""
Pub/Sub commands for NomDB.
"""

from __future__ import annotations
from typing import Any, List
from nomdb.commands.base import BaseCommand, CommandContext
from nomdb.protocol.resp import OK


class SubscribeCommand(BaseCommand):
    name = "SUBSCRIBE"
    arity = -2
    is_write = False
    is_pubsub = True
    complexity = "O(N)"
    description = "Listen for messages published to the given channels."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        subs = ctx.server.pubsub_broker.subscribe(ctx.connection, args)
        # In Redis, subscribing produces response array for each channel: ["subscribe", channel, count]
        # First subscription is written to client in dispatcher
        results = []
        for ch, count in subs:
            results.append([b"subscribe", ch, count])
        return results[0] if len(results) == 1 else results


class UnsubscribeCommand(BaseCommand):
    name = "UNSUBSCRIBE"
    arity = -1
    is_write = False
    is_pubsub = True
    complexity = "O(N)"
    description = "Stop listening for messages posted to the given channels."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        unsubs = ctx.server.pubsub_broker.unsubscribe(ctx.connection, args)
        if not unsubs:
            return [b"unsubscribe", None, 0]
        results = []
        for ch, count in unsubs:
            results.append([b"unsubscribe", ch, count])
        return results[0] if len(results) == 1 else results


class PSubscribeCommand(BaseCommand):
    name = "PSUBSCRIBE"
    arity = -2
    is_write = False
    is_pubsub = True
    complexity = "O(N)"
    description = "Listen for messages published to channels matching the given patterns."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        subs = ctx.server.pubsub_broker.psubscribe(ctx.connection, args)
        results = []
        for pat, count in subs:
            results.append([b"psubscribe", pat, count])
        return results[0] if len(results) == 1 else results


class PUnsubscribeCommand(BaseCommand):
    name = "PUNSUBSCRIBE"
    arity = -1
    is_write = False
    is_pubsub = True
    complexity = "O(N)"
    description = "Stop listening for messages posted to channels matching the given patterns."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        unsubs = ctx.server.pubsub_broker.punsubscribe(ctx.connection, args)
        if not unsubs:
            return [b"punsubscribe", None, 0]
        results = []
        for pat, count in unsubs:
            results.append([b"punsubscribe", pat, count])
        return results[0] if len(results) == 1 else results


class PublishCommand(BaseCommand):
    name = "PUBLISH"
    arity = 3
    is_write = False
    complexity = "O(N+M)"
    description = "Post a message to a channel."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        channel = args[0]
        message = args[1]
        receivers = ctx.server.pubsub_broker.publish(channel, message)
        return receivers
