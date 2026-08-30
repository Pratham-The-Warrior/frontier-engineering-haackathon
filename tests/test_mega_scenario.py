"""
Mega Scenario Validation Test — INC-011.

Validates the full enterprise pipeline on a large-scale 1,000+ log, multi-service,
multi-participant production outage with secret injection, entity resolution,
Drain3 template mining, and knowledge graph causal path tracing.
"""

import json
import os
import unittest

from agents.orchestrator import run_pipeline
from collectors.log_collector import cluster_log_templates
from tools.sanitizer import sanitize_dict, sanitize_text
from tools.entity_resolver import EntityResolver
from models.canonical_event import EntityRegistry
from models.incident_graph import IncidentGraph, GraphNode, GraphEdge, NodeType, EdgeRelation


class TestMegaScenario(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["USE_MOCK_LLM"] = "true"
        cls.incident_dir = os.path.join(
            os.path.dirname(__file__), "..", "data", "incidents", "incident_11_mega_payment_outage"
        )
        # Run the full pipeline on INC-011
        cls.pipeline_result = run_pipeline(cls.incident_dir, verbose=False)

    def test_pipeline_execution_successful(self):
        self.assertEqual(self.pipeline_result["incident_id"], "INC-011")
        self.assertIn("Global Payment Outage", self.pipeline_result["incident_title"])
        self.assertTrue(len(self.pipeline_result["report_markdown"]) > 500)
        self.assertTrue(len(self.pipeline_result["trajectory"]) > 0)

    def test_zero_trust_secret_scrubbing(self):
        # Ensure that no raw passwords or AWS keys from the 1,000+ logs leaked into output
        report = self.pipeline_result["report_markdown"]
        context_str = json.dumps(self.pipeline_result["context_snapshot"])
        trajectory_str = json.dumps(self.pipeline_result["trajectory"])

        # Check injected raw credentials are NOT present anywhere in memory or output
        for text in [report, context_str, trajectory_str]:
            self.assertNotIn("SuperSecretPostgresPass123!", text)
            self.assertNotIn("AKIAIOSFODNN7EXAMPLE", text)
            self.assertNotIn("ghp_1234567890abcdefghijklmnopqrstuvwxyz12", text)

    def test_drain3_log_template_clustering(self):
        with open(os.path.join(self.incident_dir, "logs.jsonl"), "r", encoding="utf-8") as f:
            logs = json.load(f)

        clusters = cluster_log_templates(logs, min_count=5)
        # Verify high-volume logs were clustered into distinct invariant templates
        self.assertTrue(len(clusters) >= 3)
        
        templates = [c["template"] for c in clusters]
        has_deadlock = any("DeadlockDetected" in t for t in templates)
        has_rebalance = any("CommitFailedException" in t for t in templates)
        has_timeout = any("ConnectionPoolTimeoutException" in t for t in templates)

        self.assertTrue(has_deadlock)
        self.assertTrue(has_rebalance)
        self.assertTrue(has_timeout)

    def test_mmer_entity_resolution(self):
        registry = EntityRegistry()
        resolver = EntityResolver(registry)

        with open(os.path.join(self.incident_dir, "slack_thread.json"), "r", encoding="utf-8") as f:
            slack_data = json.load(f)
        with open(os.path.join(self.incident_dir, "git_commits.json"), "r", encoding="utf-8") as f:
            git_data = json.load(f)

        incident_data = {
            "slack_thread.json": slack_data,
            "git_commits.json": git_data,
            "logs.jsonl": [],
        }
        resolver.populate_from_incident_data(incident_data)

        # Check Sarah Chen resolved across platforms
        sarah = resolver.resolve_actor_from_signal("Sarah Chen")
        self.assertIsNotNone(sarah)
        self.assertEqual(sarah.actor_id, "sarah_chen")

        # Check Dave Kumar resolved from git author and Slack
        dave = resolver.resolve_actor_from_signal("Dave Kumar")
        self.assertIsNotNone(dave)
        self.assertEqual(dave.actor_id, "dave_kumar")

    def test_knowledge_graph_and_causal_path(self):
        ctx = self.pipeline_result["context_snapshot"]
        # Verify canonical events and graph were populated from 1,000+ events
        self.assertTrue(ctx["total_timeline_events"] > 0)
        self.assertTrue(ctx["total_canonical_events"] >= 1000)
        self.assertTrue(ctx["graph_summary"]["total_nodes"] >= 1000)
        self.assertIn("payment-gateway", ctx["registered_services"])


if __name__ == "__main__":
    unittest.main()
