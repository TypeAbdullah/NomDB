"""
Command Dispatcher.
Routes parsed RESP commands through authentication, transaction queueing, eviction, persistence, and replication.
"""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Any, List
from nomdb.commands.base import CommandContext
from nomdb.protocol.exceptions import (
    AuthenticationError,
    NomDBError,
    WrongTypeError,
    MovedError,
    AskError,
    CrossSlotError,
)
from nomdb.protocol.resp import QUEUED, ErrorResponse

if TYPE_CHECKING:
    from nomdb.server.connection import ClientConnection
    from nomdb.server.server import NomDBServer

logger = logging.getLogger("nomdb.server.dispatcher")


class CommandDispatcher:
    """Dispatches command execution and hooks into AOF, eviction, and replication."""

    def __init__(self, server: NomDBServer):
        self.server = server

    def dispatch_command(self, client: ClientConnection, cmd_parts: List[bytes]) -> Any:
        """
        Process single parsed command array from a client.
        Returns the command result or ErrorResponse.
        """
        if not cmd_parts:
            return None

        # Convert first element to uppercase command name string
        first_token = cmd_parts[0]
        cmd_name = (
            first_token.decode("utf-8", errors="replace").upper()
            if isinstance(first_token, bytes)
            else str(first_token).upper()
        )

        args = [
            arg if isinstance(arg, bytes) else str(arg).encode("utf-8")
            for arg in cmd_parts[1:]
        ]

        # 1. Authentication Check
        if not client.authenticated and cmd_name not in ("AUTH", "QUIT", "PING"):
            return AuthenticationError()

        # 2. PubSub Mode Restriction
        if client.is_pubsub and cmd_name not in (
            "SUBSCRIBE", "UNSUBSCRIBE", "PSUBSCRIBE", "PUNSUBSCRIBE", "PING", "QUIT"
        ):
            return NomDBError(
                f"only (P)SUBSCRIBE / (P)UNSUBSCRIBE / PING / QUIT allowed in this context",
                prefix="ERR"
            )

        # 3. Lookup command
        cmd = self.server.registry.get(cmd_name)
        if cmd is None:
            return NomDBError(f"unknown command `{cmd_name}`")

        # 4. Arity validation (total tokens = 1 + len(args))
        if not cmd.validate_arity(1 + len(args)):
            return NomDBError(f"wrong number of arguments for '{cmd_name.lower()}' command")

        # 5. Transaction Queueing
        if client.transaction.in_transaction and cmd_name not in (
            "EXEC", "DISCARD", "MULTI", "WATCH", "UNWATCH", "QUIT"
        ):
            client.transaction.queue_command(cmd_parts)
            return QUEUED

        # 6. Read-Only Replica Check for write commands
        if cmd.is_write and self.server.replica_manager and self.server.settings.replica_read_only:
            return NomDBError("You can't write against a read only replica.", prefix="READONLY")

        # 7. Check maxmemory & Eviction on write commands
        if cmd.is_write:
            try:
                self.server.eviction_manager.check_and_evict()
            except NomDBError as e:
                return e

        # 8. Execute command
        ctx = CommandContext(
            connection=client,
            server=self.server,
            db_id=client.db_id,
            keyspace=self.server.db_manager.get_database(client.db_id),
            raw_args=args,
        )

        try:
            result = cmd.execute(ctx, args)
            self.server.metrics.record_command(cmd_name)

            # 9. If write succeeded, log to AOF and propagate to replicas
            if cmd.is_write:
                normalized_parts = [cmd_name.encode("ascii")] + args
                self.server.aof_manager.append_command(client.db_id, normalized_parts)
                self.server.primary_replication.propagate_write(normalized_parts)

            return result

        except NomDBError as e:
            return e
        except Exception as e:
            logger.error(f"Unexpected error executing command {cmd_name}: {e}", exc_info=True)
            return NomDBError(str(e))

    def execute_single_command(self, client: ClientConnection, cmd_parts: List[bytes], is_queued_exec: bool = False) -> Any:
        """Helper used by EXEC transaction block."""
        return self.dispatch_command(client, cmd_parts)

    def execute_replayed_command(self, db_id: int, cmd_parts: List[bytes]) -> None:
        """
        Execute command during AOF recovery or Replica replication without re-logging or re-propagating.
        """
        if not cmd_parts:
            return

        first_token = cmd_parts[0]
        cmd_name = (
            first_token.decode("utf-8", errors="replace").upper()
            if isinstance(first_token, bytes)
            else str(first_token).upper()
        )

        args = [
            arg if isinstance(arg, bytes) else str(arg).encode("utf-8")
            for arg in cmd_parts[1:]
        ]

        cmd = self.server.registry.get(cmd_name)
        if cmd is None:
            return

        # Dummy context
        from unittest.mock import MagicMock
        dummy_conn = MagicMock()
        dummy_conn.db_id = db_id
        dummy_conn.authenticated = True

        ctx = CommandContext(
            connection=dummy_conn,
            server=self.server,
            db_id=db_id,
            keyspace=self.server.db_manager.get_database(db_id),
            raw_args=args,
        )

        try:
            cmd.execute(ctx, args)
        except Exception as e:
            logger.debug(f"Error executing replayed command {cmd_name}: {e}")
