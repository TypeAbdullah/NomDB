"""
Base command class and execution context for NomDB commands.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional
from nomdb.storage.keyspace import Keyspace

if TYPE_CHECKING:
    from nomdb.server.connection import ClientConnection
    from nomdb.server.server import NomDBServer


@dataclass
class CommandContext:
    """Context passed to each command execution."""
    connection: ClientConnection
    server: NomDBServer
    db_id: int
    keyspace: Keyspace
    raw_args: List[bytes]


class BaseCommand(ABC):
    """Abstract base class for all database commands."""

    name: str = ""
    # Arity: positive number = exact args (including command name),
    # negative number = minimum abs(arity) args (e.g. -2 means >= 2 args total)
    arity: int = 1
    is_write: bool = False
    is_admin: bool = False
    is_pubsub: bool = False
    complexity: str = "O(1)"
    description: str = ""

    def validate_arity(self, args_len: int) -> bool:
        """Validate argument count against command arity specification."""
        if self.arity > 0:
            return args_len == self.arity
        return args_len >= abs(self.arity)

    @abstractmethod
    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        """
        Execute command with given context and arguments.
        args: list of argument bytes excluding the command name itself.
        Returns RESP-serializable object or raises NomDBError.
        """
        pass
