"""
Automated unit & integration regression tests.
Can run completely offline without an OpenAI API key.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import patch

import agents.llm_client


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def mock_call_llm(system_prompt, user_prompt, model=None, **kwargs):
    content = """# Post-Mortem: Database Connection Pool Exhaustion

[![Severity](https://img.shields.io/badge/Severity-CRITICAL_P1-e11d48?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-RESOLVED-10b981?style=flat-square)](#)
[![Duration](https://img.shields.io/badge/Duration-18m-6366f1?style=flat-square)](#)
[![Evidence](https://img.shields.io/badge/Evidence-100%25_Grounded-0284c7?style=flat-square)](#)

> **Blast Radius:** ~2,000 requests | **MTTR:** 15 min
> **Root Cause (1-line):** Database connection pool timeout was omitted during a config migration.

---

## <img src="https://api.iconify.design/lucide:gauge.svg?color=%236366f1" width="18"/> Executive Summary
A database connection pool timeout was dropped during deploy v2.14.0, causing pool exhaustion. Service was restored by deploying hotfix v2.14.1.

---

## <img src="https://api.iconify.design/lucide:shield-alert.svg?color=%23f59e0b" width="18"/> Risk & Systemic Vulnerability Assessment
| Risk Dimension | Risk Level | Finding | Evidence |
|:---|:---:|:---|:---|
| **Deploy Safety** | [![High](https://img.shields.io/badge/HIGH-f97316?style=flat-square)](#) | Config migration lacked CI checks `[Git:a1b2c3d]` |
| **Observability** | [![Low](https://img.shields.io/badge/LOW-22c55e?style=flat-square)](#) | Pool usage alert fired in 90s `[Alert:db-pool]` |

---

## <img src="https://api.iconify.design/lucide:activity.svg?color=%2306b6d4" width="18"/> Impact
**Affected Services:** user-service, checkout-service
**User Impact:** 2,000 failed requests with HTTP 503 `[Log:14:30:12]`
**Duration:** 18 minutes

---

## <img src="https://api.iconify.design/lucide:clock.svg?color=%2364748b" width="18"/> Timeline
| Time (UTC) | Source | Event |
|:---|:---|:---|
| 14:02:45 | `[Git:a1b2c3d]` | Deploy v2.14.0 completed `[Deploy:v2.14.0]` |
| 14:30:12 | `[Log:14:30:12]` | First 503 errors reported `[Log:user-service:14:30]` |

---

## <img src="https://api.iconify.design/lucide:search.svg?color=%23e11d48" width="18"/> Root Cause Analysis
**Root Cause:** Config migration dropped connection timeout parameters.
**Causal Chain:**
1. Deploy v2.14.0 removed pool timeouts `[Git:a1b2c3d]`
2. Connections remained open indefinitely `[Log:14:30:12]`
3. Pool exhausted causing 503s `[Alert:db-pool]`

---

### <img src="https://api.iconify.design/lucide:file-code-2.svg?color=%238b5cf6" width="18"/> Forensic Code Analysis (Root Cause Diff)

> **Commit:** [`a1b2c3d`] | **Author:** `Mike Torres` | **Primary File:** `src/config/schema.py`

```diff
- async with db.acquire(timeout=5.0) as conn:
+ conn = await db.acquire()  # [CAUSE: dropped timeout allows connections to hang]
```

#### Preventative Remediation Patch
```diff
+ async with db.acquire(timeout=settings.DB_TIMEOUT) as conn:
```

---

## <img src="https://api.iconify.design/lucide:layers.svg?color=%230ea5e9" width="18"/> Contributing Factors
- Missing schema validation in CI pipeline `[Git:a1b2c3d]`
- Low threshold alerting absent `[Alert:db-pool]`

---

## <img src="https://api.iconify.design/lucide:shield-check.svg?color=%2310b981" width="18"/> Prevention Analysis
| Prevention Point | Safeguard | Expected Outcome |
|:---|:---|:---|
| At PR / CI Stage | Config linter | Prevented before merge |

---

## <img src="https://api.iconify.design/lucide:wrench.svg?color=%2364748b" width="18"/> Resolution
Restored connection pool timeout settings via hotfix v2.14.1 `[Git:q3r4s5t]`.

---

## <img src="https://api.iconify.design/lucide:check-square.svg?color=%2310b981" width="18"/> Action Items
| Priority | Type | Action | Owner | Est. |
|:---|:---|:---|:---|:---|
| **P0** | Prevent | Add CI validation for required database config keys | @backend | 1d |
| **P1** | Detect | Add connection pool alerts at 70% threshold | @sre | 2d |

---

## <img src="https://api.iconify.design/lucide:book-open.svg?color=%236366f1" width="18"/> Lessons Learned
- Configuration migrations must undergo automated schema validation tests.

## What Went Well
- On-call team detected root cause within 3 minutes of triage start.

## What Could Be Improved
- Alerting on pool growth should trigger earlier before full exhaustion.
"""
    return {
        "content": content,
        "model": "gpt-4o",
        "usage": {"total_tokens": 1500, "prompt_tokens": 1000, "completion_tokens": 500},
        "latency_seconds": 1.2,
        "retries_used": 0,
    }


def mock_call_llm_json(system_prompt, user_prompt, model=None, **kwargs):
    raw = mock_call_llm(system_prompt, user_prompt, model=model)
    if "impartial judge" in system_prompt.lower():
        parsed = {"accuracy": "exact", "score": 1.0, "explanation": "Exact match with ground truth root cause."}
    elif "checking whether a post-mortem report's timeline" in system_prompt.lower():
        parsed = {"recall": 1.0, "found_count": 7, "total_count": 7, "events_found": []}
    elif "checking whether a post-mortem report captures the known contributing factors" in system_prompt.lower():
        parsed = {"recall": 1.0, "found_count": 4, "total_count": 4, "factors_found": []}
    elif "hypotheses" in system_prompt.lower() or "hypotheses" in user_prompt.lower():
        parsed = {"hypotheses": ["Hypothesis 1: Config migration dropped timeout", "Hypothesis 2: Query join latency"]}
    elif "root cause analyst" in system_prompt.lower():
        parsed = {
            "root_cause": {
                "summary": "Database connection pool timeout settings were accidentally removed during a config schema migration.",
                "detail": "Detailed explanation of pool exhaustion.",
                "category": "configuration",
                "evidence": ["[Git:a1b2c3d]", "[Log:14:30:12]"],
                "confidence": "high",
                "confidence_justification": "Direct correlation between deploy and error spike.",
            },
            "causal_chain": [
                {"step": 1, "event": "Deploy v2.14.0 config migration", "caused_by": "commit a1b2c3d", "evidence": "[Git:a1b2c3d]"},
                {"step": 2, "event": "Pool exhaustion and 503 errors", "caused_by": "unclosed connections", "evidence": "[Log:14:30:12]"},
            ],
            "contributing_factors": [
                {"factor": "Missing config validation in CI", "type": "testing_gap", "evidence": "[Git:a1b2c3d]"}
            ],
            "blast_radius": {"affected_components": ["user-service"], "impact_severity": "P1", "estimated_user_impact": "2000 requests"},
            "prevention_safeguards": [{"stage": "CI/PR", "safeguard": "Linter", "outcome": "Prevented"}],
        }
    elif "quality reviewer" in system_prompt or "Audit this" in user_prompt:
        parsed = {"issues_found": [], "overall_quality": "good", "refined_root_cause_summary": None}
    elif "timeline" in system_prompt.lower() or "unified" in user_prompt.lower():
        parsed = {
            "unified_timeline": [
                {"timestamp": "2025-03-15T14:02:45Z", "source": "git", "category": "trigger", "description": "Deploy completed", "evidence": "commit a1b2c3d", "significance": "trigger"},
                {"timestamp": "2025-03-15T14:30:12Z", "source": "logs", "category": "impact", "description": "503 errors", "evidence": "log line 40", "significance": "outage"},
            ],
            "incident_phases": {"trigger_time": "2025-03-15T14:02:45Z", "detection_time": "2025-03-15T14:28:30Z", "total_duration_minutes": 18},
            "cross_source_correlations": [{"description": "Deploy to error correlation", "evidence_sources": ["git", "logs"]}],
            "timeline_gaps": [],
            "narrative_summary": "Deploy caused pool exhaustion.",
        }
    elif "log" in system_prompt.lower():
        parsed = {
            "key_errors": [{"message": "Pool exhausted", "timestamp": "2025-03-15T14:30:12Z", "level": "FATAL", "count": 45}],
            "error_timeline": [{"timestamp": "2025-03-15T14:30:12Z", "description": "Pool exhausted", "evidence": "log"}],
            "affected_services": ["user-service"],
            "log_summary": "Summary of errors",
        }
    elif "communication" in system_prompt.lower() or "slack" in system_prompt.lower():
        parsed = {
            "key_decisions": [{"decision": "Hotfix rollback", "timestamp": "2025-03-15T14:35:00Z", "actor": "@sarah"}],
            "communication_timeline": [{"timestamp": "2025-03-15T14:35:00Z", "description": "Decided to hotfix", "evidence": "slack"}],
            "comms_summary": "Slack triage summary",
        }
    elif "git" in system_prompt.lower():
        parsed = {
            "suspicious_commits": [{"sha": "a1b2c3d", "author": "Mike Torres", "message": "migrate DB config", "timestamp": "2025-03-15T11:30:00Z", "risk_assessment": "removed timeout", "files_changed": ["src/config/schema.py"], "could_cause": "pool leak"}],
            "deploy_timeline": [{"timestamp": "2025-03-15T14:02:45Z", "description": "Deploy v2.14.0"}],
            "most_likely_culprit": {"sha": "a1b2c3d", "primary_file": "src/config/schema.py", "reason": "removed timeout"},
            "forensic_code_diff": {
                "culprit_file": "src/config/schema.py",
                "problematic_diff": "- timeout = 5.0\n+ conn = pool.acquire()  # [CAUSE: missing timeout]",
                "line_annotations": ["Line 2: Removed timeout"],
                "remediation_diff": "+ timeout = 5.0",
            },
            "git_summary": "Git changes summary",
        }
    else:
        parsed = {"accuracy": "exact", "score": 1.0, "recall": 1.0, "events_found": [], "factors_found": []}

    raw["parsed"] = parsed
    return raw


class TestAgenticPipeline(unittest.TestCase):

    def test_full_pipeline_run(self):
        import agents.log_parser
        import agents.comms_analyzer
        import agents.git_analyzer
        import agents.timeline_builder
        import agents.root_cause_analyzer
        import agents.report_writer
        import evaluation.metrics

        # Save originals
        orig_lp = agents.log_parser.call_llm_json
        orig_ca = agents.comms_analyzer.call_llm_json
        orig_ga = agents.git_analyzer.call_llm_json
        orig_tb = agents.timeline_builder.call_llm_json
        orig_rc = agents.root_cause_analyzer.call_llm_json
        orig_rw = agents.report_writer.call_llm
        orig_em = evaluation.metrics.call_llm_json

        try:
            agents.log_parser.call_llm_json = mock_call_llm_json
            agents.comms_analyzer.call_llm_json = mock_call_llm_json
            agents.git_analyzer.call_llm_json = mock_call_llm_json
            agents.timeline_builder.call_llm_json = mock_call_llm_json
            agents.root_cause_analyzer.call_llm_json = mock_call_llm_json
            agents.report_writer.call_llm = mock_call_llm
            evaluation.metrics.call_llm_json = mock_call_llm_json

            from agents.orchestrator import run_pipeline
            from integrations.enterprise_integrations import format_slack_blocks, export_jira_tickets
            from evaluation.metrics import evaluate_report

            result = run_pipeline("data/incidents/incident_01_db_connection_pool", verbose=False)

            # 1. Pipeline output verification
            self.assertIn("report_markdown", result)
            self.assertIn("trajectory", result)
            self.assertIn("context_snapshot", result)
            self.assertGreater(len(result["report_markdown"]), 500)

            # 2. Lucide Icons & Shields verification
            self.assertIn("shields.io", result["report_markdown"])
            self.assertIn("iconify.design", result["report_markdown"])

            # 3. Slack Integration verification
            slack_blocks = format_slack_blocks(result["report_markdown"], result["incident_title"])
            self.assertIn("blocks", slack_blocks)
            self.assertGreaterEqual(len(slack_blocks["blocks"]), 3)

            # 4. Jira Tickets verification
            jira_tickets = export_jira_tickets(result["report_markdown"])
            self.assertGreaterEqual(len(jira_tickets), 2)

            # 5. Evaluation framework verification
            with open("data/incidents/incident_01_db_connection_pool/ground_truth.json", "r") as f:
                gt = json.load(f)
            eval_res = evaluate_report(result["report_markdown"], gt)
            self.assertGreaterEqual(eval_res["weighted_score"], 80.0)
            self.assertTrue(eval_res["deterministic_metrics"]["has_forensic_diff"])
        finally:
            agents.log_parser.call_llm_json = orig_lp
            agents.comms_analyzer.call_llm_json = orig_ca
            agents.git_analyzer.call_llm_json = orig_ga
            agents.timeline_builder.call_llm_json = orig_tb
            agents.root_cause_analyzer.call_llm_json = orig_rc
            agents.report_writer.call_llm = orig_rw
            evaluation.metrics.call_llm_json = orig_em




if __name__ == "__main__":
    unittest.main()
