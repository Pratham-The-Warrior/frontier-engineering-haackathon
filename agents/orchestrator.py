"""
Pipeline Orchestrator
Runs the multi-agent incident analysis pipeline:
Phase 1: Source Analysis Agents (Log, Slack, Git)
Phase 2: Timeline Builder (Cross-Source Synthesis & IncidentContext)
Phase 3: Agentic Root Cause Analyzer (Hypothesis Testing & Evidence Tools)
Phase 4: Report Writer (CodeRabbit-Grade Scannable Post-Mortem)

Integrates shared memory (IncidentContext) and comprehensive trajectory capture.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

# Ensure safe console output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from agents import (
    log_parser,
    comms_analyzer,
    git_analyzer,
    timeline_builder,
    root_cause_analyzer,
    report_writer,
)
from agents.incident_context import IncidentContext


def load_incident(incident_dir: str) -> dict:
    """Load all data files for a single incident."""
    data = {}
    for filename in sorted(os.listdir(incident_dir)):
        filepath = os.path.join(incident_dir, filename)
        if filename.endswith(".json") or filename.endswith(".jsonl"):
            with open(filepath, "r", encoding="utf-8") as f:
                data[filename] = json.load(f)
    return data


def collect_data_from_sources(config: dict) -> tuple[dict, list[str]]:
    """
    Collect incident data from real sources (GitHub, Slack, PagerDuty, uploads).

    Args:
        config: Dict with source configuration:
            - github_repo: GitHub repo URL or owner/repo
            - slack_channel: Slack channel ID
            - slack_thread_ts: Specific thread timestamp
            - pagerduty_incident_id: PagerDuty incident ID
            - incident_time: ISO timestamp of the incident
            - time_window_hours: How far back to look for commits
            - logs_text: Raw log text (upload/paste fallback)
            - slack_text: Raw chat text (paste fallback)
            - alerts_json: Raw alerts JSON (upload/paste fallback)

    Returns:
        (data_dict, sources_used) — data in the same format as load_incident()
    """
    from collectors import github_collector, slack_collector, pagerduty_collector, log_collector
    import storage

    data: dict[str, Any] = {}
    sources_used: list[str] = []
    incident_time = config.get("incident_time", "")
    window_hours = config.get("time_window_hours", 24)

    # Calculate time window
    if incident_time:
        try:
            inc_dt = datetime.fromisoformat(incident_time.replace("Z", "+00:00"))
            since = (inc_dt - timedelta(hours=window_hours)).isoformat()
            until = inc_dt.isoformat()
        except ValueError:
            since = None
            until = None
    else:
        since = None
        until = None

    # --- GitHub ---
    github_repo = config.get("github_repo", "")
    if github_repo:
        try:
            # Get credentials from stored integration or use empty
            gh_integration = storage.get_integration("github")
            token = ""
            if gh_integration:
                token = gh_integration.get("credentials", {}).get("token", "")

            commits = github_collector.fetch_commits(
                repo_url=github_repo,
                token=token,
                since=since,
                until=until,
                max_commits=30,
            )
            data["git_commits.json"] = commits
            sources_used.append("github")
        except Exception as e:
            print(f"  [WARN] GitHub collection failed: {e}")

    # --- Slack ---
    slack_channel = config.get("slack_channel", "")
    slack_text = config.get("slack_text", "")
    if slack_channel:
        try:
            sl_integration = storage.get_integration("slack")
            if sl_integration:
                token = sl_integration.get("credentials", {}).get("bot_token", "")
                thread_ts = config.get("slack_thread_ts", "")
                if thread_ts:
                    messages = slack_collector.fetch_thread_replies(
                        token=token, channel_id=slack_channel, thread_ts=thread_ts
                    )
                else:
                    messages = slack_collector.fetch_channel_messages(
                        token=token, channel_id=slack_channel,
                        oldest=since, latest=until,
                    )
                data["slack_thread.json"] = messages
                sources_used.append("slack")
        except Exception as e:
            print(f"  [WARN] Slack collection failed: {e}")
    elif slack_text:
        # Fallback: parse pasted messages
        data["slack_thread.json"] = slack_collector.parse_pasted_messages(slack_text)
        sources_used.append("slack_paste")

    # --- PagerDuty ---
    pd_incident_id = config.get("pagerduty_incident_id", "")
    alerts_json = config.get("alerts_json", "")
    if pd_incident_id:
        try:
            pd_integration = storage.get_integration("pagerduty")
            if pd_integration:
                api_key = pd_integration.get("credentials", {}).get("api_key", "")
                alerts = pagerduty_collector.fetch_incident_alerts(api_key, pd_incident_id)
                data["alerts.json"] = alerts
                sources_used.append("pagerduty")
        except Exception as e:
            print(f"  [WARN] PagerDuty collection failed: {e}")
    elif alerts_json:
        try:
            data["alerts.json"] = json.loads(alerts_json)
            sources_used.append("alerts_upload")
        except json.JSONDecodeError:
            pass

    # --- Logs ---
    logs_text = config.get("logs_text", "")
    if logs_text:
        logs = log_collector.parse_uploaded_file(logs_text, "logs.jsonl")
        data["logs.jsonl"] = logs
        sources_used.append("logs_upload")

    # Ensure we have at least empty lists for missing sources
    data.setdefault("git_commits.json", [])
    data.setdefault("slack_thread.json", [])
    data.setdefault("alerts.json", [])
    data.setdefault("logs.jsonl", [])
    data.setdefault("metadata.json", {
        "incident_id": config.get("incident_id", "LIVE"),
        "title": config.get("title", "Live Incident Analysis"),
    })

    return data, sources_used


def run_pipeline_from_sources(
    config: dict,
    progress_callback: Callable[[str, int], None] | None = None,
    verbose: bool = True,
) -> dict:
    """
    Run the full pipeline using real data sources instead of static files.

    This is the main entry point for the web dashboard / API.
    It collects data from configured sources, then feeds it into the
    existing run_pipeline logic.

    Args:
        config: Source configuration dict (see collect_data_from_sources)
        progress_callback: Optional function(phase_name, percent) for live status
        verbose: Print progress to console

    Returns:
        Same result dict as run_pipeline(), plus sources_used list
    """
    def _progress(phase: str, pct: int):
        if progress_callback:
            try:
                progress_callback(phase, pct)
            except Exception:
                pass
        if verbose:
            print(f"  [{pct}%] {phase}")

    _progress("Collecting data from sources", 5)

    # Collect real data
    data, sources_used = collect_data_from_sources(config)

    if verbose:
        print(f"  Sources used: {', '.join(sources_used) if sources_used else 'none'}")
        for key, val in data.items():
            if isinstance(val, list):
                print(f"    {key}: {len(val)} items")

    _progress("Data collection complete", 15)

    # Now run the standard pipeline with the collected data
    pipeline_start = time.time()
    full_trajectory: list[dict] = []

    metadata = data.get("metadata.json", {})
    incident_id = metadata.get("incident_id", "LIVE")
    incident_title = metadata.get("title", config.get("title", "Live Analysis"))

    context = IncidentContext(incident_id=incident_id, incident_title=incident_title)

    if verbose:
        print(f"\n{'='*65}")
        print(f"  Incident Investigation Pipeline: {incident_title}")
        print(f"{'='*65}")

    # Phase 1: Source Analysis
    _progress("Running Log Parser Agent", 20)
    log_trajectory: list[dict] = []
    log_findings = log_parser.run(logs_data=data.get("logs.jsonl", []), trajectory=log_trajectory)
    full_trajectory.extend(log_trajectory)

    for err in log_findings.get("key_errors", []):
        context.add_finding(
            source_agent="log_parser", category="error",
            summary=err.get("message", "Error"),
            timestamp=err.get("timestamp", ""),
            severity="critical" if err.get("level") == "FATAL" else "warning",
            evidence=f"Log count: {err.get('count', 1)}",
        )

    _progress("Running Communications Analyzer Agent", 35)
    comms_trajectory: list[dict] = []
    comms_findings = comms_analyzer.run(slack_data=data.get("slack_thread.json", []), trajectory=comms_trajectory)
    full_trajectory.extend(comms_trajectory)

    for dec in comms_findings.get("key_decisions", []):
        context.add_finding(
            source_agent="comms_analyzer", category="decision",
            summary=dec.get("decision", ""),
            timestamp=dec.get("timestamp", ""),
            evidence=f"User: {dec.get('actor', 'unknown')}",
        )

    _progress("Running Git Analyzer Agent", 50)
    logs = data.get("logs.jsonl", [])
    error_logs = [l for l in logs if l.get("level") in ("ERROR", "FATAL")]
    incident_time = error_logs[0]["timestamp"] if error_logs else config.get("incident_time", "")

    git_trajectory: list[dict] = []
    git_findings = git_analyzer.run(
        git_data=data.get("git_commits.json", []),
        incident_time=incident_time,
        trajectory=git_trajectory,
    )
    full_trajectory.extend(git_trajectory)

    for commit in git_findings.get("suspicious_commits", []):
        context.add_finding(
            source_agent="git_analyzer", category="deploy",
            summary=commit.get("summary", ""),
            timestamp=commit.get("timestamp", ""),
            severity="warning" if commit.get("risk_score", 0) > 60 else "info",
            evidence=f"Commit: {commit.get('hash', '')[:7]}",
            metadata={"risk_score": commit.get("risk_score", 0)},
        )

    # Phase 2: Timeline
    _progress("Synthesizing unified timeline", 65)
    timeline_trajectory: list[dict] = []
    timeline_result = timeline_builder.run(
        log_findings=log_findings, comms_findings=comms_findings,
        git_findings=git_findings, alerts_data=data.get("alerts.json", []),
        trajectory=timeline_trajectory,
    )
    full_trajectory.extend(timeline_trajectory)

    for ev in timeline_result.get("unified_timeline", []):
        context.add_timeline_event(
            timestamp=ev.get("timestamp", ""), source=ev.get("source", ""),
            description=ev.get("description", ""), evidence=ev.get("evidence", ""),
            category=ev.get("category", ""),
        )

    # Phase 3: Root Cause Analysis
    _progress("Running Root Cause Analyzer with evidence verification", 75)
    rca_trajectory: list[dict] = []
    rca_result = root_cause_analyzer.run(
        timeline_data=timeline_result, incident_context=context,
        trajectory=rca_trajectory,
    )
    full_trajectory.extend(rca_trajectory)

    # Phase 4: Report Generation
    _progress("Generating executive post-mortem report", 90)
    report_trajectory: list[dict] = []
    report_result = report_writer.run(
        root_cause_data=rca_result, timeline_data=timeline_result,
        git_findings=git_findings, incident_title=incident_title,
        trajectory=report_trajectory,
    )
    full_trajectory.extend(report_trajectory)

    total_time = time.time() - pipeline_start
    total_tokens = sum(
        step.get("usage", {}).get("total_tokens", 0)
        for step in full_trajectory if "usage" in step
    )

    _progress("Report generated successfully", 100)

    return {
        "incident_id": incident_id,
        "incident_title": incident_title,
        "report_markdown": report_result["report_markdown"],
        "quality_scores": report_result["quality_scores"],
        "root_cause_summary": rca_result.get("root_cause", {}).get("summary", ""),
        "ranked_hypotheses": rca_result.get("ranked_hypotheses", []),
        "trajectory": full_trajectory,
        "context_snapshot": context.snapshot(),
        "timing": {"total_seconds": round(total_time, 1)},
        "token_usage": total_tokens,
        "metadata": metadata,
        "sources_used": sources_used,
    }


def run_pipeline(
    incident_dir: str,
    verbose: bool = True,
    interactive: bool = False,
) -> dict:
    """
    Run the full agentic post-mortem generation pipeline on an incident.

    Args:
        incident_dir: Path to the incident data directory
        verbose: Whether to print progress updates
        interactive: If True, pauses for human approval of root cause before report generation

    Returns:
        {
            "report_markdown": str,
            "quality_scores": dict,
            "trajectory": list[dict],
            "timing": dict,
            "metadata": dict,
            "context_snapshot": dict,
        }
    """
    pipeline_start = time.time()
    full_trajectory: list[dict] = []

    # --- Load incident data ---
    data = load_incident(incident_dir)
    metadata = data.get("metadata.json", {})
    incident_id = metadata.get("incident_id", os.path.basename(incident_dir))
    incident_title = metadata.get("title", "Unknown Incident")

    # Initialize shared memory context
    context = IncidentContext(incident_id=incident_id, incident_title=incident_title)

    if verbose:
        print(f"\n{'='*65}")
        print(f"  Incident Investigation Pipeline: {incident_title} ({incident_id})")
        print(f"{'='*65}")

    # =========================================================================
    # Phase 1: Source Analysis Agents
    # =========================================================================
    if verbose:
        print("\n[Phase 1/4] Running source-specific analysis agents...")

    # Agent 1: Log Parser
    if verbose:
        print("  -> [1/3] Log Parser Agent...")
    t1 = time.time()
    log_trajectory: list[dict] = []
    log_findings = log_parser.run(
        logs_data=data.get("logs.jsonl", []),
        trajectory=log_trajectory,
    )
    log_time = time.time() - t1
    full_trajectory.extend(log_trajectory)

    # Ingest log findings into shared memory
    for err in log_findings.get("key_errors", []):
        context.add_finding(
            source_agent="log_parser",
            category="error",
            summary=err.get("message", "Error"),
            timestamp=err.get("timestamp", ""),
            severity="critical" if err.get("level") == "FATAL" else "warning",
            evidence=f"Log count: {err.get('count', 1)}",
        )
    if verbose:
        print(f"     OK ({log_time:.1f}s) - {len(log_findings.get('key_errors', []))} error signatures identified")

    # Agent 2: Communications Analyzer
    if verbose:
        print("  -> [2/3] Communications Analyzer Agent...")
    t2 = time.time()
    comms_trajectory: list[dict] = []
    comms_findings = comms_analyzer.run(
        slack_data=data.get("slack_thread.json", []),
        trajectory=comms_trajectory,
    )
    comms_time = time.time() - t2
    full_trajectory.extend(comms_trajectory)

    # Ingest comms findings into shared memory
    for dec in comms_findings.get("key_decisions", []):
        context.add_finding(
            source_agent="comms_analyzer",
            category="decision",
            summary=dec.get("decision", ""),
            timestamp=dec.get("timestamp", ""),
            evidence=f"User: {dec.get('actor', 'unknown')}",
        )
    if verbose:
        print(f"     OK ({comms_time:.1f}s) - {len(comms_findings.get('key_decisions', []))} team decisions captured")

    # Agent 3: Git Analyzer
    if verbose:
        print("  -> [3/3] Git / Deploy Analyzer Agent...")
    logs = data.get("logs.jsonl", [])
    error_logs = [l for l in logs if l.get("level") in ("ERROR", "FATAL")]
    incident_time = error_logs[0]["timestamp"] if error_logs else ""

    t3 = time.time()
    git_trajectory: list[dict] = []
    git_findings = git_analyzer.run(
        git_data=data.get("git_commits.json", []),
        incident_time=incident_time,
        trajectory=git_trajectory,
    )
    git_time = time.time() - t3
    full_trajectory.extend(git_trajectory)

    # Ingest git findings into shared memory
    for commit in git_findings.get("suspicious_commits", []):
        context.add_finding(
            source_agent="git_analyzer",
            category="deploy",
            summary=commit.get("summary", ""),
            timestamp=commit.get("timestamp", ""),
            severity="warning" if commit.get("risk_score", 0) > 60 else "info",
            evidence=f"Commit: {commit.get('hash', '')[:7]}",
            metadata={"risk_score": commit.get("risk_score", 0)},
        )
    if verbose:
        print(f"     OK ({git_time:.1f}s) - {len(git_findings.get('suspicious_commits', []))} high-risk changes analyzed")

    # =========================================================================
    # Phase 2: Timeline Builder (Synthesis & Memory Correlation)
    # =========================================================================
    if verbose:
        print("\n[Phase 2/4] Synthesizing unified cross-source timeline...")
    t4 = time.time()
    timeline_trajectory: list[dict] = []
    timeline_result = timeline_builder.run(
        log_findings=log_findings,
        comms_findings=comms_findings,
        git_findings=git_findings,
        alerts_data=data.get("alerts.json", []),
        trajectory=timeline_trajectory,
    )
    timeline_time = time.time() - t4
    full_trajectory.extend(timeline_trajectory)

    # Populate timeline into IncidentContext
    for ev in timeline_result.get("unified_timeline", []):
        context.add_timeline_event(
            timestamp=ev.get("timestamp", ""),
            source=ev.get("source", ""),
            description=ev.get("description", ""),
            evidence=ev.get("evidence", ""),
            category=ev.get("category", ""),
        )

    if verbose:
        events = timeline_result.get("unified_timeline", [])
        print(f"     OK ({timeline_time:.1f}s) - {len(events)} correlated timeline milestones")

    # =========================================================================
    # Phase 3: Agentic Root Cause Analyzer (Hypothesis Testing & Verification)
    # =========================================================================
    if verbose:
        print("\n[Phase 3/4] Running agentic Root Cause Analyzer with Evidence Tools...")
    t5 = time.time()
    rca_trajectory: list[dict] = []
    rca_result = root_cause_analyzer.run(
        timeline_data=timeline_result,
        incident_context=context,
        trajectory=rca_trajectory,
    )
    rca_time = time.time() - t5
    full_trajectory.extend(rca_trajectory)

    rc = rca_result.get("root_cause", {})
    if verbose:
        print(f"     OK ({rca_time:.1f}s) - Category: [{rc.get('category', 'N/A')}], Confidence: [{rc.get('confidence', 'N/A')}]")
        print(f"     Root Cause: {rc.get('summary', 'N/A')[:90]}...")

    # Optional Human-in-the-Loop Checkpoint (Ground Rules & Control)
    if interactive:
        print("\n" + "="*50)
        print("  HUMAN-IN-THE-LOOP CHECKPOINT")
        print("="*50)
        print(f"Identified Root Cause: {rc.get('summary')}")
        print(f"Confidence: {rc.get('confidence')}")
        print("\nTop Candidate Hypotheses Evaluated:")
        for h in rca_result.get("ranked_hypotheses", []):
            print(f"  - Rank {h.get('rank')}: {h.get('hypothesis')[:80]} (Evidence Score: {h.get('score')})")
        user_choice = input("\nApprove this root cause analysis to proceed with report generation? [Y/n/custom]: ").strip()
        if user_choice.lower().startswith("n"):
            print("Aborting report generation by user request.")
            return {"status": "cancelled_by_user", "rca": rca_result}
        elif user_choice and not user_choice.lower().startswith("y"):
            rca_result["root_cause"]["summary"] = user_choice
            print(f"Custom root cause applied: {user_choice}")

    # =========================================================================
    # Phase 4: Report Generation (CodeRabbit-Grade Output)
    # =========================================================================
    if verbose:
        print("\n[Phase 4/4] Generating executive & technical post-mortem report...")
    t6 = time.time()
    report_trajectory: list[dict] = []
    report_result = report_writer.run(
        root_cause_data=rca_result,
        timeline_data=timeline_result,
        git_findings=git_findings,
        incident_title=incident_title,
        trajectory=report_trajectory,
    )
    report_time = time.time() - t6
    full_trajectory.extend(report_trajectory)

    scores = report_result.get("quality_scores", {})
    if verbose:
        print(f"     OK ({report_time:.1f}s)")
        print(f"     Blameless Score:    {scores.get('blameless_score', 'N/A')}/100")
        print(f"     Completeness Score: {scores.get('completeness_score', 'N/A')}/100")
        print(f"     Evidence Citations: {scores.get('evidence_citations', 0)} verified tags")

    total_time = time.time() - pipeline_start

    if verbose:
        print(f"\n{'='*65}")
        print(f"  Pipeline execution successful in {total_time:.1f}s")
        print(f"{'='*65}\n")

    # Record context snapshot into trajectory
    full_trajectory.append({
        "agent": "orchestrator",
        "step": "memory_context_snapshot",
        "context_snapshot": context.snapshot(),
    })

    total_tokens = sum(
        step.get("usage", {}).get("total_tokens", 0)
        for step in full_trajectory
        if "usage" in step
    )

    return {
        "incident_id": incident_id,
        "incident_title": incident_title,
        "report_markdown": report_result["report_markdown"],
        "quality_scores": report_result["quality_scores"],
        "root_cause_summary": rca_result.get("root_cause", {}).get("summary", ""),
        "ranked_hypotheses": rca_result.get("ranked_hypotheses", []),
        "trajectory": full_trajectory,
        "context_snapshot": context.snapshot(),
        "timing": {
            "total_seconds": round(total_time, 1),
            "log_parser_seconds": round(log_time, 1),
            "comms_analyzer_seconds": round(comms_time, 1),
            "git_analyzer_seconds": round(git_time, 1),
            "timeline_builder_seconds": round(timeline_time, 1),
            "root_cause_analyzer_seconds": round(rca_time, 1),
            "report_writer_seconds": round(report_time, 1),
        },
        "token_usage": total_tokens,
        "metadata": metadata,
    }
