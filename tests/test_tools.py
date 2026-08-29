import unittest
from datetime import datetime, timezone
import re

from tools.diff_tools import detect_diff_risk_patterns, build_forensic_diff_markdown
from tools.evidence_tools import check_evidence, find_corroborating_events, assess_causal_chain, rank_hypotheses
from tools.git_tools import parse_commits, find_suspicious_changes, summarise_git_activity
from tools.log_tools import parse_logs, filter_by_severity, find_error_patterns, detect_anomalies, summarise_logs
from tools.template_tools import check_blameless_language, validate_report_completeness, get_postmortem_template
from tools.time_tools import normalise_timestamp, events_in_window, correlate_events, detect_gaps, compute_duration


class TestDiffTools(unittest.TestCase):
    def test_detect_diff_risk_patterns(self):
        # 1. Connection pool leak
        diff_1 = "removed timeout settings in connection pool"
        risks_1 = detect_diff_risk_patterns(diff_1)
        self.assertTrue(any(r["risk_type"] == "leak_vulnerability" for r in risks_1))

        # 2. Concurrency
        diff_2 = "use mutex and lock for async operations"
        risks_2 = detect_diff_risk_patterns(diff_2)
        self.assertTrue(any(r["risk_type"] == "concurrency_flaw" for r in risks_2))

        # 3. Cache / memory growth
        diff_3 = "introduced unbounded memoize cache without ttl"
        risks_3 = detect_diff_risk_patterns(diff_3)
        self.assertTrue(any(r["risk_type"] == "memory_leak" for r in risks_3))

        # 4. DB latency / join
        diff_4 = "performed unindexed join query and select *"
        risks_4 = detect_diff_risk_patterns(diff_4)
        self.assertTrue(any(r["risk_type"] == "performance_degradation" for r in risks_4))

        # 5. Suppressed error
        diff_5 = "except: pass statement in removed try block"
        risks_5 = detect_diff_risk_patterns(diff_5)
        self.assertTrue(any(r["risk_type"] == "resilience_gap" for r in risks_5))

    def test_build_forensic_diff_markdown(self):
        commit = {
            "sha": "a1b2c3d4e5f6",
            "author": "Alice",
            "message": "remove database connection pool limits",
            "files_changed": ["config.py"]
        }
        md = build_forensic_diff_markdown(
            culprit_commit=commit,
            culprit_file="config.py",
            problematic_diff="- pool.timeout = 5\n+ pool.timeout = None",
            remediation_diff="+ pool.timeout = 5",
            line_annotations=["Line 1: Timeout removed"]
        )
        self.assertIn("a1b2c3d", md)
        self.assertIn("Alice", md)
        self.assertIn("config.py", md)
        self.assertIn("Timeout removed", md)
        self.assertIn("Preventative Remediation Patch", md)


