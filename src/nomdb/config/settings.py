"""
Configuration settings for NomDB.
Supports loading from environment variables, config files, and CLI flags.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ServerSettings:
    # Network
    host: str = "127.0.0.1"
    port: int = 6379
    max_clients: int = 10000
    timeout_seconds: float = 0.0  # 0 means no idle timeout
    tcp_backlog: int = 511

    # Security
    require_auth: bool = False
    password: Optional[str] = None
    protected_mode: bool = False

    # Databases
    databases: int = 16

    # Memory & Eviction
    max_memory_bytes: int = 0  # 0 means unlimited
    max_memory_policy: str = "noeviction"  # noeviction, allkeys-lru, volatile-lru, allkeys-lfu, volatile-lfu
    max_memory_samples: int = 5

    # Persistence
    data_dir: str = "./data"
    aof_enabled: bool = True
    aof_filename: str = "appendonly.aof"
    aof_fsync: str = "everysec"  # always, everysec, no
    aof_rewrite_min_size: int = 64 * 1024 * 1024  # 64MB
    aof_rewrite_percentage: int = 100

    snapshot_enabled: bool = True
    snapshot_filename: str = "dump.nomdb"
    snapshot_interval_seconds: int = 300  # 5 min
    snapshot_min_changes: int = 100

    # Expiration
    active_expire_interval_ms: int = 100
    active_expire_batch_size: int = 20

    # Replication
    replica_of_host: Optional[str] = None
    replica_of_port: Optional[int] = None
    replication_backlog_size: int = 1024 * 1024  # 1MB
    replica_read_only: bool = True

    # Cluster
    cluster_enabled: bool = False
    cluster_node_id: Optional[str] = None
    cluster_config_file: str = "nodes.conf"

    # Observability
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    metrics_enabled: bool = True
    metrics_port: int = 9121

    @property
    def aof_path(self) -> Path:
        return Path(self.data_dir) / self.aof_filename

    @property
    def snapshot_path(self) -> Path:
        return Path(self.data_dir) / self.snapshot_filename

    @classmethod
    def from_env(cls) -> ServerSettings:
        """Create settings populated from NOMDB_* environment variables."""
        return cls(
            host=os.getenv("NOMDB_HOST", "127.0.0.1"),
            port=int(os.getenv("NOMDB_PORT", "6379")),
            max_clients=int(os.getenv("NOMDB_MAX_CLIENTS", "10000")),
            timeout_seconds=float(os.getenv("NOMDB_TIMEOUT", "0")),
            require_auth=os.getenv("NOMDB_REQUIRE_AUTH", "false").lower() in ("true", "1", "yes"),
            password=os.getenv("NOMDB_PASSWORD") or None,
            databases=int(os.getenv("NOMDB_DATABASES", "16")),
            max_memory_bytes=int(os.getenv("NOMDB_MAX_MEMORY_BYTES", "0")),
            max_memory_policy=os.getenv("NOMDB_MAX_MEMORY_POLICY", "noeviction"),
            data_dir=os.getenv("NOMDB_DATA_DIR", "./data"),
            aof_enabled=os.getenv("NOMDB_AOF_ENABLED", "true").lower() in ("true", "1", "yes"),
            aof_filename=os.getenv("NOMDB_AOF_FILENAME", "appendonly.aof"),
            aof_fsync=os.getenv("NOMDB_AOF_FSYNC", "everysec"),
            snapshot_enabled=os.getenv("NOMDB_SNAPSHOT_ENABLED", "true").lower() in ("true", "1", "yes"),
            snapshot_filename=os.getenv("NOMDB_SNAPSHOT_FILENAME", "dump.nomdb"),
            active_expire_interval_ms=int(os.getenv("NOMDB_ACTIVE_EXPIRE_INTERVAL_MS", "100")),
            active_expire_batch_size=int(os.getenv("NOMDB_ACTIVE_EXPIRE_BATCH_SIZE", "20")),
            replica_of_host=os.getenv("NOMDB_REPLICA_OF") or None,
            replica_of_port=int(os.getenv("NOMDB_REPLICA_PORT", "6379")) if os.getenv("NOMDB_REPLICA_PORT") else None,
            replication_backlog_size=int(os.getenv("NOMDB_REPLICATION_BACKLOG_SIZE", str(1024 * 1024))),
            cluster_enabled=os.getenv("NOMDB_CLUSTER_ENABLED", "false").lower() in ("true", "1", "yes"),
            cluster_node_id=os.getenv("NOMDB_CLUSTER_NODE_ID") or None,
            log_level=os.getenv("NOMDB_LOG_LEVEL", "INFO").upper(),
            log_format=os.getenv("NOMDB_LOG_FORMAT", "json").lower(),
            metrics_enabled=os.getenv("NOMDB_METRICS_ENABLED", "true").lower() in ("true", "1", "yes"),
            metrics_port=int(os.getenv("NOMDB_METRICS_PORT", "9121")),
        )
