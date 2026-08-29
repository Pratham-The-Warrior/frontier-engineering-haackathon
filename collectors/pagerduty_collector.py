"""
PagerDuty Collector — fetches real incident alerts from PagerDuty.

Supports:
  1. PagerDuty REST API v2 (API key authentication)
  2. Manual JSON / file upload fallback

Output matches the existing alerts.json schema.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests


_PD_API = "https://api.pagerduty.com"


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Token token={api_key}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.pagerduty+json;version=2",
    }


def fetch_incident_alerts(
    api_key: str,
    incident_id: str,
) -> list[dict]:
    """
    Fetch all alerts for a PagerDuty incident.

    Returns:
        List in the standard alerts schema:
        [{timestamp, severity, source, title, description}]
    """
    url = f"{_PD_API}/incidents/{incident_id}/alerts"
    resp = requests.get(url, headers=_headers(api_key), timeout=15)
    resp.raise_for_status()

    alerts = []
    for alert in resp.json().get("alerts", []):
        alerts.append({
            "timestamp": alert.get("created_at", ""),
            "severity": _map_severity(alert.get("severity", "info")),
            "source": "PagerDuty",
            "title": alert.get("summary", "Alert"),
            "description": alert.get("body", {}).get("details", {}).get("description", ""),
        })

    return alerts


def fetch_recent_incidents(
    api_key: str,
    since: str | None = None,
    until: str | None = None,
    statuses: list[str] | None = None,
    limit: int = 25,
) -> list[dict]:
    """
    Fetch recent incidents from PagerDuty.

    Args:
        api_key: PagerDuty API key
        since: ISO timestamp — start of window
        until: ISO timestamp — end of window
        statuses: Filter by status (triggered, acknowledged, resolved)
        limit: Max incidents

    Returns:
        List of incidents with metadata.
    """
    params: dict[str, Any] = {
        "sort_by": "created_at:desc",
        "limit": min(limit, 100),
    }
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    if statuses:
        params["statuses[]"] = statuses

    resp = requests.get(
        f"{_PD_API}/incidents",
        headers=_headers(api_key),
        params=params,
        timeout=15,
    )
    resp.raise_for_status()

    incidents = []
    for inc in resp.json().get("incidents", []):
        incidents.append({
            "id": inc.get("id", ""),
            "title": inc.get("title", ""),
            "status": inc.get("status", ""),
            "urgency": inc.get("urgency", ""),
            "created_at": inc.get("created_at", ""),
            "resolved_at": inc.get("last_status_change_at", ""),
            "service": inc.get("service", {}).get("summary", ""),
            "html_url": inc.get("html_url", ""),
        })

    return incidents


def fetch_incident_log_entries(
    api_key: str,
    incident_id: str,
) -> list[dict]:
    """
    Fetch timeline log entries for a PagerDuty incident.
    Returns chronological list of actions taken.
    """
    url = f"{_PD_API}/incidents/{incident_id}/log_entries"
    params = {"include[]": ["channels"], "is_overview": True}

    resp = requests.get(url, headers=_headers(api_key), params=params, timeout=15)
    resp.raise_for_status()

    entries = []
    for entry in resp.json().get("log_entries", []):
        entries.append({
            "timestamp": entry.get("created_at", ""),
            "type": entry.get("type", ""),
            "summary": entry.get("summary", ""),
            "agent": entry.get("agent", {}).get("summary", ""),
        })

    return entries


def test_connection(api_key: str) -> dict:
    """Test PagerDuty connectivity."""
    try:
        resp = requests.get(
            f"{_PD_API}/abilities",
            headers=_headers(api_key),
            timeout=10,
        )
        if resp.status_code == 200:
            return {
                "status": "connected",
                "abilities": resp.json().get("abilities", [])[:5],
            }
        if resp.status_code == 401:
            return {"status": "error", "message": "Invalid API key"}
        return {"status": "error", "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _map_severity(pd_severity: str) -> str:
    """Map PagerDuty severity to our schema."""
    mapping = {
        "critical": "critical",
        "error": "critical",
        "warning": "warning",
        "info": "info",
    }
    return mapping.get(pd_severity.lower(), "info")
