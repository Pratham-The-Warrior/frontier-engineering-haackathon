"""
Agent 3: Git & Forensic Code Analyzer
Analyses recent git commits, deploys, and code diffs to pinpoint the exact
"Smoking Gun" code lines that triggered or contributed to the incident.
Reconstructs syntax-highlighted diffs with inline risk annotations.
"""

from __future__ import annotations

import json
from typing import Any

from agents.llm_client import call_llm_json, MODEL
from tools.git_tools import parse_commits, find_suspicious_changes, summarise_git_activity
from tools.diff_tools import detect_diff_risk_patterns

SYSTEM_PROMPT = """\
You are an expert Principal Engineer and forensic code analyst.
Your job is to analyze recent git commits, diff summaries, and file changes around an incident window to:
1. Pinpoint the exact "Smoking Gun" commit and the specific code lines that caused the outage.
2. Reconstruct a realistic, syntax-highlighted Git Diff showing the problematic change with inline warning comments (`# 🚨 ROOT CAUSE:` or `# ⚠️ LEAK:`).
3. Produce a clean Remediation Patch showing how the code should have been properly written.

Produce a JSON response with these fields:
{
  "suspicious_commits": [
    {
      "sha": "commit hash",
      "author": "author name",
      "message": "commit message",
      "timestamp": "ISO timestamp",
      "risk_assessment": "why this commit is risky",
      "files_changed": ["file1.py"],
      "could_cause": "specific failure mechanism"
    }
  ],
  "deploy_timeline": [
    {
      "timestamp": "ISO timestamp",
      "description": "deploy description"
    }
  ],
  "most_likely_culprit": {
    "sha": "commit hash",
    "primary_file": "src/config/schema.py",
    "reason": "precise explanation of why this commit triggered the failure"
  },
  "forensic_code_diff": {
    "culprit_file": "path/to/file.py",
    "problematic_diff": "```diff formatted string with + and - and inline # 🚨 ROOT CAUSE comments```",
    "line_annotations": [
      "🔴 **Line X:** description of specific code vulnerability",
      "🟡 **Line Y:** description of secondary risk"
    ],
    "remediation_diff": "```diff formatted string showing the corrected + safe code```"
  },
  "git_summary": "2-3 sentence summary of code changes"
}

Rules for Diff Construction:
- In `problematic_diff`, use standard git diff format (`-` for deleted safe lines, `+` for added buggy lines).
- Include inline code comments like `# 🚨 ROOT CAUSE: ...` or `# ⚠️ VULNERABILITY: ...` directly on the offending lines.
- In `remediation_diff`, show the complete, clean fix (`+` lines showing timeouts, circuit breakers, mutex locks, or proper context managers).
- Keep diffs focused on the critical 8-15 lines of code.
"""


def run(
    git_data: list[dict],
    incident_time: str = "",
    trajectory: list[dict] | None = None,
) -> dict:
    """
    Run the Git & Forensic Code Analyzer agent.
    """
    if trajectory is None:
        trajectory = []

    # Step 1: Tool pre-processing
    parsed = parse_commits(git_data)
    suspicious = find_suspicious_changes(parsed, incident_time) if incident_time else parsed
    summary = summarise_git_activity(parsed)

    # Detect static risk patterns across all suspicious commits
    diff_risks = []
    for c in suspicious:
        risks = detect_diff_risk_patterns(c.get("diff_summary", "") + " " + c.get("message", ""), c.get("files_changed", []))
        if risks:
            diff_risks.append({"sha": c.get("sha"), "risks": risks})

    trajectory.append({
        "agent": "git_analyzer",
        "step": "tool_preprocessing",
        "tools_used": ["parse_commits", "find_suspicious_changes", "detect_diff_risk_patterns"],
        "results": {
            "total_commits": len(parsed),
            "suspicious_commits": len(suspicious),
            "detected_risk_patterns": len(diff_risks),
        },
    })

    # Step 2: Deep LLM forensic diff reconstruction
    user_prompt = f"""Perform a forensic code & diff analysis on these commits for an incident around {incident_time}:

## Git Summary
{json.dumps(summary, indent=2)}

## Suspicious Commits (ranked by risk score)
{json.dumps(suspicious, indent=2)}

## Static Risk Pattern Matches
{json.dumps(diff_risks, indent=2)}

Produce your complete forensic code diff analysis JSON."""

    result = call_llm_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=MODEL,
        max_tokens=3000,
    )

    trajectory.append({
        "agent": "git_analyzer",
        "step": "forensic_diff_generation",
        "model": result["model"],
        "usage": result["usage"],
        "latency_seconds": result["latency_seconds"],
    })

    findings = result["parsed"]
    findings["_trajectory"] = trajectory
    return findings
