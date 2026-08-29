"""
Agent 4: Timeline Builder
Synthesises findings from all source-specific agents into a unified, chronological
incident timeline.  This is the key "memory" agent — it holds context from all
sources and finds connections between them.
"""

from __future__ import annotations

import json
from typing import Any

from agents.llm_client import call_llm_json, MODEL
from tools.time_tools import correlate_events, detect_gaps

SYSTEM_PROMPT = """\
You are an expert incident timeline reconstructor. Your job is to take findings
from three separate analysis agents (logs, communications/Slack, git/deploys) and
synthesise them into a single, unified, chronological timeline of the incident.

This is the most critical step in the post-mortem process. You must:
1. Merge events from all three sources into one timeline
2. Resolve any timestamp conflicts or ambiguities
3. Identify cause-and-effect relationships between events
4. Fill in gaps where one source provides context that another is missing
5. Mark the key milestones: trigger, detection, investigation, mitigation, resolution

Produce a JSON response with these fields:

{
  "unified_timeline": [
    {
      "timestamp": "ISO timestamp",
      "source": "logs|slack|git|alerts|inferred",
      "category": "trigger|detection|investigation|mitigation|resolution|impact|escalation",
      "description": "what happened",
      "evidence": "which specific log entry, Slack message, or commit supports this",
      "significance": "why this event matters in the incident narrative"
    }
  ],
  "incident_phases": {
    "trigger_time": "when the root cause was introduced (e.g., deploy time)",
    "symptom_start": "when the first symptoms appeared",
    "detection_time": "when the team became aware",
    "identification_time": "when root cause was identified",
    "mitigation_time": "when the fix was applied",
    "resolution_time": "when full recovery was confirmed",
    "total_duration_minutes": 0,
    "detection_delay_minutes": 0,
    "time_to_resolve_minutes": 0
  },
  "cross_source_correlations": [
    {
      "description": "A connection found between events from different sources",
      "evidence_sources": ["source1", "source2"]
    }
  ],
  "timeline_gaps": [
    {
      "gap_start": "timestamp",
      "gap_end": "timestamp",
      "description": "what information is missing during this period"
    }
  ],
  "narrative_summary": "3-5 sentence narrative that tells the story of this incident from start to finish, connecting all the dots"
}

Rules:
- Every event MUST be traceable to a specific piece of evidence from one of the source analyses.
- If you infer an event that isn't directly in the data, mark its source as "inferred" and explain why.
- The timeline must be strictly chronologically ordered.
- Identify the causal chain: what caused what, and how events cascaded.
- Focus on events that matter for understanding WHY the incident happened and HOW it was resolved.
"""


def run(
    log_findings: dict,
    comms_findings: dict,
    git_findings: dict,
    alerts_data: list[dict] | None = None,
    trajectory: list[dict] | None = None,
) -> dict:
    """
    Run the Timeline Builder agent to synthesise findings from all sources.

    Args:
        log_findings: Output from the Log Parser agent
        comms_findings: Output from the Communications Analyzer agent
        git_findings: Output from the Git Analyzer agent
        alerts_data: Raw alert data (optional, used for additional context)
        trajectory: Mutable list to append trajectory steps to

    Returns:
        Unified timeline and incident phases (dict)
    """
    if trajectory is None:
        trajectory = []

    # Step 1: Use tools to find cross-source correlations
    log_events = log_findings.get("error_timeline", [])
    comms_events = comms_findings.get("communication_timeline", [])
    git_events = git_findings.get("deploy_timeline", [])

    correlations = correlate_events(log_events, comms_events, window_minutes=5)
    all_events = log_events + comms_events + git_events
    gaps = detect_gaps(all_events, min_gap_minutes=10)

    trajectory.append({
        "agent": "timeline_builder",
        "step": "tool_preprocessing",
        "tools_used": ["correlate_events", "detect_gaps"],
        "results": {
            "cross_correlations_found": len(correlations),
            "timeline_gaps_found": len(gaps),
            "total_source_events": len(all_events),
        }
    })

    # Step 2: Build the synthesis prompt
    # Remove _trajectory keys to keep prompt clean
    clean_log = {k: v for k, v in log_findings.items() if k != "_trajectory"}
    clean_comms = {k: v for k, v in comms_findings.items() if k != "_trajectory"}
    clean_git = {k: v for k, v in git_findings.items() if k != "_trajectory"}

    alerts_section = ""
    if alerts_data:
        alerts_section = f"""
## Alert Data
{json.dumps(alerts_data, indent=2)}
"""

    user_prompt = f"""Synthesise these findings from three separate analysis agents into a unified incident timeline:

## Log Analysis Findings
{json.dumps(clean_log, indent=2)}

## Communication/Slack Analysis Findings
{json.dumps(clean_comms, indent=2)}

## Git/Deploy Analysis Findings
{json.dumps(clean_git, indent=2)}
{alerts_section}
## Cross-Source Correlations (automated)
{json.dumps(correlations[:10], indent=2)}

## Timeline Gaps Detected
{json.dumps(gaps, indent=2)}

Produce your unified timeline JSON."""

    result = call_llm_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=MODEL,  # Use the full model for this critical synthesis step
        max_tokens=4096,
    )

    trajectory.append({
        "agent": "timeline_builder",
        "step": "llm_synthesis",
        "model": result["model"],
        "usage": result["usage"],
        "latency_seconds": result["latency_seconds"],
    })

    findings = result["parsed"]
    findings["_trajectory"] = trajectory
    return findings
