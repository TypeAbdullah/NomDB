"""
FluxKV compatibility wrapper for NomDB.
"""

import sys
import nomdb
from nomdb.client.client import Client, AsyncClient

__version__ = nomdb.__version__
__all__ = ["Client", "AsyncClient", "__version__"]