class TestEvidenceTools(unittest.TestCase):
    def test_check_evidence(self):
        events = [
            {"timestamp": "2025-03-15T14:02:45Z", "source": "git", "description": "Deploy v2.14.0 completed", "evidence": "commit a1b2c3d"},
            {"timestamp": "2025-03-15T14:30:12Z", "source": "logs", "description": "503 error database pool timeout", "evidence": "log line 40"},
        ]
        
        # Test keyword matching & support level
        res_strong = check_evidence("Deploy v2.14.0 and database pool 503 error", events)
        self.assertIn(res_strong["support_level"], ("strong", "partial"))
        self.assertGreater(res_strong["match_count"], 0)
        self.assertIn("deploy", res_strong["matched_keywords"])

        res_unsupported = check_evidence("unrelated random terms check", events)
        self.assertEqual(res_unsupported["support_level"], "unsupported")

    def test_find_corroborating_events(self):
        events = [
            {"timestamp": "2025-03-15T14:00:00Z", "source": "logs", "description": "Database connection pool exhausted: 503 error", "evidence": "log line 12"},
            {"timestamp": "2025-03-15T14:15:00Z", "source": "git", "description": "Deploy v2.14.0 completed", "evidence": "commit abc"},
        ]
        
        # Test deploy contradiction where errors started before deploy
        res = find_corroborating_events("deploy database release", events)
        self.assertEqual(len(res["contradicting_signals"]), 1)
        self.assertIn("Errors began before the deploy", res["contradicting_signals"][0]["signal"])

    def test_assess_causal_chain(self):
        events = [
            {"timestamp": "2025-03-15T14:00:00Z", "source": "git", "description": "Deploy v2.14.0 config migration", "evidence": "abc"},
            {"timestamp": "2025-03-15T14:10:00Z", "source": "logs", "description": "503 database pool exhausted", "evidence": "log"},
        ]
        
        chain = [
            {"event": "Deploy v2.14.0", "evidence": "deploy completed"},
            {"event": "503 database pool exhausted", "evidence": "log entries"}
        ]
        
        res = assess_causal_chain(chain, events)
        self.assertTrue(res["chain_valid"])
        self.assertEqual(res["overall_confidence"], "high")
        self.assertEqual(len(res["issues"]), 0)

        bad_chain = [
            {"event": "Deploy v2.14.0", "evidence": "deploy completed"},
            {"event": "Random unreferenced event in space", "evidence": "none"}
        ]
        res_bad = assess_causal_chain(bad_chain, events)
        self.assertEqual(res_bad["overall_confidence"], "medium")
        self.assertEqual(len(res_bad["issues"]), 1)

    def test_rank_hypotheses(self):
        events = [
            {"timestamp": "2025-03-15T14:00:00Z", "source": "git", "description": "Deploy v2.14.0 config migration timeout limit", "evidence": "abc"},
            {"timestamp": "2025-03-15T14:10:00Z", "source": "logs", "description": "503 database pool exhausted", "evidence": "log"},
        ]
        hypotheses = [
            "Deploy v2.14.0 migration changed timeout limit",
            "Random memory leak in worker processes"
        ]
        ranked = rank_hypotheses(hypotheses, events)
        self.assertEqual(ranked[0]["hypothesis"], "Deploy v2.14.0 migration changed timeout limit")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])


class TestGitTools(unittest.TestCase):
    def test_parse_commits(self):
        raw = [
            {"sha": "222", "timestamp": "2025-03-15T14:10:00Z", "author": "Bob", "message": "second"},
            {"sha": "111", "timestamp": "2025-03-15T14:00:00Z", "author": "Alice", "message": "first"},
        ]
        parsed = parse_commits(raw)
        self.assertEqual(parsed[0]["sha"], "111")
        self.assertEqual(parsed[1]["sha"], "222")

    def test_find_suspicious_changes(self):
        commits = [
            {"sha": "abc", "timestamp": "2025-03-15T10:00:00Z", "author": "Alice", "message": "update config settings", "files_changed": ["src/config.py"], "diff_summary": "timeout limit changes"},
            {"sha": "def", "timestamp": "2025-03-15T13:50:00Z", "author": "Bob", "message": "refactor code migration", "files_changed": ["src/db/migration.sql"], "diff_summary": "db changes"},
            {"sha": "xyz", "timestamp": "2025-03-14T08:00:00Z", "author": "Bob", "message": "early commit", "files_changed": ["readme.md"], "diff_summary": "docs"}
        ]
        
        # Test filtering based on time window
        suspicious = find_suspicious_changes(commits, incident_time="2025-03-15T14:00:00Z", window_hours=12)
        # xyz is too early, so only abc and def should be returned
        shas = [c["sha"] for c in suspicious]
        self.assertIn("abc", shas)
        self.assertIn("def", shas)
        self.assertNotIn("xyz", shas)
        
        # Risk assessment test
        self.assertEqual(suspicious[0]["sha"], "def")  # migration + refactor + db has high risk score
        self.assertIn("Includes database migration", suspicious[0]["risk_factors"])

    def test_summarise_git_activity(self):
        commits = [
            {"sha": "111", "timestamp": "2025-03-15T14:00:00Z", "author": "Alice", "files_changed": ["a.py"]},
            {"sha": "222", "timestamp": "2025-03-15T14:10:00Z", "author": "Bob", "files_changed": ["b.py", "a.py"]},
        ]
        summary = summarise_git_activity(commits)
        self.assertEqual(summary["total_commits"], 2)
        self.assertCountEqual(summary["authors"], ["Alice", "Bob"])
        self.assertCountEqual(summary["files_touched"], ["a.py", "b.py"])


