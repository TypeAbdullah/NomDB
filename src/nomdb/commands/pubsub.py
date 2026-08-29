from __future__ import annotations
from typing import Any, List
from nomdb.commands.base import BaseCommand, CommandContext
from nomdb.protocol.resp import NO_REPLY

class SubscribeCommand(BaseCommand):
    name = "SUBSCRIBE"
    arity = -2
    is_write = False
    is_pubsub = True
    complexity = "O(N)"
    description = "Listen for messages published to the given channels."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        subs = ctx.server.pubsub_broker.subscribe(ctx.connection, args)
        for ch, count in subs:
            ctx.connection.send_response([b"subscribe", ch, count])
        return NO_REPLY

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
            ctx.connection.send_response([b"unsubscribe", None, 0])
        else:
            for ch, count in unsubs:
                ctx.connection.send_response([b"unsubscribe", ch, count])
        return NO_REPLY

class PSubscribeCommand(BaseCommand):
    name = "PSUBSCRIBE"
    arity = -2
    is_write = False
    is_pubsub = True
    complexity = "O(N)"
    description = "Listen for messages published to channels matching the given patterns."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        subs = ctx.server.pubsub_broker.psubscribe(ctx.connection, args)
        for pat, count in subs:
            ctx.connection.send_response([b"psubscribe", pat, count])
        return NO_REPLY

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
            ctx.connection.send_response([b"punsubscribe", None, 0])
        else:
            for pat, count in unsubs:
                ctx.connection.send_response([b"punsubscribe", pat, count])
        return NO_REPLY

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
