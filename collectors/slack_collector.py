"""
Slack Collector — fetches real incident threads from Slack workspaces.

Supports:
  1. Slack Web API (Bot token with channels:history, users:read scopes)
  2. Manual paste / file upload fallback

Output matches the existing slack_thread.json schema.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests


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
            }
        else:
            info = {"name": user_id, "role": "Team Member"}
    except Exception:
        info = {"name": user_id, "role": "Team Member"}

    cache[user_id] = info
    return info


def fetch_channel_messages(
    token: str,
    channel_id: str,
    oldest: str | None = None,
    latest: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """
    Fetch messages from a Slack channel within a time window.

    Args:
        token: Slack Bot Token (xoxb-...)
        channel_id: Slack channel ID (C01234ABCDE)
        oldest: Unix timestamp or ISO — start of window
        latest: Unix timestamp or ISO — end of window
        limit: Max messages

    Returns:
        List in standard schema: [{timestamp, user, role, message}]
    """
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

        messages.append({
            "timestamp": _slack_ts_to_iso(msg.get("ts", "")),
            "user": user_info["name"],
            "role": user_info["role"],
            "message": msg.get("text", ""),
        })

    return messages


def fetch_thread_replies(
    token: str,
    channel_id: str,
    thread_ts: str,
    limit: int = 200,
) -> list[dict]:
    """
    Fetch all replies in a specific Slack thread.

    Args:
        token: Slack Bot Token
        channel_id: Channel containing the thread
        thread_ts: Thread timestamp (parent message ts)
        limit: Max replies

    Returns:
        Same schema as fetch_channel_messages
    """
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

        messages.append({
            "timestamp": _slack_ts_to_iso(msg.get("ts", "")),
            "user": user_info["name"],
            "role": user_info["role"],
            "message": msg.get("text", ""),
        })

    return messages


def search_channels(token: str, query: str = "incident") -> list[dict]:
    """Search for incident-related channels."""
    resp = requests.get(
        f"{_SLACK_API}/conversations.list",
        headers=_headers(token),
        params={"types": "public_channel,private_channel", "limit": 200},
        timeout=15,
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")

    channels = []
    for ch in data.get("channels", []):
        name = ch.get("name", "")
        if query.lower() in name.lower():
            channels.append({
                "id": ch["id"],
                "name": name,
                "topic": ch.get("topic", {}).get("value", ""),
                "num_members": ch.get("num_members", 0),
            })

    return channels


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
    Supports common formats like:
      [2025-03-15T14:30:00Z] Sarah Chen: DB pool is exhausted
      14:30 - Sarah: something happened
    """
    import re
    messages = []

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # Try pattern: [timestamp] user (role): message
        m = re.match(r"\[([^\]]+)\]\s+(.+?)(?:\s*\(([^)]+)\))?\s*:\s*(.*)", line)
        if m:
            messages.append({
                "timestamp": m.group(1),
                "user": m.group(2).strip(),
                "role": m.group(3) or "Team Member",
                "message": m.group(4).strip(),
            })
            continue

        # Try pattern: timestamp - user: message
        m = re.match(r"(\S+)\s*[-–]\s*(.+?):\s*(.*)", line)
        if m:
            messages.append({
                "timestamp": m.group(1),
                "user": m.group(2).strip(),
                "role": "Team Member",
                "message": m.group(3).strip(),
            })
            continue

        # Fallback: treat as a plain message
        messages.append({
            "timestamp": "",
            "user": "Unknown",
            "role": "Team Member",
            "message": line,
        })

    return messages


def _to_slack_ts(time_str: str) -> str:
    """Convert ISO timestamp to Slack's Unix timestamp format."""
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return str(dt.timestamp())
    except (ValueError, TypeError):
        return time_str  # already a unix timestamp
