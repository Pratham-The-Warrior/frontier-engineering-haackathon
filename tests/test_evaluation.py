import unittest
from unittest.mock import patch

from evaluation.metrics import (
    evaluate_root_cause_accuracy,
    evaluate_timeline_recall,
    evaluate_contributing_factors_recall,
    calculate_deterministic_metrics,
    evaluate_report
)


class TestEvaluationMetrics(unittest.TestCase):
    @patch("evaluation.metrics.call_llm_json")
    def test_evaluate_root_cause_accuracy(self, mock_llm):
        mock_llm.return_value = {
            "parsed": {
                "accuracy": "exact",
                "score": 1.0,
                "explanation": "Matches perfectly."
            }
        }
        res = evaluate_root_cause_accuracy("## Root Cause\nOmitted timeout.", "Omitted timeout.")
        self.assertEqual(res["accuracy"], "exact")
        self.assertEqual(res["score"], 1.0)

    @patch("evaluation.metrics.call_llm_json")
    def test_evaluate_timeline_recall(self, mock_llm):
        mock_llm.return_value = {
            "parsed": {
                "events_found": [{"ground_truth": "Outage start", "found": True}],
                "recall": 1.0,
                "found_count": 1,
                "total_count": 1
            }
        }
        gt_events = [{"timestamp": "14:00", "description": "Outage start"}]
        res = evaluate_timeline_recall("## Timeline\n14:00 Outage.", gt_events)
        self.assertEqual(res["recall"], 1.0)
        self.assertEqual(res["found_count"], 1)

    @patch("evaluation.metrics.call_llm_json")
    def test_evaluate_contributing_factors_recall(self, mock_llm):
        mock_llm.return_value = {
            "parsed": {
                "factors_found": [{"ground_truth": "No CI test", "found": True}],
                "recall": 1.0,
                "found_count": 1,
                "total_count": 1
            }
        }
        res = evaluate_contributing_factors_recall("## Contributing Factors\nNo CI test.", ["No CI test"])
        self.assertEqual(res["recall"], 1.0)

    def test_calculate_deterministic_metrics(self):
        report = """
# Post-Mortem
## Risk & Systemic Vulnerability Assessment
| Risk Dimension | Risk Level | Finding | Evidence |
|---|---|---|---|
| Deploy Safety | High | Gap | `[Git:abc]` |
| Observability | Low | Alert | `[Alert:xyz]` |

## Root Cause
Database connection timeout dropped in config.
`[Log:14:30]`

## Prevention Analysis
| Prevention Point | Safeguard |
|---|---|
| CI | Linter |

```diff
- timeout = 5
+ timeout = None
```
"""
        gt = {"root_cause": "Database connection timeout dropped"}
        metrics = calculate_deterministic_metrics(report, gt)
        
        self.assertEqual(metrics["evidence_citation_count"], 3)  # [Git:abc], [Alert:xyz], [Log:14:30]
        self.assertTrue(metrics["has_risk_matrix"])
        self.assertTrue(metrics["has_prevention_analysis"])
        self.assertTrue(metrics["has_forensic_diff"])
        self.assertGreater(metrics["root_cause_keyword_overlap"], 0.5)

    @patch("evaluation.metrics.call_llm_json")
    def test_evaluate_report(self, mock_llm):
        # mock_llm needs to be mocked for the three LLM calls inside evaluate_report.
        # Call 1: root cause accuracy
        # Call 2: timeline recall
        # Call 3: contributing factors recall
        mock_llm.side_effect = [
            {"parsed": {"accuracy": "exact", "score": 1.0, "explanation": "ok"}},
            {"parsed": {"recall": 1.0, "found_count": 1, "total_count": 1, "events_found": []}},
            {"parsed": {"recall": 1.0, "found_count": 1, "total_count": 1, "factors_found": []}},
        ]
        
        report = """
# Post-Mortem
## Executive Summary
This is a summary of the database outage. It explains what happened in details.
## Impact
Affected user-service and checkouts. It caused significant damage.
## Timeline
| Time | Event |
|---|---|
| 14:00 | Outage occurred today |
## Root Cause
Database connection timeout limits were omitted in config.
## Contributing Factors
- Missing proper config validation in our CI pipeline.
## Resolution
Restored timeout settings in production immediately.
## Action Items
| Priority | Action |
|---|---|
| P0 | Add CI config linting |
## Lessons Learned
- Validate configs properly in CI to prevent issues.
"""
        gt = {
            "root_cause": "Omitted timeout",
            "key_timeline_events": [{"timestamp": "14:00", "description": "Outage"}],
            "contributing_factors": ["Missing CI tests"]
        }
        
        res = evaluate_report(report, gt)
        # Check weighted score computation:
        # rca score 1.0 * 30 + timeline recall 1.0 * 20 + 15 + factors recall 1.0 * 15 + blameless 1.0 * 10 + completeness 1.0 * 10 = 30 + 20 + 15 + 15 + 10 + 10 = 100.
        self.assertEqual(res["weighted_score"], 100.0)


if __name__ == "__main__":
    unittest.main()
