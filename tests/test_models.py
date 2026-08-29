import unittest
from models.incident import LogEntry, SlackMessage, GitCommit, Alert, GroundTruth, IncidentData
from models.report import ActionItem, PostMortemReport
from models.timeline import TimelineEvent, Timeline


class TestIncidentModels(unittest.TestCase):
    def test_log_entry_parsing(self):
        data = {
            "timestamp": "2025-03-15T14:00:00Z",
            "level": "ERROR",
            "service": "user-service",
            "message": "connection pool exhausted",
            "metadata": {"pool_size": 20}
        }
        entry = LogEntry(**data)
        self.assertEqual(entry.timestamp, "2025-03-15T14:00:00Z")
        self.assertEqual(entry.level, "ERROR")
        self.assertEqual(entry.service, "user-service")
        self.assertEqual(entry.message, "connection pool exhausted")
        self.assertEqual(entry.metadata["pool_size"], 20)

    def test_slack_message_parsing(self):
        data = {
            "timestamp": "2025-03-15T14:05:00Z",
            "user": "Alice",
            "role": "SRE",
            "message": "Investigating user-service errors."
        }
        msg = SlackMessage(**data)
        self.assertEqual(msg.user, "Alice")
        self.assertEqual(msg.role, "SRE")

    def test_git_commit_parsing(self):
        data = {
            "sha": "a1b2c3d4",
            "timestamp": "2025-03-15T13:30:00Z",
            "author": "Bob",
            "message": "remove timeouts",
            "files_changed": ["config.py"],
            "diff_summary": "- timeout = 5\n+ timeout = None"
        }
        commit = GitCommit(**data)
        self.assertEqual(commit.sha, "a1b2c3d4")
        self.assertEqual(commit.files_changed, ["config.py"])

    def test_alert_parsing(self):
        data = {
            "timestamp": "2025-03-15T14:01:00Z",
            "severity": "critical",
            "source": "PagerDuty",
            "title": "Database pool exhausted",
            "description": "Database connections have reached 100%"
        }
        alert = Alert(**data)
        self.assertEqual(alert.source, "PagerDuty")
        self.assertEqual(alert.severity, "critical")

    def test_ground_truth_parsing(self):
        data = {
            "root_cause": "Omitted timeout limits in deploy",
            "root_cause_category": "configuration",
            "contributing_factors": ["No config validation in CI"],
            "key_timeline_events": [
                {"timestamp": "2025-03-15T14:00:00Z", "description": "Outage start"}
            ],
            "severity": "SEV1",
            "impact_summary": "2000 users affected",
            "resolution": "Rollback config change",
            "duration_minutes": 18
        }
        gt = GroundTruth(**data)
        self.assertEqual(gt.root_cause_category, "configuration")
        self.assertEqual(gt.duration_minutes, 18)


class TestReportModels(unittest.TestCase):
    def test_postmortem_report_to_markdown(self):
        report = PostMortemReport(
            title="Database Connection Pool Exhaustion",
            date="2025-03-15",
            severity="SEV1",
            authors=["Alice", "Bob"],
            executive_summary="Database connection pool was exhausted due to config removal.",
            impact_summary="2,000 failed requests with HTTP 503.",
            affected_services=["user-service", "checkout-service"],
            affected_users="~2,000 requests",
            duration="18 minutes",
            timeline_markdown="| Time | Event |\n|---|---|",
            root_cause="Database connection pool timeout omitted in config schema migration.",
            contributing_factors=["Missing config validation in CI"],
            resolution="Restored timeout via hotfix v2.14.1.",
            action_items=[
                ActionItem(description="Add CI validation", priority="P0", owner="backend", type="prevent")
            ],
            lessons_learned=["Validate configurations in CI."],
            what_went_well=["Incident identified within 3 mins."],
            what_could_be_improved=["Earlier alerting on pool usage."]
        )
        md = report.to_markdown()
        self.assertIn("Database Connection Pool Exhaustion", md)
        self.assertIn("Alice, Bob", md)
        self.assertIn("user-service, checkout-service", md)
        self.assertIn("P0 | prevent | Add CI validation | backend", md)
        self.assertIn("Lessons Learned", md)


class TestTimelineModels(unittest.TestCase):
    def test_timeline_operations(self):
        timeline = Timeline()
        event_1 = TimelineEvent(
            timestamp="2025-03-15T14:10:00Z",
            source="logs",
            category="error",
            description="503 database pool exhausted",
            evidence="log line 10"
        )
        event_2 = TimelineEvent(
            timestamp="2025-03-15T14:00:00Z",
            source="git",
            category="deploy",
            description="Deploy completed",
            evidence="commit abc"
        )

        timeline.add_event(event_1)
        timeline.add_event(event_2)

        # Check sorting (earlier event first)
        self.assertEqual(timeline.events[0].timestamp, "2025-03-15T14:00:00Z")
        self.assertEqual(timeline.events[1].timestamp, "2025-03-15T14:10:00Z")

        # Check filtering
        git_events = timeline.get_events_by_source("git")
        self.assertEqual(len(git_events), 1)
        self.assertEqual(git_events[0].category, "deploy")

        error_events = timeline.get_events_by_category("error")
        self.assertEqual(len(error_events), 1)
        self.assertEqual(error_events[0].source, "logs")

        # Check markdown generation
        md = timeline.to_markdown()
        self.assertIn("| 2025-03-15T14:00:00Z | git | deploy | Deploy completed |", md)


if __name__ == "__main__":
    unittest.main()
