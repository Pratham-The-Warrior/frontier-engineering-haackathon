import unittest
from unittest.mock import patch, MagicMock

import agents.llm_client
from agents.incident_context import Finding, IncidentContext
from agents.llm_client import call_llm, call_llm_json
from agents import log_parser, comms_analyzer, git_analyzer, timeline_builder, root_cause_analyzer, report_writer


class TestIncidentContext(unittest.TestCase):
    def test_add_finding_and_query(self):
        context = IncidentContext(incident_id="INC-001", incident_title="DB Exhaustion")
        
        context.add_finding(
            source_agent="log_parser",
            category="error",
            summary="connection pool exhausted",
            detail="critical DB error details",
            timestamp="2025-03-15T14:00:00Z",
            severity="critical",
            metadata={"pool_size": 20}
        )
        context.add_finding(
            source_agent="comms_analyzer",
            category="decision",
            summary="roll back version",
            severity="info"
        )

        # Check total findings
        findings = context.get_all_findings()
        self.assertEqual(len(findings), 2)

        # Check queries with filters
        log_findings = context.query(source_agent="log_parser")
        self.assertEqual(len(log_findings), 1)
        self.assertEqual(log_findings[0]["summary"], "connection pool exhausted")

        crit_findings = context.get_critical_findings()
        self.assertEqual(len(crit_findings), 1)
        self.assertEqual(crit_findings[0]["severity"], "critical")

        dec_findings = context.query(category="decision")
        self.assertEqual(len(dec_findings), 1)
        self.assertEqual(dec_findings[0]["source_agent"], "comms_analyzer")

        kw_findings = context.query(keyword="roll back")
        self.assertEqual(len(kw_findings), 1)

    def test_timeline_events(self):
        context = IncidentContext()
        context.add_timeline_event(
            timestamp="2025-03-15T14:10:00Z",
            source="logs",
            description="DB failure",
            evidence="log line 10",
            category="error"
        )
        context.add_timeline_event(
            timestamp="2025-03-15T14:00:00Z",
            source="git",
            description="Deploy completed",
            evidence="commit abc",
            category="deploy"
        )

        timeline = context.get_timeline()
        self.assertEqual(timeline[0]["timestamp"], "2025-03-15T14:00:00Z")
        self.assertEqual(timeline[1]["timestamp"], "2025-03-15T14:10:00Z")

    def test_agent_summaries(self):
        context = IncidentContext()
        context.set_agent_summary("log_parser", "Logs showed DB timeout.")
        self.assertEqual(context.get_agent_summaries()["log_parser"], "Logs showed DB timeout.")

    def test_snapshot(self):
        context = IncidentContext(incident_id="INC-001", incident_title="DB Exhaustion")
        context.add_finding(source_agent="log_parser", category="error", summary="err", severity="critical")
        context.add_timeline_event("2025", "logs", "desc")
        context.set_agent_summary("log_parser", "summary")
        
        snapshot = context.snapshot()
        self.assertEqual(snapshot["incident_id"], "INC-001")
        self.assertEqual(snapshot["total_findings"], 1)
        self.assertEqual(snapshot["total_timeline_events"], 1)


