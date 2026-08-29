"""
Cluster commands for NomDB (CLUSTER NODES, SLOTS, INFO, MEET, ADDSLOTS, KEYSLOT).
"""

from __future__ import annotations
from typing import Any, List
from nomdb.cluster.slots import key_to_slot
from nomdb.commands.base import BaseCommand, CommandContext
from nomdb.protocol.exceptions import NomDBError, SyntaxError
from nomdb.protocol.resp import OK, SimpleString


class ClusterCommand(BaseCommand):
    name = "CLUSTER"
    arity = -2  # CLUSTER subcmd [args...]
    is_write = False
    complexity = "O(N)"
    description = "A group of cluster management commands."

    def execute(self, ctx: CommandContext, args: List[bytes]) -> Any:
        subcmd = args[0].decode("utf-8", errors="replace").upper()

        if subcmd == "NODES":
            return ctx.server.cluster_manager.get_cluster_nodes_output().encode("utf-8")

        elif subcmd == "SLOTS":
            return ctx.server.cluster_manager.get_cluster_slots_output()

        elif subcmd == "INFO":
            return ctx.server.cluster_manager.get_cluster_info_output().encode("utf-8")

        elif subcmd == "MYID":
            return ctx.server.cluster_manager.myself_id.encode("ascii")

        elif subcmd == "KEYSLOT" and len(args) > 1:
            key = args[1]
            return key_to_slot(key)

        elif subcmd == "MEET" and len(args) > 2:
            host = args[1].decode("utf-8", errors="replace")
            try:
                port = int(args[2])
            except ValueError:
                raise NomDBError("invalid port")
            node_id = f"node_{host}_{port}"
            ctx.server.cluster_manager.add_node(node_id, host, port)
            return OK

        elif subcmd == "ADDSLOTS" and len(args) > 1:
            slots = []
            for arg in args[1:]:
                try:
                    slot = int(arg)
                    slots.append(slot)
                except ValueError:
                    raise NomDBError("invalid slot")
            ctx.server.cluster_manager.assign_slots(ctx.server.cluster_manager.myself_id, slots)
            return OK

        else:
            raise SyntaxError(f"unknown CLUSTER subcommand '{subcmd}'")
