"""
Slack Collector — fetches real incident threads from Slack workspaces.

Supports:
  1. Slack Web API (Bot token with channels:history, users:read, reactions:read scopes)
  2. Emoji reaction extraction (:white_check_mark: confirmation, :eyes: investigating)
  3. Thread hierarchy and reply chain preservation
  4. Manual paste / file upload fallback with automated sanitization
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
import requests

from tools.sanitizer import sanitize_dict, sanitize_text

_SLACK_API = "https://slack.com/api"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }


def _slack_ts_to_iso(ts: str) -> str:
    """Convert Slack timestamp (e.g. '1710512340.000100') to ISO 8601."""
    try:
        epoch = float(ts.split(".")[0])
        return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, TypeError):
        return ts


def _get_user_info(token: str, user_id: str, cache: dict) -> dict:
    """Fetch and cache Slack user info."""
    if user_id in cache:
        return cache[user_id]

    try:
        resp = requests.get(
            f"{_SLACK_API}/users.info",
            headers=_headers(token),
            params={"user": user_id},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            user = data["user"]
            info = {
                "name": user.get("real_name", user.get("name", user_id)),
                "role": user.get("profile", {}).get("title", "Team Member"),
                "email": user.get("profile", {}).get("email", ""),
            }
        else:
            info = {"name": user_id, "role": "Team Member", "email": ""}
    except Exception:
        info = {"name": user_id, "role": "Team Member", "email": ""}

    cache[user_id] = info
    return info


def _extract_reactions(msg: dict) -> dict[str, int]:
    """Extract emoji reactions with counts."""
    reactions = {}
    for r in msg.get("reactions", []):
        name = r.get("name", "")
        count = r.get("count", 1)
        if name:
            reactions[name] = count
    return reactions


def fetch_channel_messages(
    token: str,
    channel_id: str,
    oldest: str | None = None,
    latest: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """Fetch messages from a Slack channel within a time window."""
    params: dict[str, Any] = {"channel": channel_id, "limit": min(limit, 200)}
    if oldest:
        params["oldest"] = _to_slack_ts(oldest)
    if latest:
        params["latest"] = _to_slack_ts(latest)

    resp = requests.get(
        f"{_SLACK_API}/conversations.history",
        headers=_headers(token),
        params=params,
        timeout=15,
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")

    user_cache: dict = {}
    messages = []

    for msg in reversed(data.get("messages", [])):
        if msg.get("subtype") in ("channel_join", "channel_leave", "bot_add"):
            continue

        user_id = msg.get("user", "unknown")
        user_info = _get_user_info(token, user_id, user_cache)
        reactions = _extract_reactions(msg)
        text = sanitize_text(msg.get("text", ""))

        messages.append(sanitize_dict({
            "timestamp": _slack_ts_to_iso(msg.get("ts", "")),
            "user": user_info["name"],
            "user_id": user_id,
            "role": user_info["role"],
            "message": text,
            "reactions": reactions,
            "reply_count": msg.get("reply_count", 0),
            "thread_ts": msg.get("thread_ts", ""),
        }))

    return messages


def fetch_thread_replies(
    token: str,
    channel_id: str,
    thread_ts: str,
    limit: int = 200,
) -> list[dict]:
    """Fetch all replies in a specific Slack thread."""
    params: dict[str, Any] = {
        "channel": channel_id,
        "ts": thread_ts,
        "limit": min(limit, 200),
    }

    resp = requests.get(
        f"{_SLACK_API}/conversations.replies",
        headers=_headers(token),
        params=params,
        timeout=15,
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")

    user_cache: dict = {}
    messages = []

    for msg in data.get("messages", []):
        user_id = msg.get("user", "unknown")
        user_info = _get_user_info(token, user_id, user_cache)
        reactions = _extract_reactions(msg)
        text = sanitize_text(msg.get("text", ""))

        messages.append(sanitize_dict({
            "timestamp": _slack_ts_to_iso(msg.get("ts", "")),
            "user": user_info["name"],
            "user_id": user_id,
            "role": user_info["role"],
            "message": text,
            "reactions": reactions,
            "thread_ts": thread_ts,
        }))

    return messages


def test_connection(token: str) -> dict:
    """Test Slack connectivity."""
    try:
        resp = requests.get(
            f"{_SLACK_API}/auth.test",
            headers=_headers(token),
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            return {
                "status": "connected",
                "team": data.get("team", ""),
                "user": data.get("user", ""),
                "team_id": data.get("team_id", ""),
            }
        return {"status": "error", "message": data.get("error", "Auth failed")}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def parse_pasted_messages(text: str) -> list[dict]:
    """
    Parse pasted chat messages as a fallback when no Slack API is available.
    """
    messages = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # Pattern: [timestamp] user (role): message
        m = re.match(r"\[([^\]]+)\]\s+(.+?)(?:\s*\(([^)]+)\))?\s*:\s*(.*)", line)
        if m:
            messages.append({
                "timestamp": m.group(1),
                "user": m.group(2).strip(),
                "role": m.group(3) or "Team Member",
                "message": sanitize_text(m.group(4).strip()),
                "reactions": {},
            })
            continue

        # Pattern: timestamp - user: message
        m = re.match(r"(\S+)\s*[-–]\s*(.+?):\s*(.*)", line)
        if m:
            messages.append({
                "timestamp": m.group(1),
                "user": m.group(2).strip(),
                "role": "Team Member",
                "message": sanitize_text(m.group(3).strip()),
                "reactions": {},
            })
            continue

        messages.append({
            "timestamp": "",
            "user": "Unknown",
            "role": "Team Member",
            "message": sanitize_text(line),
            "reactions": {},
        })

    return messages


def _to_slack_ts(time_str: str) -> str:
    """Convert ISO timestamp to Slack's Unix timestamp format."""
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return str(dt.timestamp())
    except (ValueError, TypeError):
        return time_str
