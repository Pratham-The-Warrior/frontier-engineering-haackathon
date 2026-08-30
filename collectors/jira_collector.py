"""
Jira Collector — Bi-directional integration with Jira Cloud / Server.

Supports:
  1. Ingesting active incident tickets, linked issues, bug reports, and sprint tasks via Jira REST API v3.
  2. Searching historical incident tickets for recurrence patterns using JQL.
  3. Exporting post-mortem action items as new Jira tickets with priority, component, and assignee mapping.
  4. Offline manual paste / fallback parsing.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any, Optional
import requests

from tools.sanitizer import sanitize_dict, sanitize_text


def _headers(email: str, api_token: str) -> dict:
    auth_str = f"{email}:{api_token}"
    encoded = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _clean_jira_url(base_url: str) -> str:
    """Normalize Jira base URL."""
    url = base_url.strip().rstrip("/")
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"
    return url


def test_connection(base_url: str, email: str, api_token: str) -> dict:
    """Test Jira connectivity and verify user credentials."""
    url = f"{_clean_jira_url(base_url)}/rest/api/3/myself"
    try:
        resp = requests.get(url, headers=_headers(email, api_token), timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "status": "connected",
                "display_name": data.get("displayName", ""),
                "email": data.get("emailAddress", email),
                "account_id": data.get("accountId", ""),
                "time_zone": data.get("timeZone", ""),
            }
        elif resp.status_code in (401, 403):
            return {"status": "error", "message": "Authentication failed. Check email and API token."}
        return {"status": "error", "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def fetch_incident_tickets(
    base_url: str,
    email: str,
    api_token: str,
    project_key: str = "",
    jql: str = "",
    max_results: int = 50,
) -> list[dict]:
    """
    Fetch incident-related Jira tickets matching project or JQL.
    """
    clean_url = _clean_jira_url(base_url)
    endpoint = f"{clean_url}/rest/api/3/search"

    if not jql:
        if project_key:
            jql = f"project = '{project_key}' ORDER BY created DESC"
        else:
            jql = "issuetype in (Incident, Bug, Problem) ORDER BY created DESC"

    params = {
        "jql": jql,
        "maxResults": min(max_results, 100),
        "fields": ["summary", "description", "status", "priority", "assignee", "reporter", "created", "updated", "resolutiondate", "issuelinks", "components", "labels"],
    }

    try:
        resp = requests.get(endpoint, headers=_headers(email, api_token), params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"Jira API search failed: {e}")

    tickets = []
    for issue in data.get("issues", []):
        fields = issue.get("fields", {})
        
        # Extract description text safely from Atlassian Document Format or plain string
        raw_desc = fields.get("description")
        desc_text = _extract_adf_text(raw_desc) if isinstance(raw_desc, dict) else str(raw_desc or "")

        assignee = fields.get("assignee") or {}
        reporter = fields.get("reporter") or {}
        priority = fields.get("priority") or {}
        status = fields.get("status") or {}

        tickets.append(sanitize_dict({
            "key": issue.get("key", ""),
            "summary": fields.get("summary", ""),
            "description": desc_text,
            "status": status.get("name", "Unknown"),
            "priority": priority.get("name", "Medium"),
            "created_at": fields.get("created", ""),
            "updated_at": fields.get("updated", ""),
            "resolved_at": fields.get("resolutiondate", ""),
            "assignee": assignee.get("displayName", "Unassigned"),
            "assignee_email": assignee.get("emailAddress", ""),
            "reporter": reporter.get("displayName", "Unknown"),
            "components": [c.get("name") for c in fields.get("components", []) if isinstance(c, dict)],
            "labels": fields.get("labels", []),
            "url": f"{clean_url}/browse/{issue.get('key', '')}",
        }))

    return tickets


def fetch_ticket_details(
    base_url: str,
    email: str,
    api_token: str,
    issue_key: str,
) -> dict:
    """Fetch full details and changelog for a specific Jira issue."""
    clean_url = _clean_jira_url(base_url)
    endpoint = f"{clean_url}/rest/api/3/issue/{issue_key}?expand=changelog"

    try:
        resp = requests.get(endpoint, headers=_headers(email, api_token), timeout=15)
        resp.raise_for_status()
        issue = resp.json()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch Jira ticket {issue_key}: {e}")

    fields = issue.get("fields", {})
    changelog = issue.get("changelog", {}).get("histories", [])

    changes = []
    for h in changelog:
        created = h.get("created", "")
        author = h.get("author", {}).get("displayName", "Unknown")
        for item in h.get("items", []):
            changes.append({
                "timestamp": created,
                "author": author,
                "field": item.get("field", ""),
                "from": item.get("fromString", ""),
                "to": item.get("toString", ""),
            })

    return sanitize_dict({
        "key": issue_key,
        "summary": fields.get("summary", ""),
        "status": fields.get("status", {}).get("name", ""),
        "priority": fields.get("priority", {}).get("name", ""),
        "created_at": fields.get("created", ""),
        "changes": changes,
    })


def create_postmortem_tickets(
    base_url: str,
    email: str,
    api_token: str,
    project_key: str,
    action_items: list[dict],
) -> list[dict]:
    """
    Publish action items to Jira as structured Task / Improvement tickets.
    """
    clean_url = _clean_jira_url(base_url)
    endpoint = f"{clean_url}/rest/api/3/issue"
    created_tickets = []

    for item in action_items:
        priority_str = str(item.get("priority") or "Medium")
        jira_priority = "High" if "P0" in priority_str or "P1" in priority_str else "Medium"
        
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": item.get("summary", "Post-Mortem Action Item"),
                "issuetype": {"name": "Task"},
                "priority": {"name": jira_priority},
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": item.get("description", "Automated post-mortem action item."),
                                }
                            ],
                        }
                    ],
                },
                "labels": ["postmortem", "incident-prevention"],
            }
        }

        try:
            resp = requests.post(endpoint, headers=_headers(email, api_token), json=payload, timeout=15)
            if resp.status_code in (200, 201):
                res_data = resp.json()
                created_tickets.append({
                    "key": res_data.get("key"),
                    "id": res_data.get("id"),
                    "url": f"{clean_url}/browse/{res_data.get('key')}",
                    "summary": item.get("summary"),
                })
        except Exception as e:
            print(f"Failed to create Jira ticket: {e}")

    return created_tickets


def parse_pasted_jira_tickets(text: str) -> list[dict]:
    """
    Parse pasted Jira search results or text lists as offline fallback.
    Matches lines like:
      PROD-1024 [P1] [Resolved] Database connection leak in auth service
    """
    tickets = []
    pattern = re.compile(r"([A-Z]{2,10}-\d+)\s*(?:\[([^\]]+)\])?\s*(?:\[([^\]]+)\])?\s*[:\-–]?\s*(.*)")

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            key = m.group(1)
            p1 = m.group(2) or "Medium"
            status = m.group(3) or "Open"
            summary = m.group(4) or ""
            tickets.append({
                "key": key,
                "summary": sanitize_text(summary),
                "priority": p1,
                "status": status,
                "created_at": "",
            })

    return tickets


def _extract_adf_text(adf_node: Any) -> str:
    """Extract plain text from Atlassian Document Format (ADF) JSON structure."""
    if not isinstance(adf_node, dict):
        return str(adf_node or "")
    
    text_chunks = []
    def _traverse(node):
        if isinstance(node, dict):
            if node.get("type") == "text" and "text" in node:
                text_chunks.append(node["text"])
            for child in node.get("content", []):
                _traverse(child)
        elif isinstance(node, list):
            for child in node:
                _traverse(child)

    _traverse(adf_node)
    joined = " ".join(text_chunks)
    return re.sub(r"\s+", " ", joined).strip()
