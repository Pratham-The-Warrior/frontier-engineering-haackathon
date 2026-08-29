"""
Data models for the final post-mortem report.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """A single follow-up action item from the post-mortem."""
    description: str
    priority: str  # P0, P1, P2
    owner: str = "TBD"
    type: str = "prevent"  # "prevent", "detect", "mitigate"


class PostMortemReport(BaseModel):
    """The complete post-mortem report — the final output of the pipeline."""
    title: str = ""
    date: str = ""
    severity: str = ""  # SEV1, SEV2, SEV3
    authors: list[str] = Field(default_factory=list)

    # Executive summary
    executive_summary: str = ""

    # Impact
    impact_summary: str = ""
    affected_services: list[str] = Field(default_factory=list)
    affected_users: str = ""
    duration: str = ""

    # Timeline (markdown table)
    timeline_markdown: str = ""

    # Root cause
    root_cause: str = ""
    root_cause_detail: str = ""

    # Contributing factors
    contributing_factors: list[str] = Field(default_factory=list)

    # Resolution
    resolution: str = ""
    resolution_detail: str = ""

    # Action items
    action_items: list[ActionItem] = Field(default_factory=list)

    # Lessons learned
    lessons_learned: list[str] = Field(default_factory=list)

    # What went well
    what_went_well: list[str] = Field(default_factory=list)

    # What could be improved
    what_could_be_improved: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Render the full post-mortem as a polished markdown document."""
        sections = []

        sections.append(f"# Post-Mortem Report: {self.title}\n")
        sections.append(f"**Date:** {self.date}  ")
        sections.append(f"**Severity:** {self.severity}  ")
        if self.authors:
            sections.append(f"**Authors:** {', '.join(self.authors)}  ")
        sections.append("")

        sections.append("---\n")

        sections.append("## Executive Summary\n")
        sections.append(self.executive_summary + "\n")

        sections.append("## Impact\n")
        sections.append(self.impact_summary + "\n")
        if self.affected_services:
            sections.append(f"**Affected Services:** {', '.join(self.affected_services)}  ")
        sections.append(f"**Affected Users:** {self.affected_users}  ")
        sections.append(f"**Duration:** {self.duration}\n")

        sections.append("## Timeline\n")
        sections.append(self.timeline_markdown + "\n")

        sections.append("## Root Cause\n")
        sections.append(self.root_cause + "\n")
        if self.root_cause_detail:
            sections.append(self.root_cause_detail + "\n")

        if self.contributing_factors:
            sections.append("## Contributing Factors\n")
            for factor in self.contributing_factors:
                sections.append(f"- {factor}")
            sections.append("")

        sections.append("## Resolution\n")
        sections.append(self.resolution + "\n")
        if self.resolution_detail:
            sections.append(self.resolution_detail + "\n")

        if self.action_items:
            sections.append("## Action Items\n")
            sections.append("| Priority | Type | Description | Owner |")
            sections.append("|----------|------|-------------|-------|")
            for item in self.action_items:
                sections.append(f"| {item.priority} | {item.type} | {item.description} | {item.owner} |")
            sections.append("")

        if self.lessons_learned:
            sections.append("## Lessons Learned\n")
            for lesson in self.lessons_learned:
                sections.append(f"- {lesson}")
            sections.append("")

        if self.what_went_well:
            sections.append("## What Went Well\n")
            for item in self.what_went_well:
                sections.append(f"- {item}")
            sections.append("")

        if self.what_could_be_improved:
            sections.append("## What Could Be Improved\n")
            for item in self.what_could_be_improved:
                sections.append(f"- {item}")
            sections.append("")

        return "\n".join(sections)
