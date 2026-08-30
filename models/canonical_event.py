"""
Universal Canonical Incident Event (UCIE) and Entity Models.

Defines the normalized data schema for all signals across Slack, GitHub,
Jira, PagerDuty, logs, and monitoring metrics.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class EventSourceType(str, Enum):
    SLACK = "slack"
    GITHUB_COMMIT = "github_commit"
    GITHUB_PR = "github_pr"
    GITHUB_CI = "github_ci"
    GITHUB_DEPLOY = "github_deploy"
    JIRA_TICKET = "jira_ticket"
    PAGERDUTY_ALERT = "pagerduty_alert"
    APP_LOG = "app_log"
    METRIC_ANOMALY = "metric_anomaly"
    HUMAN_DECISION = "human_decision"
    SYSTEM_INFERRED = "system_inferred"


class EventSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ActorEntity(BaseModel):
    """Normalized actor/user identity across platforms."""
    actor_id: str  # Canonical unique ID
    display_name: str
    email: Optional[str] = None
    role: str = "Team Member"
    platform_ids: dict[str, str] = Field(default_factory=dict)  # {"slack": "U123", "github": "sarah", "jira": "acc_456"}
    metadata: dict[str, Any] = Field(default_factory=dict)


class ServiceEntity(BaseModel):
    """Normalized service or infrastructure component."""
    service_id: str  # Canonical name (e.g. "auth-service")
    display_name: str
    tier: str = "tier-1"
    owner_team: str = "Unassigned"
    repo_url: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)  # ["auth-svc", "authentication", "AUTH"]
    dependencies: list[str] = Field(default_factory=list)  # ["db-cluster", "redis-session"]


class CanonicalEvent(BaseModel):
    """
    Universal Canonical Incident Event (UCIE)
    Every ingested telemetry point is normalized into this structure.
    """
    event_id: str = Field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:10].upper()}")
    source_type: EventSourceType
    source_system: str  # e.g. "slack.enterprise.com", "github.com/org/repo", "datadog"
    
    # Timestamps
    event_timestamp: str  # ISO-8601 UTC - when it occurred in the real world
    ingest_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    observed_timestamp: Optional[str] = None  # when telemetry first recorded it
    
    # Severity & Classification
    severity: EventSeverity = EventSeverity.INFO
    category: str = "general"  # error, deploy, decision, alert, communication, recovery, config
    
    # Actors & Entities
    actor: Optional[ActorEntity] = None
    service_refs: list[str] = Field(default_factory=list)  # ["auth-service", "checkout-service"]
    entity_refs: list[str] = Field(default_factory=list)   # ["PROD-1029", "commit:7a8b9c", "pr:#42"]
    
    # Semantic content
    title: str = ""
    summary: str = ""
    description: str = ""
    evidence_payload: dict[str, Any] = Field(default_factory=dict)
    
    # Cryptographic provenance & auditing
    raw_payload_hash: str = ""
    provenance_url: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    @classmethod
    def generate_deterministic_id(cls, source: str, raw_id: str, timestamp: str) -> str:
        """Create deterministic ID to prevent duplicate events on webhook retries."""
        raw_key = f"{source}:{raw_id}:{timestamp}"
        digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:12].upper()
        return f"EVT-{digest}"


class EntityRegistry(BaseModel):
    """Global registry of resolved actors and services for an incident."""
    actors: dict[str, ActorEntity] = Field(default_factory=dict)       # canonical_id -> ActorEntity
    services: dict[str, ServiceEntity] = Field(default_factory=dict)   # canonical_id -> ServiceEntity
    actor_alias_index: dict[str, str] = Field(default_factory=dict)   # platform:handle or handle -> canonical_id
    service_alias_index: dict[str, str] = Field(default_factory=dict) # alias_str -> canonical_id

    def register_actor(self, actor: ActorEntity) -> None:
        self.actors[actor.actor_id] = actor
        for platform, handle in actor.platform_ids.items():
            h_clean = handle.lower().strip()
            self.actor_alias_index[f"{platform.lower()}:{h_clean}"] = actor.actor_id
            self.actor_alias_index[h_clean] = actor.actor_id
        if actor.email:
            e_clean = actor.email.lower().strip()
            self.actor_alias_index[f"email:{e_clean}"] = actor.actor_id
            self.actor_alias_index[e_clean] = actor.actor_id
        n_clean = actor.display_name.lower().strip()
        self.actor_alias_index[f"name:{n_clean}"] = actor.actor_id
        self.actor_alias_index[n_clean] = actor.actor_id

    def register_service(self, service: ServiceEntity) -> None:
        self.services[service.service_id] = service
        self.service_alias_index[service.service_id.lower().strip()] = service.service_id
        for alias in service.aliases:
            self.service_alias_index[alias.lower().strip()] = service.service_id

    def resolve_actor(self, identifier: str, platform: str = "") -> Optional[ActorEntity]:
        if not identifier:
            return None
        clean = identifier.lower().strip()
        if platform:
            key = f"{platform.lower()}:{clean}"
            if key in self.actor_alias_index:
                return self.actors.get(self.actor_alias_index[key])
        if clean in self.actor_alias_index:
            return self.actors.get(self.actor_alias_index[clean])
        for prefix in ["name:", "email:"]:
            k = f"{prefix}{clean}"
            if k in self.actor_alias_index:
                return self.actors.get(self.actor_alias_index[k])
        if clean in self.actors:
            return self.actors[clean]
        return None

    def resolve_service(self, alias_or_name: str) -> Optional[ServiceEntity]:
        if not alias_or_name:
            return None
        clean = alias_or_name.lower().strip()
        if clean in self.service_alias_index:
            canonical_id = self.service_alias_index[clean]
            return self.services.get(canonical_id)
        return None
