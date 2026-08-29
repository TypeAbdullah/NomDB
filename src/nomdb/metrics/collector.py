"""
Metrics Collector and INFO statistics generator.
"""

from __future__ import annotations
import os
import platform
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from nomdb.server.server import NomDBServer


class MetricsCollector:
    """Collects runtime statistics, latencies, and generates INFO sections."""

    def __init__(self):
        self.start_time: float = time.time()
        self.total_connections: int = 0
        self.total_commands_processed: int = 0
        self.command_counts: Dict[str, int] = {}
        self.keyspace_hits: int = 0
        self.keyspace_misses: int = 0
        self.last_sample_time: float = time.time()
        self.last_sample_commands: int = 0
        self.current_ops_per_sec: int = 0

    def record_command(self, cmd_name: str) -> None:
        """Record command execution."""
        self.total_commands_processed += 1
        name = cmd_name.upper()
        self.command_counts[name] = self.command_counts.get(name, 0) + 1

    def record_hit(self) -> None:
        self.keyspace_hits += 1

    def record_miss(self) -> None:
        self.keyspace_misses += 1

    def sample_ops(self) -> None:
        """Compute instantaneous ops per second."""
        now = time.time()
        dt = now - self.last_sample_time
        if dt >= 1.0:
            d_cmds = self.total_commands_processed - self.last_sample_commands
            self.current_ops_per_sec = int(d_cmds / dt)
            self.last_sample_time = now
            self.last_sample_commands = self.total_commands_processed

    def get_info(self, server: NomDBServer, section: Optional[str] = None) -> str:
        """Generate Redis-compatible INFO command string."""
        sec = section.lower() if section else "all"
        sections = []

        # # Server
        if sec in ("all", "default", "server"):
            uptime = int(time.time() - self.start_time)
            sections.append(
                "# Server\r\n"
                f"nomdb_version:1.0.0\r\n"
                f"os:{platform.system()} {platform.release()}\r\n"
                f"arch_bits:64\r\n"
                f"process_id:{os.getpid()}\r\n"
                f"tcp_port:{server.settings.port}\r\n"
                f"uptime_in_seconds:{uptime}\r\n"
                f"uptime_in_days:{uptime // 86400}\r\n"
            )

        # # Clients
        if sec in ("all", "default", "clients"):
            sections.append(
                "# Clients\r\n"
                f"connected_clients:{server.connected_clients_count}\r\n"
                f"maxclients:{server.settings.max_clients}\r\n"
                f"total_connections_received:{self.total_connections}\r\n"
            )

        # # Memory
        if sec in ("all", "default", "memory"):
            mem_stats = server.memory_tracker.get_memory_stats()
            sections.append(
                "# Memory\r\n"
                f"used_memory:{mem_stats['used_memory']}\r\n"
                f"used_memory_human:{mem_stats['used_memory_human']}\r\n"
                f"used_memory_peak:{mem_stats['used_memory_peak']}\r\n"
                f"used_memory_peak_human:{mem_stats['used_memory_peak_human']}\r\n"
                f"maxmemory:{server.settings.max_memory_bytes}\r\n"
                f"maxmemory_policy:{server.settings.max_memory_policy}\r\n"
            )

        # # Persistence
        if sec in ("all", "default", "persistence"):
            sections.append(
                "# Persistence\r\n"
                f"loading:0\r\n"
                f"rdb_changes_since_last_save:0\r\n"
                f"rdb_bgsave_in_progress:{1 if server.snapshot_manager.is_saving else 0}\r\n"
                f"rdb_last_save_time:{int(server.snapshot_manager.last_save_time)}\r\n"
                f"aof_enabled:{1 if server.aof_manager.enabled else 0}\r\n"
                f"aof_fsync:{server.aof_manager.fsync_mode}\r\n"
            )

        # # Stats
        if sec in ("all", "default", "stats"):
            sections.append(
                "# Stats\r\n"
                f"total_connections_received:{self.total_connections}\r\n"
                f"total_commands_processed:{self.total_commands_processed}\r\n"
                f"instantaneous_ops_per_sec:{self.current_ops_per_sec}\r\n"
                f"keyspace_hits:{self.keyspace_hits}\r\n"
                f"keyspace_misses:{self.keyspace_misses}\r\n"
                f"expired_keys:{server.expiration_manager.expired_keys_count}\r\n"
                f"evicted_keys:{server.memory_tracker.evicted_keys_count}\r\n"
            )

        # # Replication
        if sec in ("all", "default", "replication"):
            role = "slave" if server.replica_manager else "master"
            rep_lines = [
                "# Replication\r\n",
                f"role:{role}\r\n",
            ]
            if role == "master":
                rep_lines.append(f"connected_slaves:{server.primary_replication.connected_replicas_count}\r\n")
                rep_lines.append(f"master_replid:{server.primary_replication.replid}\r\n")
                rep_lines.append(f"master_repl_offset:{server.primary_replication.master_offset}\r\n")
            else:
                rep_lines.append(f"master_host:{server.settings.replica_of_host}\r\n")
                rep_lines.append(f"master_port:{server.settings.replica_of_port}\r\n")
                rep_lines.append(f"master_link_status:{'up' if server.replica_manager and server.replica_manager.connected else 'down'}\r\n")
            sections.append("".join(rep_lines))

        # # Keyspace
        if sec in ("all", "default", "keyspace"):
            db_lines = ["# Keyspace\r\n"]
            for db_id in range(server.db_manager._num_databases):
                keyspace = server.db_manager.get_database(db_id)
                size = keyspace.size()
                if size > 0:
                    expires_count = sum(1 for e in keyspace.entries.values() if e.expire_at_ms is not None)
                    db_lines.append(f"db{db_id}:keys={size},expires={expires_count},avg_ttl=0\r\n")
            sections.append("".join(db_lines))

        # # Cluster
        if sec in ("all", "cluster"):
            sections.append(
                "# Cluster\r\n"
                f"cluster_enabled:{1 if server.cluster_manager.enabled else 0}\r\n"
            )

        return "\r\n".join(sections)
