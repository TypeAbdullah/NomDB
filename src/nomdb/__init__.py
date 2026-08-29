"""
NomDB: Production-grade Redis-inspired in-memory key-value database from scratch.
"""

from nomdb.client.client import Client, AsyncClient

__version__ = "1.0.0"
__all__ = ["Client", "AsyncClient", "__version__"]
