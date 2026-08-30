"""
Temporal-Causal Incident Knowledge Graph (TCIKG)

Represents entities (Actors, Services, Commits, PRs, Tickets, Alerts, Error Clusters, Decisions)
as nodes and their temporal, topological, and causal dependencies as directed typed edges.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from models.canonical_event import CanonicalEvent, EntityRegistry, EventSourceType


class NodeType(str, Enum):
    ACTOR = "actor"
    SERVICE = "service"
    COMMIT = "commit"
    PR = "pull_request"
    TICKET = "jira_ticket"
    ALERT = "alert"
    ERROR_CLUSTER = "error_cluster"
    DECISION = "decision"
    DEPLOYMENT = "deployment"
    RECOVERY = "recovery"


class EdgeRelation(str, Enum):
    TRIGGERED_BY = "triggered_by"
    COMMITTED_BY = "committed_by"
    AFFECTS_SERVICE = "affects_service"
    LINKED_TO = "linked_to"
    PRECEDES = "precedes"
    MITIGATED_BY = "mitigated_by"
    DISCUSSED_IN = "discussed_in"
    CORRELATED_WITH = "correlated_with"


class GraphNode(BaseModel):
    id: str
    node_type: NodeType
    label: str
    timestamp: str = ""
    entity_ref: str = ""
    severity: str = "info"
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: EdgeRelation
    weight: float = 1.0
    lag_seconds: float = 0.0
    evidence: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentGraph(BaseModel):
    """
    Queryable Incident Knowledge Graph.
    """
    nodes: dict[str, GraphNode] = Field(default_factory=dict)
    edges: list[GraphEdge] = Field(default_factory=list)
    adjacency: dict[str, list[str]] = Field(default_factory=dict)  # source -> [target_ids]

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node
        if node.id not in self.adjacency:
            self.adjacency[node.id] = []

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)
        if edge.source not in self.adjacency:
            self.adjacency[edge.source] = []
        if edge.target not in self.adjacency[edge.source]:
            self.adjacency[edge.source].append(edge.target)

    def get_nodes_by_type(self, node_type: NodeType) -> list[GraphNode]:
        return [n for n in self.nodes.values() if n.node_type == node_type]

    def find_causal_paths(self, start_id: str, end_id: str, max_depth: int = 5) -> list[list[str]]:
        """Find all directed causal paths between two nodes using DFS."""
        if start_id not in self.nodes or end_id not in self.nodes:
            return []

        paths = []
        visited = set()

        def _dfs(current: str, target: str, current_path: list[str], depth: int):
            if depth > max_depth:
                return
            if current == target:
                paths.append(list(current_path))
                return

            visited.add(current)
            for neighbor in self.adjacency.get(current, []):
                if neighbor not in visited:
                    current_path.append(neighbor)
                    _dfs(neighbor, target, current_path, depth + 1)
                    current_path.pop()
            visited.remove(current)

        _dfs(start_id, end_id, [start_id], 0)
        return paths

    def compute_blast_radius(self, trigger_node_id: str) -> list[str]:
        """Compute all affected service and component nodes reachable from a trigger."""
        if trigger_node_id not in self.nodes:
            return []

        affected = set()
        queue = [trigger_node_id]
        visited = {trigger_node_id}

        while queue:
            curr = queue.pop(0)
            node = self.nodes.get(curr)
            if node and node.node_type == NodeType.SERVICE:
                affected.add(node.label)

            for neighbor in self.adjacency.get(curr, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return sorted(affected)

    def find_suspicious_triggers(self, incident_time: str, lookback_hours: int = 48) -> list[GraphNode]:
        """Find deploys, commits, and config changes preceding the incident time."""
        triggers = []
        for node in self.nodes.values():
            if node.node_type in (NodeType.COMMIT, NodeType.DEPLOYMENT, NodeType.PR):
                if node.timestamp and incident_time:
                    try:
                        t_node = datetime.fromisoformat(node.timestamp.replace("Z", "+00:00"))
                        t_inc = datetime.fromisoformat(incident_time.replace("Z", "+00:00"))
                        diff_sec = (t_inc - t_node).total_seconds()
                        if 0 <= diff_sec <= (lookback_hours * 3600):
                            triggers.append(node)
                    except ValueError:
                        triggers.append(node)
                else:
                    triggers.append(node)

        # Sort closest to incident time first
        triggers.sort(key=lambda n: n.timestamp, reverse=True)
        return triggers

    def to_summary_dict(self) -> dict[str, Any]:
        """Return high-level summary of the graph topology."""
        counts = {}
        for n in self.nodes.values():
            counts[n.node_type.value] = counts.get(n.node_type.value, 0) + 1

        rel_counts = {}
        for e in self.edges:
            rel_counts[e.relation.value] = rel_counts.get(e.relation.value, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes_by_type": counts,
            "edges_by_relation": rel_counts,
        }
