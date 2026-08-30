"""
Shared Incident Context — the "memory" and graph layer for the multi-agent pipeline.

All agents write structured findings and canonical events to this context.
Downstream agents can query it by source, category, time range, entity reference,
or graph relationships.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from models.canonical_event import CanonicalEvent, EntityRegistry, ActorEntity, ServiceEntity
from models.incident_graph import IncidentGraph, GraphNode, GraphEdge, NodeType, EdgeRelation


@dataclass
class Finding:
    """A single finding written by an agent."""
    source_agent: str
    category: str          # e.g. "error", "decision", "deploy", "alert", "correlation"
    summary: str
    detail: str = ""
    timestamp: str = ""    # ISO 8601 or empty
    evidence: str = ""     # raw evidence reference
    severity: str = "info" # "critical", "warning", "info"
    metadata: dict = field(default_factory=dict)


class IncidentContext:
    """
    Queryable shared memory and causal knowledge graph for an incident investigation.
    """

    def __init__(self, incident_id: str = "", incident_title: str = "") -> None:
        self.incident_id = incident_id
        self.incident_title = incident_title
        self._findings: list[Finding] = []
        self._timeline_events: list[dict] = []
        self._agent_summaries: dict[str, str] = {}
        self._canonical_events: list[CanonicalEvent] = []
        self.registry: EntityRegistry = EntityRegistry()
        self.graph: IncidentGraph = IncidentGraph()

    # ------------------------------------------------------------------
    # Write API — agents add findings and events
    # ------------------------------------------------------------------

    def add_finding(
        self,
        source_agent: str,
        category: str,
        summary: str,
        *,
        detail: str = "",
        timestamp: str = "",
        evidence: str = "",
        severity: str = "info",
        metadata: dict | None = None,
    ) -> None:
        """Record a structured finding from an agent."""
        self._findings.append(
            Finding(
                source_agent=source_agent,
                category=category,
                summary=summary,
                detail=detail,
                timestamp=timestamp,
                evidence=evidence,
                severity=severity,
                metadata=metadata or {},
            )
        )

    def add_canonical_event(self, event: CanonicalEvent) -> None:
        """Ingest a validated CanonicalEvent and register into the IncidentGraph."""
        self._canonical_events.append(event)
        
        # Add corresponding node in the graph
        node_id = event.event_id
        node_type_map = {
            "slack": NodeType.DECISION if event.category == "decision" else NodeType.ACTOR,
            "github_commit": NodeType.COMMIT,
            "github_pr": NodeType.PR,
            "jira_ticket": NodeType.TICKET,
            "pagerduty_alert": NodeType.ALERT,
            "app_log": NodeType.ERROR_CLUSTER,
        }
        n_type = node_type_map.get(event.source_type.value, NodeType.ERROR_CLUSTER)
        
        self.graph.add_node(GraphNode(
            id=node_id,
            node_type=n_type,
            label=event.title or event.summary[:60],
            timestamp=event.event_timestamp,
            severity=event.severity.value,
            entity_ref=",".join(event.entity_refs),
            metadata=event.evidence_payload,
        ))

        # Add entity relations
        for s_ref in event.service_refs:
            svc_node_id = f"svc:{s_ref}"
            if svc_node_id not in self.graph.nodes:
                self.graph.add_node(GraphNode(
                    id=svc_node_id,
                    node_type=NodeType.SERVICE,
                    label=s_ref,
                ))
            self.graph.add_edge(GraphEdge(
                source=node_id,
                target=svc_node_id,
                relation=EdgeRelation.AFFECTS_SERVICE,
            ))

    def add_timeline_event(
        self,
        timestamp: str,
        source: str,
        description: str,
        evidence: str = "",
        category: str = "",
    ) -> None:
        """Add a timeline event to the shared context."""
        self._timeline_events.append({
            "timestamp": timestamp,
            "source": source,
            "description": description,
            "evidence": evidence,
            "category": category,
        })

    def set_agent_summary(self, agent_name: str, summary: str) -> None:
        """Store a high-level summary from an agent's analysis."""
        self._agent_summaries[agent_name] = summary

    # ------------------------------------------------------------------
    # Read / Query API
    # ------------------------------------------------------------------

    def query(
        self,
        source_agent: str | None = None,
        category: str | None = None,
        severity: str | None = None,
        keyword: str | None = None,
    ) -> list[dict]:
        """Query findings with optional filters."""
        results: list[Finding] = list(self._findings)

        if source_agent:
            results = [f for f in results if f.source_agent == source_agent]
        if category:
            results = [f for f in results if f.category == category]
        if severity:
            results = [f for f in results if f.severity == severity]
        if keyword:
            kw = keyword.lower()
            results = [
                f for f in results
                if kw in f.summary.lower() or kw in f.detail.lower()
            ]

        return [self._finding_to_dict(f) for f in results]

    def query_canonical_events(
        self,
        service: str | None = None,
        source_type: str | None = None,
        min_severity: str | None = None,
    ) -> list[CanonicalEvent]:
        """Query canonical events by service, source, or severity."""
        events = list(self._canonical_events)
        if service:
            s_clean = service.lower()
            events = [e for e in events if any(s_clean in s.lower() for s in e.service_refs)]
        if source_type:
            events = [e for e in events if e.source_type.value == source_type]
        return events

    def get_timeline(self) -> list[dict]:
        """Return all timeline events sorted chronologically."""
        return sorted(
            copy.deepcopy(self._timeline_events),
            key=lambda e: e.get("timestamp", ""),
        )

    def get_all_findings(self) -> list[dict]:
        """Return all findings as serialisable dicts."""
        return [self._finding_to_dict(f) for f in self._findings]

    def get_agent_summaries(self) -> dict[str, str]:
        """Return the high-level summary from each agent."""
        return dict(self._agent_summaries)

    def get_critical_findings(self) -> list[dict]:
        """Return only critical-severity findings."""
        return self.query(severity="critical")

    # ------------------------------------------------------------------
    # Snapshot — for trajectory logging & audit
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """Return a serialisable snapshot of the entire context and graph."""
        return {
            "incident_id": self.incident_id,
            "incident_title": self.incident_title,
            "total_findings": len(self._findings),
            "total_timeline_events": len(self._timeline_events),
            "total_canonical_events": len(self._canonical_events),
            "findings_by_agent": self._count_by("source_agent"),
            "findings_by_category": self._count_by("category"),
            "findings_by_severity": self._count_by("severity"),
            "agent_summaries": dict(self._agent_summaries),
            "graph_summary": self.graph.to_summary_dict(),
            "registered_services": [s.service_id for s in self.registry.services.values()],
            "registered_actors": [a.display_name for a in self.registry.actors.values()],
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _finding_to_dict(f: Finding) -> dict:
        return {
            "source_agent": f.source_agent,
            "category": f.category,
            "summary": f.summary,
            "detail": f.detail,
            "timestamp": f.timestamp,
            "evidence": f.evidence,
            "severity": f.severity,
            "metadata": f.metadata,
        }

    def _count_by(self, attr: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self._findings:
            val = getattr(f, attr, "unknown")
            counts[val] = counts.get(val, 0) + 1
        return counts
