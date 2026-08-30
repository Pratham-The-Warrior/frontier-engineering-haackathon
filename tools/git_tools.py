"""
Tools for analyzing git commit history around an incident window.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def parse_commits(raw_commits: list[dict]) -> list[dict]:
    """Normalise raw commit data into structured records."""
    commits = []
    for c in raw_commits:
        commits.append({
            "sha": c.get("sha", ""),
            "timestamp": c.get("timestamp", ""),
            "author": c.get("author", "unknown"),
            "message": c.get("message", ""),
            "files_changed": c.get("files_changed", []),
            "diff_summary": c.get("diff_summary", ""),
        })
    commits.sort(key=lambda c: c.get("timestamp", ""))
    return commits


def find_suspicious_changes(
    commits: list[dict],
    incident_time: str,
    window_hours: int = 24,
) -> list[dict]:
    """
    Find commits within *window_hours* before the incident that could be
    related to the failure.  Ranks them by proximity and risk indicators.
    """
    if not incident_time:
        return commits
    try:
        inc_dt = datetime.fromisoformat(str(incident_time).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return commits  # fall back to returning all

    window_start = inc_dt - timedelta(hours=window_hours)
    suspicious = []

    for commit in commits:
        try:
            ts_str = commit.get("timestamp", "")
            if not ts_str:
                continue
            c_dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        if window_start <= c_dt <= inc_dt:
            risk_score = _assess_risk(commit)
            suspicious.append({
                **commit,
                "hours_before_incident": round((inc_dt - c_dt).total_seconds() / 3600, 1),
                "risk_score": risk_score,
                "risk_factors": _get_risk_factors(commit),
            })

    suspicious.sort(key=lambda c: c["risk_score"], reverse=True)
    return suspicious


def _assess_risk(commit: dict) -> int:
    """Simple heuristic risk scoring for a commit."""
    score = 0
    msg = commit.get("message", "").lower()
    diff = commit.get("diff_summary", "").lower()
    files = commit.get("files_changed", [])

    # Config changes are risky
    if any("config" in f.lower() for f in files):
        score += 3
    # Infrastructure / deployment files
    if any(kw in f.lower() for f in files for kw in ("deploy", "k8s", "infra", "terraform", ".tf")):
        score += 3
    # Database migrations
    if any("migration" in f.lower() for f in files):
        score += 3
    # Dependency changes
    if any(f.lower() in ("requirements.txt", "package.json", "go.mod", "pom.xml") for f in files):
        score += 2
    # Keywords in commit message
    risky_keywords = ["refactor", "remove", "delete", "upgrade", "migrate", "breaking", "hotfix", "revert"]
    for kw in risky_keywords:
        if kw in msg:
            score += 1
    # Large diff descriptions suggest big changes
    if len(diff) > 200:
        score += 1

    return score


def _get_risk_factors(commit: dict) -> list[str]:
    """Return human-readable risk factors for a commit."""
    factors = []
    msg = commit.get("message", "").lower()
    files = commit.get("files_changed", [])

    if any("config" in f.lower() for f in files):
        factors.append("Modifies configuration files")
    if any(kw in f.lower() for f in files for kw in ("deploy", "k8s", "infra")):
        factors.append("Touches infrastructure/deployment")
    if any("migration" in f.lower() for f in files):
        factors.append("Includes database migration")
    if "refactor" in msg:
        factors.append("Refactoring change — may alter behavior")
    if "upgrade" in msg or "bump" in msg:
        factors.append("Dependency upgrade")
    if "remove" in msg or "delete" in msg:
        factors.append("Removes existing functionality")

    return factors if factors else ["No specific risk factors identified"]


def summarise_git_activity(commits: list[dict]) -> dict[str, Any]:
    """Summarise recent git activity around the incident."""
    return {
        "total_commits": len(commits),
        "authors": list({c["author"] for c in commits}),
        "files_touched": list({f for c in commits for f in c.get("files_changed", [])}),
        "time_range": {
            "earliest": commits[0]["timestamp"] if commits else "",
            "latest": commits[-1]["timestamp"] if commits else "",
        },
    }
