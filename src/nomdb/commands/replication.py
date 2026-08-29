"""
Replication commands for NomDB (REPLCONF, PSYNC, SYNC, REPLICAOF).
"""

from __future__ import annotations
from typing import Any, List
from nomdb.commands.base import BaseCommand, CommandContext
from nomdb.protocol.exceptions import NomDBError, SyntaxError
from nomdb.protocol.resp import OK, SimpleString, NO_REPLY


class ReplConfCommand(BaseCommand):
    name = "REPLCONF"
    arity = -3  # REPLCONF listening-port <port> | REPLCONF ACK <offset>
    is_write = False
    complexity = "O(1)"
    description = "Configure replication parameters and acknowledge offset."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        subcmd = args[0].decode("utf-8", errors="replace").upper()
        if subcmd == "LISTENING-PORT":
            try:
                port = int(args[1])
                info = ctx.server.primary_replication.register_replica(ctx.connection)
                info.listening_port = port
            except ValueError:
                raise NomDBError("invalid port")
            return OK

        elif subcmd == "ACK":
            try:
                offset = int(args[1])
                ctx.server.primary_replication.update_replica_ack(ctx.connection, offset)
            except ValueError:
                pass
            return NO_REPLY  # ACK requires no return response

        elif subcmd == "GETACK":
            # Primary requests ACK from replica
            return [b"REPLCONF", b"ACK", str(ctx.server.primary_replication.master_offset).encode("ascii")]

        return OK


class PSyncCommand(BaseCommand):
    name = "PSYNC"
    arity = 3  # PSYNC replid offset
    is_write = False
    complexity = "O(N)"
    description = "Initiate synchronization with primary."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        replid = args[0].decode("utf-8", errors="replace")
        try:
            offset = int(args[1])
        except ValueError:
            offset = -1

        raw_sync_payload = ctx.server.primary_replication.handle_psync(
            ctx.connection, replid, offset, ctx.server.db_manager
        )
        ctx.connection.send_raw(raw_sync_payload)
        return NO_REPLY  # Response already sent directly as raw stream


class SyncCommand(BaseCommand):
    name = "SYNC"
    arity = 1
    is_write = False
    complexity = "O(N)"
    description = "Full synchronization with primary (legacy)."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        raw_sync_payload = ctx.server.primary_replication.handle_psync(
            ctx.connection, "?", -1, ctx.server.db_manager
        )
        ctx.connection.send_raw(raw_sync_payload)
        return NO_REPLY


class ReplicaOfCommand(BaseCommand):
    name = "REPLICAOF"
    arity = 3  # REPLICAOF host port | REPLICAOF NO ONE
    is_write = False
    is_admin = True
    complexity = "O(1)"
    description = "Make the server a replica of another instance, or promote it as master."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        host = args[0].decode("utf-8", errors="replace")
        port_str = args[1].decode("utf-8", errors="replace")

        if host.upper() == "NO" and port_str.upper() == "ONE":
            # Turn into master
            if ctx.server.replica_manager:
                ctx.server.replica_manager.stop()
                ctx.server.replica_manager = None
            ctx.server.settings.replica_of_host = None
            ctx.server.settings.replica_of_port = None
            return OK
        else:
            try:
                port = int(port_str)
            except ValueError:
                raise NomDBError("invalid port")
            ctx.server.set_replica_of(host, port)
            return OK


class SlaveOfCommand(ReplicaOfCommand):
    name = "SLAVEOF"
