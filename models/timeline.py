"""
Data models for the unified incident timeline.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    """A single event in the unified timeline."""
    timestamp: str
    source: str  # "logs", "slack", "git", "alerts"
    category: str  # "error", "deploy", "human_action", "alert", "recovery", "config_change"
    description: str
    severity: str = "info"  # critical, warning, info
    evidence: str = ""  # raw source reference
    related_events: list[str] = Field(default_factory=list)


class Timeline(BaseModel):
    """The unified, chronologically ordered timeline of an incident."""
    events: list[TimelineEvent] = Field(default_factory=list)
    incident_start: str = ""
    incident_detected: str = ""
    incident_resolved: str = ""
    total_duration_minutes: int = 0
    detection_delay_minutes: int = 0

    def add_event(self, event: TimelineEvent) -> None:
        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp)

    def get_events_by_source(self, source: str) -> list[TimelineEvent]:
        return [e for e in self.events if e.source == source]

    def get_events_by_category(self, category: str) -> list[TimelineEvent]:
        return [e for e in self.events if e.category == category]

    def to_markdown(self) -> str:
        """Render timeline as a markdown table."""
        lines = ["| Time | Source | Category | Description |",
                 "|------|--------|----------|-------------|"]
        for e in self.events:
            lines.append(f"| {e.timestamp} | {e.source} | {e.category} | {e.description} |")
        return "\n".join(lines)
