"""
Agent 1: Log Parser
Analyses raw application and infrastructure logs to extract structured findings.
"""

from __future__ import annotations

import json
from typing import Any

from agents.llm_client import call_llm_json, MODEL_MINI
from tools.log_tools import parse_logs, filter_by_severity, find_error_patterns, detect_anomalies, summarise_logs

SYSTEM_PROMPT = """\
You are an expert SRE log analyst. Your job is to analyze application and infrastructure
logs from a production incident and extract structured findings.

You will receive:
1. Parsed log entries (chronologically sorted)
2. Error patterns detected by automated tooling
3. Anomalies detected in the log stream
4. Summary statistics

Your task is to produce a JSON analysis with these fields:

{
  "key_errors": [
    {
      "timestamp": "ISO timestamp",
      "service": "service name",
      "message": "error message",
      "significance": "why this error matters for understanding the incident"
    }
  ],
  "error_timeline": [
    {
      "timestamp": "ISO timestamp",
      "description": "what happened at this point based on logs"
    }
  ],
  "services_affected": ["list of services that showed errors or degradation"],
  "first_error_timestamp": "when the first sign of trouble appeared",
  "probable_trigger": "based ONLY on log evidence, what likely triggered the incident",
  "log_summary": "2-3 sentence summary of what the logs tell us about this incident"
}

Rules:
- Base ALL findings on the actual log data provided. Do not speculate beyond the evidence.
- Focus on ERROR and FATAL level entries, but note WARN entries that preceded the errors.
- Identify the temporal sequence: what happened first, what cascaded from it.
- Note any services that transitioned from healthy to unhealthy.
"""


def run(logs_data: list[dict], trajectory: list[dict] | None = None) -> dict:
    """
    Run the Log Parser agent on raw log data.

    Args:
        logs_data: Raw log entries (list of dicts)
        trajectory: Mutable list to append trajectory steps to

    Returns:
        Structured log analysis findings (dict)
    """
    if trajectory is None:
        trajectory = []

    # Step 1: Use tools to pre-process logs
    parsed = parse_logs(logs_data)
    errors_only = filter_by_severity(parsed, "WARN")
    patterns = find_error_patterns(parsed)
    anomalies = detect_anomalies(parsed)
    summary = summarise_logs(parsed)

    trajectory.append({
        "agent": "log_parser",
        "step": "tool_preprocessing",
        "tools_used": ["parse_logs", "filter_by_severity", "find_error_patterns", "detect_anomalies", "summarise_logs"],
        "results": {
            "total_logs": len(parsed),
            "warnings_and_errors": len(errors_only),
            "error_patterns_found": len(patterns),
            "anomalies_detected": len(anomalies),
        }
    })

    # Step 2: Feed pre-processed data to LLM for analysis
    user_prompt = f"""Analyze these incident logs:

## Log Summary
{json.dumps(summary, indent=2)}

## Warning/Error Entries ({len(errors_only)} entries)
{json.dumps(errors_only, indent=2)}

## Recurring Error Patterns
{json.dumps(patterns, indent=2)}

## Detected Anomalies
{json.dumps(anomalies, indent=2)}

Produce your structured JSON analysis."""

    result = call_llm_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=MODEL_MINI,
        max_tokens=2048,
    )

    trajectory.append({
        "agent": "log_parser",
        "step": "llm_analysis",
        "model": result["model"],
        "usage": result["usage"],
        "latency_seconds": result["latency_seconds"],
    })

    findings = result["parsed"]
    findings["_trajectory"] = trajectory
    return findings
