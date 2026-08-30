"""
Unit tests for the Temporal-Causal Incident Knowledge Graph (TCIKG).
"""

import unittest
from models.incident_graph import IncidentGraph, GraphNode, GraphEdge, NodeType, EdgeRelation


class TestIncidentGraph(unittest.TestCase):

    def setUp(self):
        self.graph = IncidentGraph()

    def test_graph_node_and_edge_addition(self):
        node1 = GraphNode(
            id="commit-1",
            node_type=NodeType.COMMIT,
            label="commit:7a8b9c (Remove connection timeout)",
            timestamp="2025-03-15T14:00:00Z",
        )
        node2 = GraphNode(
            id="alert-1",
            node_type=NodeType.ALERT,
            label="High latency on /auth/login",
            timestamp="2025-03-15T14:15:00Z",
            severity="critical",
        )
        node3 = GraphNode(
            id="svc-auth",
            node_type=NodeType.SERVICE,
            label="auth-service",
        )

        self.graph.add_node(node1)
        self.graph.add_node(node2)
        self.graph.add_node(node3)

        self.graph.add_edge(GraphEdge(
            source="commit-1",
            target="alert-1",
            relation=EdgeRelation.TRIGGERED_BY,
            lag_seconds=900.0,
        ))
        self.graph.add_edge(GraphEdge(
            source="alert-1",
            target="svc-auth",
            relation=EdgeRelation.AFFECTS_SERVICE,
        ))

        # Test path finding from commit-1 to svc-auth
        paths = self.graph.find_causal_paths("commit-1", "svc-auth")
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0], ["commit-1", "alert-1", "svc-auth"])

        # Test blast radius
        blast_radius = self.graph.compute_blast_radius("commit-1")
        self.assertIn("auth-service", blast_radius)

    def test_find_suspicious_triggers(self):
        self.graph.add_node(GraphNode(
            id="commit-old",
            node_type=NodeType.COMMIT,
            label="old commit",
            timestamp="2025-03-10T10:00:00Z",
        ))
        self.graph.add_node(GraphNode(
            id="commit-recent",
            node_type=NodeType.COMMIT,
            label="recent deploy",
            timestamp="2025-03-15T13:45:00Z",
        ))

        triggers = self.graph.find_suspicious_triggers(
            incident_time="2025-03-15T14:00:00Z",
            lookback_hours=2,
        )
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0].id, "commit-recent")


if __name__ == "__main__":
    unittest.main()
