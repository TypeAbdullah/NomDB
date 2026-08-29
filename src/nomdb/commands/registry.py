"""
Command Registry.
Dispatches command requests to their registered handlers.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from nomdb.commands.base import BaseCommand


class CommandRegistry:
    """Registry maintaining mapping from command name (uppercase) to command handler."""

    def __init__(self):
        self._commands: Dict[str, BaseCommand] = {}

    def register(self, command: BaseCommand) -> None:
        """Register a command handler."""
        self._commands[command.name.upper()] = command

    def get(self, name: str) -> Optional[BaseCommand]:
        """Look up command by case-insensitive name."""
        return self._commands.get(name.upper())

    def all_commands(self) -> List[BaseCommand]:
        return list(self._commands.values())