class TestLlmClient(unittest.TestCase):
    @patch("agents.llm_client._get_client")
    def test_call_llm(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello World"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        mock_client.chat.completions.create.return_value = mock_response

        res = call_llm("System prompt", "User prompt", model="gpt-4o")
        self.assertEqual(res["content"], "Hello World")
        self.assertEqual(res["usage"]["total_tokens"], 15)
        self.assertEqual(res["retries_used"], 0)

    @patch("agents.llm_client.call_llm")
    def test_call_llm_json(self, mock_call_llm):
        mock_call_llm.return_value = {
            "content": '{"key": "value"}',
            "model": "gpt-4o",
            "usage": {"total_tokens": 15},
            "latency_seconds": 1.0,
            "retries_used": 0
        }
        res = call_llm_json("System prompt", "User prompt")
        self.assertEqual(res["parsed"]["key"], "value")

        # Test markdown code block extraction fallback
        mock_call_llm.return_value["content"] = "```json\n{\n  \"key\": \"value2\"\n}\n```"
        res_fallback = call_llm_json("System prompt", "User prompt")
        self.assertEqual(res_fallback["parsed"]["key"], "value2")


class TestAgentsRun(unittest.TestCase):
    @patch("agents.log_parser.call_llm_json")
    def test_log_parser(self, mock_llm_json):
        mock_llm_json.return_value = {
            "model": "gpt-4o-mini",
            "usage": {"total_tokens": 10},
            "latency_seconds": 0.5,
            "parsed": {
                "key_errors": [{"timestamp": "2025-03-15T14:00:00Z", "service": "user", "message": "error", "significance": "critical"}],
                "error_timeline": [],
                "services_affected": ["user"],
                "first_error_timestamp": "2025-03-15T14:00:00Z",
                "probable_trigger": "deploy",
                "log_summary": "DB error."
            }
        }
        logs = [{"timestamp": "2025-03-15T14:00:00Z", "level": "ERROR", "service": "user", "message": "error"}]
        res = log_parser.run(logs)
        self.assertEqual(res["first_error_timestamp"], "2025-03-15T14:00:00Z")
        self.assertEqual(res["services_affected"], ["user"])

    @patch("agents.comms_analyzer.call_llm_json")
    def test_comms_analyzer(self, mock_llm_json):
        mock_llm_json.return_value = {
            "model": "gpt-4o-mini",
            "usage": {"total_tokens": 10},
            "latency_seconds": 0.5,
            "parsed": {
                "participants": [],
                "key_decisions": [{"timestamp": "14:05", "decision": "rollback", "made_by": "Alice", "rationale": "outage"}],
                "manual_actions": [],
                "communication_timeline": [],
                "investigation_path": "path",
                "time_to_identify_minutes": "5",
                "comms_summary": "summary"
            }
        }
        slack = [{"timestamp": "14:00", "user": "Alice", "role": "SRE", "message": "outage!"}]
        res = comms_analyzer.run(slack)
        self.assertEqual(res["key_decisions"][0]["made_by"], "Alice")

    @patch("agents.git_analyzer.call_llm_json")
    def test_git_analyzer(self, mock_llm_json):
        mock_llm_json.return_value = {
            "model": "gpt-4o",
            "usage": {"total_tokens": 10},
            "latency_seconds": 0.5,
            "parsed": {
                "suspicious_commits": [],
                "deploy_timeline": [],
                "most_likely_culprit": {"sha": "abc", "primary_file": "schema.py", "reason": "omitted timeout"},
                "forensic_code_diff": {},
                "git_summary": "summary"
            }
        }
        commits = [{"sha": "abc", "timestamp": "2025-03-15T13:30:00Z", "author": "Bob", "message": "deploy", "files_changed": ["schema.py"]}]
        res = git_analyzer.run(commits, incident_time="2025-03-15T14:00:00Z")
        self.assertEqual(res["most_likely_culprit"]["sha"], "abc")

    @patch("agents.timeline_builder.call_llm_json")
    def test_timeline_builder(self, mock_llm_json):
        mock_llm_json.return_value = {
            "model": "gpt-4o",
            "usage": {"total_tokens": 10},
            "latency_seconds": 0.5,
            "parsed": {
                "unified_timeline": [
                    {"timestamp": "2025-03-15T14:00:00Z", "source": "logs", "category": "impact", "description": "errors start", "evidence": "log", "significance": "start"}
                ],
                "incident_phases": {},
                "cross_source_correlations": [],
                "timeline_gaps": [],
                "narrative_summary": "summary"
            }
        }
        log_findings = {"error_timeline": []}
        comms_findings = {"communication_timeline": []}
        git_findings = {"deploy_timeline": []}
        res = timeline_builder.run(log_findings, comms_findings, git_findings)
        self.assertEqual(res["unified_timeline"][0]["source"], "logs")


if __name__ == "__main__":
    unittest.main()
