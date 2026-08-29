from __future__ import annotations
import secrets
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from nomdb.cluster.slots import TOTAL_SLOTS, key_to_slot
from nomdb.protocol.exceptions import MovedError, CrossSlotError

@dataclass
class ClusterNodeInfo:
    node_id: str
    host: str
    port: int
    flags: str = "master"
    slots: Set[int] = field(default_factory=set)

class ClusterManager:
    def __init__(
        self,
        node_id: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 6379,
        enabled: bool = False,
    ):
        self.enabled = enabled
        self.myself_id = node_id or secrets.token_hex(20)
        self.host = host
        self.port = port

        self.myself = ClusterNodeInfo(
            node_id=self.myself_id,
            host=host,
            port=port,
            flags="myself,master",
            slots=set(range(TOTAL_SLOTS)) if not enabled else set(),
        )

        self.nodes: Dict[str, ClusterNodeInfo] = {self.myself_id: self.myself}
        self.slot_owners: List[Optional[str]] = [self.myself_id] * TOTAL_SLOTS if not enabled else [None] * TOTAL_SLOTS

    def assign_slots(self, node_id: str, slots: List[int]) -> None:
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found in cluster")

        node = self.nodes[node_id]
        for s in slots:
            if 0 <= s < TOTAL_SLOTS:
                old_owner_id = self.slot_owners[s]
                if old_owner_id and old_owner_id in self.nodes:
                    self.nodes[old_owner_id].slots.discard(s)
                self.slot_owners[s] = node_id
                node.slots.add(s)

    def add_node(self, node_id: str, host: str, port: int, flags: str = "master") -> ClusterNodeInfo:
        node = ClusterNodeInfo(node_id=node_id, host=host, port=port, flags=flags)
        self.nodes[node_id] = node
        return node

    def verify_key_route(self, key: bytes) -> None:
        if not self.enabled:
            return

        slot = key_to_slot(key)
        owner_id = self.slot_owners[slot]

        if owner_id == self.myself_id:
            return

        if owner_id is not None and owner_id in self.nodes:
            owner = self.nodes[owner_id]
            raise MovedError(slot, f"{owner.host}:{owner.port}")

        raise MovedError(slot, f"{self.host}:{self.port}")

    def verify_multi_key_route(self, keys: List[bytes]) -> None:
        if not self.enabled or not keys:
            return

        first_slot = key_to_slot(keys[0])
        for k in keys[1:]:
            if key_to_slot(k) != first_slot:
                raise CrossSlotError()

        self.verify_key_route(keys[0])

    def get_cluster_nodes_output(self) -> str:
        lines = []
        for node in self.nodes.values():
            slot_ranges = self._format_slot_ranges(sorted(node.slots))
            slot_str = f" {slot_ranges}" if slot_ranges else ""
            line = f"{node.node_id} {node.host}:{node.port}@1{node.port} {node.flags} - 0 0 1 connected{slot_str}"
            lines.append(line)
        return "\n".join(lines) + "\n"

    def get_cluster_slots_output(self) -> List[List[Any]]:
        results = []
        for node in self.nodes.values():
            if not node.slots:
                continue
            sorted_slots = sorted(node.slots)
            ranges = self._get_contiguous_ranges(sorted_slots)
            for start, end in ranges:
                results.append([
                    start,
                    end,
                    [node.host.encode("ascii"), node.port, node.node_id.encode("ascii")]
                ])
        return results

    def get_cluster_info_output(self) -> str:
        assigned = sum(1 for s in self.slot_owners if s is not None)
        state = "ok" if assigned == TOTAL_SLOTS or not self.enabled else "fail"
        return (
            f"cluster_state:{state}\r\n"
            f"cluster_slots_assigned:{assigned}\r\n"
            f"cluster_slots_ok:{assigned}\r\n"
            f"cluster_slots_pfail:0\r\n"
            f"cluster_slots_fail:0\r\n"
            f"cluster_known_nodes:{len(self.nodes)}\r\n"
            f"cluster_size:{sum(1 for n in self.nodes.values() if 'master' in n.flags)}\r\n"
            f"cluster_current_epoch:1\r\n"
            f"cluster_my_epoch:1\r\n"
        )

    @staticmethod
    def _get_contiguous_ranges(sorted_slots: List[int]) -> List[Tuple[int, int]]:
        if not sorted_slots:
            return []
        ranges = []
        start = sorted_slots[0]
        prev = start
        for s in sorted_slots[1:]:
            if s == prev + 1:
                prev = s
            else:
                ranges.append((start, prev))
                start = s
                prev = s
        ranges.append((start, prev))
        return ranges

    def _format_slot_ranges(self, sorted_slots: List[int]) -> str:
        ranges = self._get_contiguous_ranges(sorted_slots)
        parts = []
        for start, end in ranges:
            if start == end:
                parts.append(str(start))
            else:
                parts.append(f"{start}-{end}")
        return " ".join(parts)
