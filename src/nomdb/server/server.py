"""
NomDB Asynchronous TCP Server and Lifespan Manager.
"""

from __future__ import annotations
import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, Optional, Set
from nomdb.commands import create_default_registry
from nomdb.config.settings import ServerSettings
from nomdb.expiration.manager import ExpirationManager
from nomdb.memory.eviction import EvictionManager
from nomdb.memory.tracker import MemoryTracker
from nomdb.metrics.collector import MetricsCollector
from nomdb.metrics.prometheus import generate_prometheus_metrics
from nomdb.persistence.aof import AOFManager
from nomdb.persistence.recovery import RecoveryManager
from nomdb.persistence.snapshot import SnapshotManager
from nomdb.protocol.exceptions import ProtocolError
from nomdb.protocol.encoder import RESPEncoder
from nomdb.protocol.resp import NO_REPLY
from nomdb.pubsub.broker import PubSubBroker
from nomdb.replication.primary import PrimaryReplicationManager
from nomdb.replication.replica import ReplicaManager
from nomdb.cluster.node import ClusterManager
from nomdb.storage.database import DatabaseManager
from nomdb.server.connection import ClientConnection
from nomdb.server.dispatcher import CommandDispatcher

logger = logging.getLogger("nomdb.server")


class NomDBServer:
    """Main NomDB Database Server."""

    def __init__(self, settings: Optional[ServerSettings] = None):
        self.settings = settings or ServerSettings.from_env()
        self._configure_logging()

        # Core Engines
        self.db_manager = DatabaseManager(self.settings.databases)
        self.expiration_manager = ExpirationManager(
            self.db_manager,
            interval_ms=self.settings.active_expire_interval_ms,
            batch_size=self.settings.active_expire_batch_size,
        )
        self.memory_tracker = MemoryTracker(self.db_manager)
        self.eviction_manager = EvictionManager(
            self.db_manager,
            self.memory_tracker,
            max_memory_bytes=self.settings.max_memory_bytes,
            policy=self.settings.max_memory_policy,
            samples=self.settings.max_memory_samples,
        )

        self.aof_manager = AOFManager(
            self.settings.aof_path,
            fsync_mode=self.settings.aof_fsync,
            enabled=self.settings.aof_enabled,
        )
        self.snapshot_manager = SnapshotManager(
            self.settings.snapshot_path,
            enabled=self.settings.snapshot_enabled,
        )
        self.recovery_manager = RecoveryManager(
            self.db_manager,
            self.snapshot_manager,
            self.aof_manager,
            self.expiration_manager,
        )

        self.pubsub_broker = PubSubBroker()
        self.primary_replication = PrimaryReplicationManager(
            backlog_size=self.settings.replication_backlog_size
        )
        self.cluster_manager = ClusterManager(
            node_id=self.settings.cluster_node_id,
            host=self.settings.host,
            port=self.settings.port,
            enabled=self.settings.cluster_enabled,
        )
        self.metrics = MetricsCollector()

        # Commands & Dispatcher
        self.registry = create_default_registry()
        self.dispatcher = CommandDispatcher(self)

        # Replica manager (if this server is configured as a replica)
        self.replica_manager: Optional[ReplicaManager] = None
        if self.settings.replica_of_host and self.settings.replica_of_port:
            self.replica_manager = ReplicaManager(
                self.settings.replica_of_host,
                self.settings.replica_of_port,
                self.settings.port,
                self.dispatcher,
            )

        # Networking State
        self._server: Optional[asyncio.Server] = None
        self._metrics_server: Optional[asyncio.Server] = None
        self._clients: Set[ClientConnection] = set()
        self._running = False
        self._ops_task: Optional[asyncio.Task] = None

    def _configure_logging(self) -> None:
        level = getattr(logging, self.settings.log_level.upper(), logging.INFO)
        fmt = (
            '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
            if self.settings.log_format == "json"
            else "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        logging.basicConfig(level=level, format=fmt, force=True)

    @property
    def connected_clients_count(self) -> int:
        return len(self._clients)

    def set_replica_of(self, host: str, port: int) -> None:
        """Dynamically configure server as replica."""
        if self.replica_manager:
            self.replica_manager.stop()
        self.settings.replica_of_host = host
        self.settings.replica_of_port = port
        self.replica_manager = ReplicaManager(host, port, self.settings.port, self.dispatcher)
        self.replica_manager.start()

    async def start(self) -> None:
        """Start the database server and all subsystem workers."""
        logger.info(f"NomDB v1.0.0 starting on {self.settings.host}:{self.settings.port}")

        # 1. Crash recovery (Snapshot + AOF)
        self.recovery_manager.recover(self.dispatcher)

        # 2. Start Subsystems
        self.expiration_manager.start()
        self.aof_manager.start()
        self.primary_replication.start()
        if self.replica_manager:
            self.replica_manager.start()

        self._running = True
        self._ops_task = asyncio.create_task(self._ops_sampling_loop())

        # 3. Start TCP Server
        self._server = await asyncio.start_server(
            self._handle_client,
            host=self.settings.host,
            port=self.settings.port,
            backlog=self.settings.tcp_backlog,
        )

        # 4. Optional Prometheus Metrics HTTP Server
        if self.settings.metrics_enabled and self.settings.metrics_port:
            try:
                self._metrics_server = await asyncio.start_server(
                    self._handle_metrics_http,
                    host=self.settings.host,
                    port=self.settings.metrics_port,
                )
                logger.info(f"Metrics HTTP exporter listening on port {self.settings.metrics_port}")
            except Exception as e:
                logger.warning(f"Could not start metrics server on port {self.settings.metrics_port}: {e}")

        logger.info(f"Ready to accept connections at {self.settings.host}:{self.settings.port}")

    async def run_forever(self) -> None:
        """Run server until stop signal received."""
        await self.start()
        async with self._server:
            await self._server.serve_forever()

    async def shutdown(self) -> None:
        """Gracefully shut down server, persist data, and close connections."""
        if not self._running:
            return
        logger.info("NomDB shutting down gracefully...")
        self._running = False

        if self._ops_task and not self._ops_task.done():
            self._ops_task.cancel()

        # Stop accepting new connections
        if self._server:
            self._server.close()
            try:
                await self._server.wait_closed()
            except Exception:
                pass

        if self._metrics_server:
            self._metrics_server.close()
            try:
                await self._metrics_server.wait_closed()
            except Exception:
                pass

        # Stop background workers
        self.expiration_manager.stop()
        if self.replica_manager:
            self.replica_manager.stop()
        self.primary_replication.stop()

        # Close existing client connections
        for client in list(self._clients):
            self.pubsub_broker.remove_connection(client)
            client.close()
        self._clients.clear()

        # Save snapshot and flush AOF
        try:
            self.snapshot_manager.save(self.db_manager)
            logger.info("Snapshot saved during shutdown")
        except Exception as e:
            logger.error(f"Error saving snapshot during shutdown: {e}")

        self.aof_manager.stop()
        logger.info("NomDB shutdown complete.")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Client connection handler."""
        if len(self._clients) >= self.settings.max_clients:
            err_resp = RESPEncoder.encode(ProtocolError("max number of clients reached"))
            writer.write(err_resp)
            await writer.drain()
            writer.close()
            return

        client = ClientConnection(reader, writer, self)
        self._clients.add(client)
        self.metrics.total_connections += 1

        try:
            while self._running and not client.should_close:
                # Read chunks from socket
                chunk = await reader.read(65536)
                if not chunk:
                    break  # Connection closed by client

                client.touch()
                client.parser.feed(chunk)

                try:
                    commands = client.parser.get_parsed_commands()
                except ProtocolError as pe:
                    client.send_response(pe)
                    await client.flush()
                    break

                for cmd_parts in commands:
                    if not cmd_parts:
                        continue

                    # Execute command
                    res = self.dispatcher.dispatch_command(client, cmd_parts)
                    if res is not NO_REPLY:
                        client.send_response(res)

                await client.flush()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Client connection error ({client.client_id}): {e}")
        finally:
            self.pubsub_broker.remove_connection(client)
            self.primary_replication.remove_replica(client)
            self._clients.discard(client)
            client.close()

    async def _handle_metrics_http(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Simple HTTP endpoint for /metrics."""
        try:
            line = await reader.readline()
            metrics_body = generate_prometheus_metrics(self)
            body_bytes = metrics_body.encode("utf-8")
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/plain; version=0.0.4\r\n"
                b"Content-Length: " + str(len(body_bytes)).encode("ascii") + b"\r\n"
                b"Connection: close\r\n\r\n" + body_bytes
            )
            writer.write(response)
            await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()

    async def _ops_sampling_loop(self) -> None:
        """Periodic metrics sampling."""
        while self._running:
            try:
                await asyncio.sleep(1.0)
                self.metrics.sample_ops()
            except asyncio.CancelledError:
                break
            except Exception:
                pass