class TestLogTools(unittest.TestCase):
    def test_parse_logs(self):
        raw = [
            {"timestamp": "2025-03-15T14:10:00Z", "level": "error", "service": "srv-b", "message": "err"},
            {"timestamp": "2025-03-15T14:00:00Z", "level": "info", "service": "srv-a", "message": "msg"},
        ]
        parsed = parse_logs(raw)
        self.assertEqual(parsed[0]["timestamp"], "2025-03-15T14:00:00Z")
        self.assertEqual(parsed[1]["level"], "ERROR")

    def test_filter_by_severity(self):
        logs = [
            {"level": "DEBUG"},
            {"level": "INFO"},
            {"level": "WARN"},
            {"level": "ERROR"},
            {"level": "FATAL"},
        ]
        self.assertEqual(len(filter_by_severity(logs, "WARN")), 3)
        self.assertEqual(len(filter_by_severity(logs, "FATAL")), 1)

    def test_find_error_patterns(self):
        logs = [
            {"level": "ERROR", "timestamp": "2025-03-15T14:00:00Z", "service": "user", "message": "failed to connect to db with uuid abcdef12"},
            {"level": "ERROR", "timestamp": "2025-03-15T14:01:00Z", "service": "user", "message": "failed to connect to db with uuid 98765432"},
        ]
        patterns = find_error_patterns(logs)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0]["count"], 2)
        self.assertIn("<ID>", patterns[0]["pattern"])

    def test_detect_anomalies(self):
        logs = [
            {"level": "INFO", "timestamp": "2025-03-15T14:00:00Z", "service": "user-service", "message": "healthy"},
            {"level": "ERROR", "timestamp": "2025-03-15T14:00:10Z", "service": "user-service", "message": "crash"},
            {"level": "ERROR", "timestamp": "2025-03-15T14:01:00Z", "service": "user-service", "message": "crash"},
            {"level": "ERROR", "timestamp": "2025-03-15T14:01:05Z", "service": "user-service", "message": "crash"},
            {"level": "ERROR", "timestamp": "2025-03-15T14:01:10Z", "service": "user-service", "message": "crash"},
            {"level": "ERROR", "timestamp": "2025-03-15T14:01:15Z", "service": "user-service", "message": "crash"},
        ]
        anomalies = detect_anomalies(logs)
        self.assertTrue(any(a["type"] == "service_degradation" for a in anomalies))
        self.assertTrue(any(a["type"] == "error_spike" for a in anomalies))

    def test_summarise_logs(self):
        logs = [
            {"level": "INFO", "service": "user", "timestamp": "2025-03-15T14:00:00Z"},
            {"level": "ERROR", "service": "checkout", "timestamp": "2025-03-15T14:10:00Z"},
        ]
        summary = summarise_logs(logs)
        self.assertEqual(summary["total_entries"], 2)
        self.assertEqual(summary["level_distribution"]["INFO"], 1)
        self.assertEqual(summary["level_distribution"]["ERROR"], 1)
        self.assertEqual(summary["services"]["checkout"], 1)


