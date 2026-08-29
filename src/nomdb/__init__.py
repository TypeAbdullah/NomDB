from pathlib import Path
from urllib.parse import urlparse
from nomdb.client.client import Client, AsyncClient
from nomdb.embedded import NomDB, open_db

__version__ = "1.0.0"

def from_url(url: str):
    # Check if direct local file path
    if url.endswith(".db") or url.endswith(".nomdb") or url.endswith(".dump") or Path(url).exists():
        raw_path = url[8:] if url.startswith("nomdb://") else url
        return open_db(raw_path)

    if url.startswith("nomdb://") or url.startswith("redis://"):
        try:
            parsed = urlparse(url)
            # If path ends with database file extension
            if parsed.path.endswith(".db") or parsed.path.endswith(".nomdb"):
                return open_db(parsed.path.lstrip("/"))
            if parsed.hostname and (parsed.port or not parsed.path.endswith(".db")):
                return Client.from_url(url)
        except Exception:
            raw_path = url.split("://", 1)[-1]
            return open_db(raw_path)

    return open_db(url)

connect = from_url

__all__ = ["NomDB", "open_db", "Client", "AsyncClient", "from_url", "connect", "__version__"]
