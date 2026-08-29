"""
Custom exceptions for NomDB protocol and command handling.
"""


class NomDBError(Exception):
    """Base exception for all NomDB errors."""

    def __init__(self, message: str, prefix: str = "ERR"):
        self.message = message
        self.prefix = prefix
        super().__init__(f"{prefix} {message}" if prefix else message)


class ProtocolError(NomDBError):
    """Raised when client sends invalid RESP protocol data."""

    def __init__(self, message: str):
        super().__init__(message, prefix="ERR Protocol error:")


class WrongTypeError(NomDBError):
    """Raised when operation is performed against incompatible key data type."""

    def __init__(self, message: str = "Operation against a key holding the wrong kind of value"):
        super().__init__(message, prefix="WRONGTYPE")


class NoSuchKeyError(NomDBError):
    """Raised when key is not found (for internal use)."""

    def __init__(self, message: str = "no such key"):
        super().__init__(message, prefix="ERR")


class AuthenticationError(NomDBError):
    """Raised when authentication fails or is required."""

    def __init__(self, message: str = "NOAUTH Authentication required."):
        super().__init__(message, prefix="")


class SyntaxError(NomDBError):
    """Raised when command syntax is invalid."""

    def __init__(self, message: str = "syntax error"):
        super().__init__(message, prefix="ERR")


class OutOfMemoryError(NomDBError):
    """Raised when maxmemory is exceeded and eviction cannot free enough memory."""

    def __init__(self, message: str = "OOM command not allowed when used memory > 'maxmemory'."):
        super().__init__(message, prefix="OOM")


class ClusterError(NomDBError):
    """Base error for cluster operations."""
    pass


class MovedError(ClusterError):
    """Raised when key belongs to a different cluster slot/node."""

    def __init__(self, slot: int, endpoint: str):
        self.slot = slot
        self.endpoint = endpoint
        super().__init__(f"{slot} {endpoint}", prefix="MOVED")


class AskError(ClusterError):
    """Raised when key slot is migrating."""

    def __init__(self, slot: int, endpoint: str):
        self.slot = slot
        self.endpoint = endpoint
        super().__init__(f"{slot} {endpoint}", prefix="ASK")


class CrossSlotError(ClusterError):
    """Raised when multi-key command touches keys from multiple hash slots."""

    def __init__(self, message: str = "CROSSSLOT Keys in request don't hash to the same slot"):
        super().__init__(message, prefix="")
