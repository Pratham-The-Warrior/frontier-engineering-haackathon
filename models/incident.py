"""
Data models for incident data — the raw inputs to the post-mortem pipeline.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


# ---------------------------------------------------------------------------
# Raw input structures  (what each synthetic incident provides)
# ---------------------------------------------------------------------------

class LogEntry(BaseModel):
    """A single structured log line."""
    timestamp: str
    level: str  # DEBUG, INFO, WARN, ERROR, FATAL
    service: str
    message: str
    metadata: dict = Field(default_factory=dict)


class SlackMessage(BaseModel):
    """One message in an incident-response Slack thread."""
    timestamp: str
    user: str
    role: str  # e.g. "SRE", "Backend Engineer", "Engineering Manager"
    message: str


class GitCommit(BaseModel):
    """A recent commit near the incident window."""
    sha: str
    timestamp: str
    author: str
    message: str
    files_changed: list[str] = Field(default_factory=list)
    diff_summary: str = ""


class Alert(BaseModel):
    """A monitoring / alerting event."""
    timestamp: str
    severity: str  # critical, warning, info
    source: str  # e.g. "PagerDuty", "Datadog", "CloudWatch"
    title: str
    description: str


# ---------------------------------------------------------------------------
# Ground truth  (used for evaluation only)
# ---------------------------------------------------------------------------

class GroundTruth(BaseModel):
    """The known-correct answers for a synthetic incident."""
    root_cause: str
    root_cause_category: str  # e.g. "configuration", "code_bug", "infrastructure"
    contributing_factors: list[str] = Field(default_factory=list)
    key_timeline_events: list[dict] = Field(default_factory=list)
    severity: str  # SEV1, SEV2, SEV3
    impact_summary: str
    resolution: str
    duration_minutes: int


# ---------------------------------------------------------------------------
# Top-level incident container
# ---------------------------------------------------------------------------

class IncidentData(BaseModel):
    """All raw data for a single incident — the input to the pipeline."""
    incident_id: str
    title: str
    logs: list[LogEntry] = Field(default_factory=list)
    slack_thread: list[SlackMessage] = Field(default_factory=list)
    git_commits: list[GitCommit] = Field(default_factory=list)
    alerts: list[Alert] = Field(default_factory=list)
    ground_truth: Optional[GroundTruth] = None
