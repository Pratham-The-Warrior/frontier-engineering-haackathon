"""
Entity Resolver Tool — Multi-Modal Entity Resolution Engine (MMER).

Resolves disparate cross-platform representations of people, services, repositories,
and tickets into unified canonical entities and links them into an EntityRegistry.
"""

from __future__ import annotations

import re
from typing import Any
from models.canonical_event import ActorEntity, ServiceEntity, EntityRegistry


# Regex patterns for entity extraction
TICKET_PATTERN = re.compile(r"\b([A-Z]{2,10}-\d{1,6})\b")
PR_PATTERN = re.compile(r"(?:PR\s*#?|pull\s*request\s*#?|#)(\d{1,6})\b", re.IGNORECASE)
# Match commit hashes with 7 to 40 hex characters that are not pure digits
COMMIT_SHA_PATTERN = re.compile(r"\b(?=[0-9a-fA-F]{7,40}\b)(?![0-9]+\b)[0-9a-fA-F]{7,40}\b")
SLACK_MENTION_PATTERN = re.compile(r"<@([A-Z0-9]{8,12})>|@([a-zA-Z0-9_.-]+)")


class EntityResolver:
    """
    Infers, clusters, and canonicalizes actors and services across platforms.
    """

    def __init__(self, registry: EntityRegistry | None = None) -> None:
        self.registry = registry or EntityRegistry()

    def register_known_service(
        self,
        service_id: str,
        display_name: str,
        aliases: list[str] | None = None,
        dependencies: list[str] | None = None,
        owner_team: str = "Unassigned",
    ) -> ServiceEntity:
        service = ServiceEntity(
            service_id=service_id,
            display_name=display_name,
            aliases=aliases or [],
            dependencies=dependencies or [],
            owner_team=owner_team,
        )
        self.registry.register_service(service)
        return service

    def register_known_actor(
        self,
        actor_id: str,
        display_name: str,
        email: str | None = None,
        role: str = "Team Member",
        platform_ids: dict[str, str] | None = None,
    ) -> ActorEntity:
        actor = ActorEntity(
            actor_id=actor_id,
            display_name=display_name,
            email=email,
            role=role,
            platform_ids=platform_ids or {},
        )
        self.registry.register_actor(actor)
        return actor

    def resolve_actor_from_signal(
        self,
        name_or_handle: str,
        platform: str = "",
        role: str = "",
    ) -> ActorEntity:
        """Resolve an actor from any platform identifier, creating a canonical record if not present."""
        if not name_or_handle or name_or_handle.lower() in ("unknown", "system", "bot"):
            return ActorEntity(actor_id="system", display_name="System / Automation", role="System")

        # Try to resolve existing
        resolved = self.registry.resolve_actor(name_or_handle, platform=platform)
        if resolved:
            if role and resolved.role == "Team Member":
                resolved.role = role
            return resolved

        # Create new canonical actor
        clean_name = name_or_handle.strip().replace("@", "")
        canonical_id = re.sub(r"[^a-zA-Z0-9_]", "_", clean_name.lower())
        platform_ids = {platform: name_or_handle} if platform else {}
        email = f"{canonical_id}@company.internal" if "@" not in name_or_handle else name_or_handle

        actor = ActorEntity(
            actor_id=canonical_id,
            display_name=clean_name.title() if " " in clean_name else clean_name,
            email=email,
            role=role or "Team Member",
            platform_ids=platform_ids,
        )
        self.registry.register_actor(actor)
        return actor

    def resolve_service_from_signal(self, raw_service_name: str) -> ServiceEntity:
        """Resolve a service from log names, repo names, or alert titles."""
        if not raw_service_name or raw_service_name.lower() in ("unknown", "system"):
            return ServiceEntity(service_id="general-system", display_name="General System Infrastructure")

        resolved = self.registry.resolve_service(raw_service_name)
        if resolved:
            return resolved

        # Canonicalize service name
        clean_id = raw_service_name.strip().lower().replace("_", "-").replace(" ", "-")
        display_name = clean_id.replace("-", " ").title()

        service = ServiceEntity(
            service_id=clean_id,
            display_name=display_name,
            aliases=[raw_service_name, clean_id],
        )
        self.registry.register_service(service)
        return service

    def extract_entity_references(self, text: str) -> list[str]:
        """Extract all ticket keys, PRs, and commit hashes from text."""
        if not text:
            return []

        refs = set()
        for m in TICKET_PATTERN.finditer(text):
            refs.add(f"ticket:{m.group(1)}")
        for m in PR_PATTERN.finditer(text):
            refs.add(f"pr:#{m.group(1)}")
        for m in COMMIT_SHA_PATTERN.finditer(text):
            sha = m.group(0)
            if len(sha) in (7, 8, 40):
                refs.add(f"commit:{sha[:7]}")

        return sorted(refs)

    def extract_actors_mentioned(self, text: str) -> list[ActorEntity]:
        """Extract all @mentions or user references in message text."""
        if not text:
            return []

        actors = []
        for m in SLACK_MENTION_PATTERN.finditer(text):
            handle = m.group(1) or m.group(2)
            if handle:
                actor = self.resolve_actor_from_signal(handle, platform="slack")
                actors.append(actor)
        return actors

    def populate_from_incident_data(self, incident_data: dict) -> None:
        """Pre-populate registry from raw incident data (logs, slack, git, alerts)."""
        # Parse git commits
        for c in incident_data.get("git_commits.json", []):
            author = c.get("author", "")
            if author:
                self.resolve_actor_from_signal(author, platform="github")

        # Parse slack threads
        for msg in incident_data.get("slack_thread.json", []):
            user = msg.get("user", "")
            role = msg.get("role", "")
            if user:
                self.resolve_actor_from_signal(user, platform="slack", role=role)

        # Parse log services
        for log in incident_data.get("logs.jsonl", []):
            svc = log.get("service", "")
            if svc:
                self.resolve_service_from_signal(svc)