class TestTemplateTools(unittest.TestCase):
    def test_check_blameless_language(self):
        text_with_blame = "The developer forgot to configure pool settings and broke the system."
        res = check_blameless_language(text_with_blame)
        self.assertLess(res["score"], 100)
        self.assertGreater(len(res["violations"]), 0)
        self.assertIn("was not part of the checklist", res["violations"][0]["suggestion"])

        text_blameless = "A configuration change was deployed without database timeout limits, contributing to pool exhaustion."
        res_blameless = check_blameless_language(text_blameless)
        self.assertEqual(res_blameless["score"], 100)
        self.assertEqual(len(res_blameless["violations"]), 0)

    def test_validate_report_completeness(self):
        bad_report = "## Executive Summary\nShort brief.\n## Impact\nNone."
        res = validate_report_completeness(bad_report)
        self.assertLess(res["score"], 50)
        self.assertIn("Timeline", res["missing"])

        good_report = """
## Executive Summary
This is a summary of the database outage. It explains what happened in details.
## Impact
Affected user-service and checkouts. It caused significant damage.
## Timeline
| Time | Event |
|---|---|
| 14:00 | Outage occurred today |
## Root Cause
A timeout configuration was omitted from the deploy.
## Contributing Factors
- Missing CI tests in our pipeline that should validate configurations.
## Resolution
Restored timeout settings in production immediately.
## Action Items
| Priority | Action |
|---|---|
| P0 | Add CI config linting |
## Lessons Learned
- Validate configs properly in CI.
"""
        res_good = validate_report_completeness(good_report)
        self.assertEqual(res_good["score"], 100)

    def test_get_postmortem_template(self):
        template = get_postmortem_template()
        self.assertIn("Executive Summary", template)
        self.assertIn("shields.io", template)


class TestTimeTools(unittest.TestCase):
    def test_normalise_timestamp(self):
        self.assertEqual(normalise_timestamp("2025-03-15T14:30:00Z"), "2025-03-15T14:30:00Z")
        self.assertEqual(normalise_timestamp("2025-03-15T14:30:00+00:00"), "2025-03-15T14:30:00Z")

    def test_events_in_window(self):
        events = [
            {"timestamp": "2025-03-15T13:50:00Z"},
            {"timestamp": "2025-03-15T14:04:00Z"},
            {"timestamp": "2025-03-15T14:20:00Z"},
        ]
        in_window = events_in_window(events, "2025-03-15T14:05:00Z", window_minutes=5)
        self.assertEqual(len(in_window), 1)
        self.assertEqual(in_window[0]["timestamp"], "2025-03-15T14:04:00Z")

    def test_correlate_events(self):
        events_a = [{"timestamp": "2025-03-15T14:00:00Z", "name": "a"}]
        events_b = [
            {"timestamp": "2025-03-15T14:02:00Z", "name": "b1"},
            {"timestamp": "2025-03-15T14:15:00Z", "name": "b2"},
        ]
        correlated = correlate_events(events_a, events_b, window_minutes=5)
        self.assertEqual(len(correlated), 1)
        self.assertEqual(correlated[0]["event_b"]["name"], "b1")
        self.assertEqual(correlated[0]["time_delta_seconds"], 120.0)

    def test_detect_gaps(self):
        events = [
            {"timestamp": "2025-03-15T14:00:00Z"},
            {"timestamp": "2025-03-15T14:05:00Z"},
            {"timestamp": "2025-03-15T14:25:00Z"},
        ]
        gaps = detect_gaps(events, min_gap_minutes=10)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["gap_start"], "2025-03-15T14:05:00Z")
        self.assertEqual(gaps[0]["gap_end"], "2025-03-15T14:25:00Z")
        self.assertEqual(gaps[0]["duration_minutes"], 20.0)

    def test_compute_duration(self):
        self.assertEqual(compute_duration("2025-03-15T14:00:00Z", "2025-03-15T14:15:30Z"), 15)
        self.assertEqual(compute_duration("2025-03-15T14:30:00Z", "2025-03-15T14:10:00Z"), 0)


if __name__ == "__main__":
    unittest.main()
