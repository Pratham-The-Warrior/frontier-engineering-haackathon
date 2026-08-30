"""
Comprehensive Edge-Case & Robustness Tests.
Validates zero-failure handling across all edge-case inputs, malformed data, and boundary conditions.
"""

import unittest
from tools.sanitizer import sanitize_text, sanitize_dict, _is_sensitive_key
from tools.entity_resolver import EntityResolver
from tools.time_tools import normalise_timestamp, events_in_window, correlate_events, correlate_events_with_lag, detect_gaps, compute_duration
from models.canonical_event import CanonicalEvent, EntityRegistry, EventSourceType, EventSeverity
from models.incident_graph import IncidentGraph, GraphNode, GraphEdge, NodeType, EdgeRelation
from collectors.log_collector import extract_log_template, cluster_log_templates
from collectors.jira_collector import parse_pasted_jira_tickets, _extract_adf_text


class TestEdgeCases(unittest.TestCase):

    # -----------------------------------------------------------------------
    # Sanitizer Edge Cases
    # -----------------------------------------------------------------------
    def test_sanitizer_does_not_redact_passed_tests_or_bypass(self):
        # Ensure benign words with "pass" are preserved
        payload = {
            "passed_tests": 48,
            "pass_rate": "99.5%",
            "bypass_cache": False,
            "compass_heading": 180,
            "password": "actual_secret_password_123",
            "db_pass": "secret_db_pass",
        }
        sanitized = sanitize_dict(payload)
        self.assertEqual(sanitized["passed_tests"], 48)
        self.assertEqual(sanitized["pass_rate"], "99.5%")
        self.assertEqual(sanitized["bypass_cache"], False)
        self.assertEqual(sanitized["compass_heading"], 180)
        self.assertEqual(sanitized["password"], "[REDACTED_CREDENTIAL]")
        self.assertEqual(sanitized["db_pass"], "[REDACTED_CREDENTIAL]")

    def test_sanitizer_none_and_empty_inputs(self):
        self.assertEqual(sanitize_text(""), "")
        self.assertEqual(sanitize_text(None), None)
        self.assertEqual(sanitize_dict(None), None)
        self.assertEqual(sanitize_dict({}), {})
        self.assertEqual(sanitize_dict([]), [])

    # -----------------------------------------------------------------------
    # Entity Resolver Edge Cases
    # -----------------------------------------------------------------------
    def test_entity_resolver_pure_numbers_not_matched_as_commits(self):
        resolver = EntityResolver()
        text = "Order 1234567 placed at timestamp 1710512340 with port 5432000. Fix in commit 7a8b9c1 for PROD-99."
        refs = resolver.extract_entity_references(text)
        self.assertIn("ticket:PROD-99", refs)
        self.assertIn("commit:7a8b9c1", refs)
        # 1234567 and 1710512340 should NOT be in commit refs
        self.assertNotIn("commit:1234567", refs)
        self.assertNotIn("commit:1710512", refs)

    def test_entity_resolver_empty_and_bot_actors(self):
        resolver = EntityResolver()
        system_actor = resolver.resolve_actor_from_signal("bot")
        self.assertEqual(system_actor.actor_id, "system")

        unknown_actor = resolver.resolve_actor_from_signal("")
        self.assertEqual(unknown_actor.actor_id, "system")

    # -----------------------------------------------------------------------
    # Time Tools Edge Cases
    # -----------------------------------------------------------------------
    def test_time_tools_none_and_malformed_timestamps(self):
        self.assertEqual(normalise_timestamp(""), "")
        self.assertEqual(normalise_timestamp("invalid-date-format"), "invalid-date-format")
        self.assertEqual(compute_duration("", "2025-03-15T14:00:00Z"), 0)
        self.assertEqual(compute_duration(None, None), 0)

        events = [
            {"timestamp": None, "msg": "no timestamp"},
            {"timestamp": "invalid", "msg": "invalid timestamp"},
            {"timestamp": "2025-03-15T14:00:00Z", "msg": "valid timestamp"},
        ]
        # Should not raise exception
        in_win = events_in_window(events, centre_time="2025-03-15T14:02:00Z", window_minutes=5)
        self.assertEqual(len(in_win), 1)

        gaps = detect_gaps(events, min_gap_minutes=5)
        self.assertIsInstance(gaps, list)

    def test_correlate_events_with_lag_strict_precedence(self):
        causes = [{"timestamp": "2025-03-15T14:00:00Z", "id": "deploy"}]
        effects = [
            {"timestamp": "2025-03-15T13:50:00Z", "id": "before_deploy"},  # happened BEFORE cause (should be excluded)
            {"timestamp": "2025-03-15T14:10:00Z", "id": "after_deploy"},   # happened AFTER cause (valid lag)
        ]
        pairs = correlate_events_with_lag(causes, effects, max_lag_minutes=60)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["effect_event"]["id"], "after_deploy")
        self.assertEqual(pairs[0]["lag_minutes"], 10.0)

    # -----------------------------------------------------------------------
    # Incident Knowledge Graph Edge Cases
    # -----------------------------------------------------------------------
    def test_graph_cycles_and_isolated_nodes(self):
        graph = IncidentGraph()
        n1 = GraphNode(id="A", node_type=NodeType.COMMIT, label="A")
        n2 = GraphNode(id="B", node_type=NodeType.ALERT, label="B")
        n3 = GraphNode(id="C", node_type=NodeType.SERVICE, label="C")
        n4 = GraphNode(id="D", node_type=NodeType.SERVICE, label="D") # isolated

        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)
        graph.add_node(n4)

        # Create cycle A -> B -> A and path B -> C
        graph.add_edge(GraphEdge(source="A", target="B", relation=EdgeRelation.TRIGGERED_BY))
        graph.add_edge(GraphEdge(source="B", target="A", relation=EdgeRelation.TRIGGERED_BY))
        graph.add_edge(GraphEdge(source="B", target="C", relation=EdgeRelation.AFFECTS_SERVICE))

        # DFS should terminate gracefully without infinite loop on cycles
        paths = graph.find_causal_paths("A", "C", max_depth=4)
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0], ["A", "B", "C"])

        # Blast radius of isolated node D should be empty
        blast = graph.compute_blast_radius("D")
        self.assertEqual(blast, ["D"])

    # -----------------------------------------------------------------------
    # Log Template Miner Edge Cases
    # -----------------------------------------------------------------------
    def test_log_template_miner_edge_cases(self):
        self.assertEqual(extract_log_template(""), "")
        logs = [
            {"timestamp": "2025-03-15T14:00:00Z", "level": "ERROR", "service": "auth", "message": "Failed to connect to 10.0.1.25:5432 with timeout 3000ms"},
            {"timestamp": "2025-03-15T14:01:00Z", "level": "ERROR", "service": "auth", "message": "Failed to connect to 10.0.1.28:5432 with timeout 3000ms"},
            {"timestamp": "", "level": "INFO", "service": "auth", "message": "Health check ok"},
        ]
        clusters = cluster_log_templates(logs)
        self.assertEqual(len(clusters), 2)
        error_cluster = [c for c in clusters if c["level"] == "ERROR"][0]
        self.assertEqual(error_cluster["count"], 2)
        self.assertIn("<IP:PORT>", error_cluster["template"])


if __name__ == "__main__":
    unittest.main()
