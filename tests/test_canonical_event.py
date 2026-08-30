"""
Unit tests for Universal Canonical Incident Event (UCIE) and Entity Registry.
"""

import unittest
from models.canonical_event import (
    CanonicalEvent,
    EventSourceType,
    EventSeverity,
    ActorEntity,
    ServiceEntity,
    EntityRegistry,
)


class TestCanonicalEvent(unittest.TestCase):

    def test_canonical_event_creation_and_deterministic_id(self):
        id1 = CanonicalEvent.generate_deterministic_id("github", "7a8b9c", "2025-03-15T14:00:00Z")
        id2 = CanonicalEvent.generate_deterministic_id("github", "7a8b9c", "2025-03-15T14:00:00Z")
        id3 = CanonicalEvent.generate_deterministic_id("slack", "7a8b9c", "2025-03-15T14:00:00Z")

        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)

        evt = CanonicalEvent(
            event_id=id1,
            source_type=EventSourceType.GITHUB_COMMIT,
            source_system="github.com/org/repo",
            event_timestamp="2025-03-15T14:00:00Z",
            severity=EventSeverity.HIGH,
            category="deploy",
            title="Commit 7a8b9c: Bump db pool size",
            entity_refs=["commit:7a8b9c", "ticket:PROD-100"],
            service_refs=["auth-service"],
        )
        self.assertEqual(evt.source_type, EventSourceType.GITHUB_COMMIT)
        self.assertEqual(evt.severity, EventSeverity.HIGH)
        self.assertIn("auth-service", evt.service_refs)


if __name__ == "__main__":
    unittest.main()
