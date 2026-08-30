"""
Unit tests for the Entity Resolver (MMER).
"""

import unittest
from tools.entity_resolver import EntityResolver
from models.canonical_event import EntityRegistry


class TestEntityResolver(unittest.TestCase):

    def setUp(self):
        self.registry = EntityRegistry()
        self.resolver = EntityResolver(self.registry)

    def test_actor_resolution_and_clustering(self):
        # Register known actor
        actor = self.resolver.register_known_actor(
            actor_id="sarah_chen",
            display_name="Sarah Chen",
            email="sarah.chen@enterprise.com",
            role="Staff SRE",
            platform_ids={"slack": "U12345", "github": "sarah-c"},
        )
        
        # Test resolving from Slack handle
        res_slack = self.resolver.resolve_actor_from_signal("U12345", platform="slack")
        self.assertIsNotNone(res_slack)
        self.assertEqual(res_slack.actor_id, "sarah_chen")
        
        # Test resolving from GitHub handle
        res_gh = self.resolver.resolve_actor_from_signal("sarah-c", platform="github")
        self.assertIsNotNone(res_gh)
        self.assertEqual(res_gh.actor_id, "sarah_chen")

        # Test resolving from name
        res_name = self.resolver.resolve_actor_from_signal("Sarah Chen")
        self.assertIsNotNone(res_name)
        self.assertEqual(res_name.actor_id, "sarah_chen")

    def test_service_alias_resolution(self):
        self.resolver.register_known_service(
            service_id="auth-service",
            display_name="Authentication Service",
            aliases=["auth-svc", "auth_service", "AUTH", "services/auth"],
        )

        res1 = self.resolver.resolve_service_from_signal("auth-svc")
        self.assertIsNotNone(res1)
        self.assertEqual(res1.service_id, "auth-service")

        res2 = self.resolver.resolve_service_from_signal("services/auth")
        self.assertIsNotNone(res2)
        self.assertEqual(res2.service_id, "auth-service")

    def test_extract_entity_references(self):
        text = "Fixes PROD-1029 and INC-842, see PR #42 and commit 7a8b9c1 for details."
        refs = self.resolver.extract_entity_references(text)
        self.assertIn("ticket:PROD-1029", refs)
        self.assertIn("ticket:INC-842", refs)
        self.assertIn("pr:#42", refs)
        self.assertIn("commit:7a8b9c1", refs)


if __name__ == "__main__":
    unittest.main()
