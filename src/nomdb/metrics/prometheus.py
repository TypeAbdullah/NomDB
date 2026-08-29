"""
Prometheus metrics format exporter for NomDB.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nomdb.server.server import NomDBServer


def generate_prometheus_metrics(server: NomDBServer) -> str:
    """Generate Prometheus metric text exposition format."""
    lines = []

    # Total commands
    lines.append("# HELP nomdb_commands_total Total number of commands processed")
    lines.append("# TYPE nomdb_commands_total counter")
    lines.append(f"nomdb_commands_total {server.metrics.total_commands_processed}")

    # Connected clients
    lines.append("# HELP nomdb_connected_clients Current number of connected clients")
    lines.append("# TYPE nomdb_connected_clients gauge")
    lines.append(f"nomdb_connected_clients {server.connected_clients_count}")

    # Memory used
    mem_stats = server.memory_tracker.get_memory_stats()
    lines.append("# HELP nomdb_used_memory_bytes Total memory consumed by keyspace in bytes")
    lines.append("# TYPE nomdb_used_memory_bytes gauge")
    lines.append(f"nomdb_used_memory_bytes {mem_stats['used_memory']}")

    # Keyspace keys
    lines.append("# HELP nomdb_total_keys Total active keys across all databases")
    lines.append("# TYPE nomdb_total_keys gauge")
    lines.append(f"nomdb_total_keys {mem_stats['total_keys']}")

    # Hits / misses
    lines.append("# HELP nomdb_keyspace_hits_total Total keyspace hits")
    lines.append("# TYPE nomdb_keyspace_hits_total counter")
    lines.append(f"nomdb_keyspace_hits_total {server.metrics.keyspace_hits}")

    lines.append("# HELP nomdb_keyspace_misses_total Total keyspace misses")
    lines.append("# TYPE nomdb_keyspace_misses_total counter")
    lines.append(f"nomdb_keyspace_misses_total {server.metrics.keyspace_misses}")

    # Expired / Evicted
    lines.append("# HELP nomdb_expired_keys_total Total expired keys purged")
    lines.append("# TYPE nomdb_expired_keys_total counter")
    lines.append(f"nomdb_expired_keys_total {server.expiration_manager.expired_keys_count}")

    lines.append("# HELP nomdb_evicted_keys_total Total keys evicted due to maxmemory")
    lines.append("# TYPE nomdb_evicted_keys_total counter")
    lines.append(f"nomdb_evicted_keys_total {server.memory_tracker.evicted_keys_count}")

    return "\n".join(lines) + "\n"
