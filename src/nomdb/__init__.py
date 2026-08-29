from pathlib import Path
from urllib.parse import urlparse
import threading
import asyncio
from nomdb.client.client import Client, AsyncClient
from nomdb.embedded import NomDB, open_db
from nomdb.server.server import NomDBServer
from nomdb.config.settings import ServerSettings

__version__ = "1.0.0"

def from_url(url: str):
    if url.endswith(".db") or url.endswith(".nomdb") or url.endswith(".dump") or Path(url).exists():
        raw_path = url[8:] if url.startswith("nomdb://") else url
        return open_db(raw_path)

    if url.startswith("nomdb://") or url.startswith("redis://"):
        try:
            parsed = urlparse(url)
            if parsed.path.endswith(".db") or parsed.path.endswith(".nomdb"):
                return open_db(parsed.path.lstrip("/"))
            if parsed.hostname and (parsed.port or not parsed.path.endswith(".db")):
                return Client.from_url(url)
        except Exception:
            raw_path = url.split("://", 1)[-1]
            return open_db(raw_path)

    return open_db(url)

connect = from_url

def serve(host: str = "127.0.0.1", port: int = 6379, data_dir: str = "./data", aof: bool = True):
    """Start and host the NomDB TCP server."""
    settings = ServerSettings(host=host, port=port, data_dir=data_dir, aof_enabled=aof)
    server = NomDBServer(settings)
    asyncio.run(server.run_forever())

def serve_background(host: str = "127.0.0.1", port: int = 6379, data_dir: str = "./data", aof: bool = True) -> NomDBServer:
    """Start and host the NomDB TCP server in a background thread."""
    settings = ServerSettings(host=host, port=port, data_dir=data_dir, aof_enabled=aof)
    server = NomDBServer(settings)
    ready = threading.Event()

    def _runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.start())
        ready.set()
        loop.run_forever()

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    ready.wait(timeout=5.0)
    return server

__all__ = [
    "NomDB",
    "open_db",
    "Client",
    "AsyncClient",
    "from_url",
    "connect",
    "serve",
    "serve_background",
    "NomDBServer",
    "__version__",
]