def main() -> None:
    """CLI entrypoint for running nomdb-server."""
    parser = argparse.ArgumentParser(description="NomDB: In-Memory Key-Value Database Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=6379, help="TCP port (default: 6379)")
    parser.add_argument("--data-dir", default="./data", help="Data directory (default: ./data)")
    parser.add_argument("--require-auth", action="store_true", help="Require password authentication")
    parser.add_argument("--password", default=None, help="Server auth password")
    parser.add_argument("--maxmemory", type=int, default=0, help="Max memory in bytes (0 for unlimited)")
    parser.add_argument("--maxmemory-policy", default="noeviction", help="Eviction policy (noeviction, allkeys-lru, etc.)")
    parser.add_argument("--aof", action="store_true", default=True, help="Enable Append-Only File")
    parser.add_argument("--no-aof", action="store_false", dest="aof", help="Disable AOF")
    parser.add_argument("--replicaof", nargs=2, metavar=("HOST", "PORT"), help="Run as replica of specified primary")
    parser.add_argument("--cluster", action="store_true", help="Enable cluster mode")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")

    args = parser.parse_args()

    settings = ServerSettings.from_env()
    settings.host = args.host
    settings.port = args.port
    settings.data_dir = args.data_dir
    settings.require_auth = args.require_auth or (args.password is not None)
    settings.password = args.password
    settings.max_memory_bytes = args.maxmemory
    settings.max_memory_policy = args.maxmemory_policy
    settings.aof_enabled = args.aof
    settings.cluster_enabled = args.cluster
    settings.log_level = args.log_level

    if args.replicaof:
        settings.replica_of_host = args.replicaof[0]
        settings.replica_of_port = int(args.replicaof[1])

    server = NomDBServer(settings)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Signal handlers
    def handle_signal():
        loop.create_task(server.shutdown())

    for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
        if sig is not None:
            try:
                loop.add_signal_handler(sig, handle_signal)
            except NotImplementedError:
                # Windows doesn't support loop.add_signal_handler
                pass

    try:
        loop.run_until_complete(server.run_forever())
    except (KeyboardInterrupt, SystemExit):
        loop.run_until_complete(server.shutdown())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
