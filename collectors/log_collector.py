"""
Log Collector — ingests application logs from various sources.

Supports:
  1. JSON / JSONL file upload
  2. Plain text log file parsing
  3. Direct JSON paste
  4. (Future: Datadog, CloudWatch, Elastic APIs)

Output matches the existing logs.jsonl schema.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any


def parse_json_logs(content: str) -> list[dict]:
    """
    Parse JSON or JSONL formatted log content.

    Handles:
      - A JSON array of log objects
      - JSONL (one JSON object per line)
    """
    content = content.strip()

    # Try as JSON array first
    if content.startswith("["):
        try:
            logs = json.loads(content)
            return [_normalize_log(l) for l in logs]
        except json.JSONDecodeError:
            pass

    # Try as JSONL
    logs = []
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            logs.append(_normalize_log(obj))
        except json.JSONDecodeError:
            continue

    return logs


def parse_text_logs(content: str) -> list[dict]:
    """
    Parse plain text log content using common log format patterns.

    Supports formats like:
      2025-03-15T14:30:12Z ERROR [user-service] Failed to acquire connection
      2025-03-15 14:30:12 [ERROR] user-service: Failed to acquire connection
      Mar 15 14:30:12 user-service ERROR: Failed to acquire connection
    """
    logs = []

    # Pattern 1: ISO timestamp + level + [service] + message
    p1 = re.compile(
        r"(\d{4}-\d{2}-\d{2}T[\d:.]+Z?)\s+"
        r"(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL)\s+"
        r"\[?([^\]\s]+)\]?\s+(.+)"
    )

    # Pattern 2: ISO date + time + [level] + service: message
    p2 = re.compile(
        r"(\d{4}-\d{2}-\d{2}\s+[\d:.]+)\s+"
        r"\[(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL)\]\s+"
        r"(\S+?):\s+(.+)"
    )

    # Pattern 3: syslog-style
    p3 = re.compile(
        r"(\w{3}\s+\d{1,2}\s+[\d:]+)\s+"
        r"(\S+)\s+"
        r"(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL):\s+(.+)"
    )

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue

        for pattern in [p1, p2]:
            m = pattern.match(line)
            if m:
                logs.append({
                    "timestamp": m.group(1),
                    "level": _normalize_level(m.group(2)),
                    "service": m.group(3),
                    "message": m.group(4),
                    "metadata": {},
                })
                break
        else:
            m = p3.match(line)
            if m:
                logs.append({
                    "timestamp": m.group(1),
                    "level": _normalize_level(m.group(3)),
                    "service": m.group(2),
                    "message": m.group(4),
                    "metadata": {},
                })
            else:
                # Fallback: treat as unstructured log
                logs.append({
                    "timestamp": "",
                    "level": "INFO",
                    "service": "unknown",
                    "message": line,
                    "metadata": {},
                })

    return logs


def parse_uploaded_file(content: str, filename: str) -> list[dict]:
    """
    Auto-detect format based on filename extension and content.

    Args:
        content: File content as string
        filename: Original filename (used for format detection)

    Returns:
        Normalized log entries
    """
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext in ("json", "jsonl"):
        return parse_json_logs(content)

    if ext in ("log", "txt", ""):
        # Try JSON first (some .log files are actually JSON)
        content_stripped = content.strip()
        if content_stripped.startswith("[") or content_stripped.startswith("{"):
            result = parse_json_logs(content)
            if result:
                return result
        return parse_text_logs(content)

    # CSV-like logs
    if ext == "csv":
        return _parse_csv_logs(content)

    # Default: try text parsing
    return parse_text_logs(content)


def _parse_csv_logs(content: str) -> list[dict]:
    """Parse CSV-formatted logs."""
    import csv
    from io import StringIO

    reader = csv.DictReader(StringIO(content))
    logs = []
    for row in reader:
        logs.append(_normalize_log(dict(row)))
    return logs


def _normalize_log(entry: dict) -> dict:
    """Normalize a log entry to the standard schema."""
    # Common field name mappings
    timestamp_fields = ["timestamp", "time", "ts", "@timestamp", "datetime", "date", "created_at"]
    level_fields = ["level", "severity", "log_level", "loglevel", "priority"]
    service_fields = ["service", "source", "app", "application", "component", "host", "logger"]
    message_fields = ["message", "msg", "text", "log", "body", "description"]

    def _find(entry: dict, candidates: list[str]) -> str:
        for key in candidates:
            if key in entry:
                return str(entry[key])
            # Case-insensitive
            for k in entry:
                if k.lower() == key.lower():
                    return str(entry[k])
        return ""

    timestamp = _find(entry, timestamp_fields)
    level = _normalize_level(_find(entry, level_fields) or "INFO")
    service = _find(entry, service_fields) or "unknown"
    message = _find(entry, message_fields)

    # Collect remaining fields as metadata
    used_keys = set()
    for candidates in [timestamp_fields, level_fields, service_fields, message_fields]:
        for k in entry:
            if k.lower() in [c.lower() for c in candidates]:
                used_keys.add(k)

    metadata = {k: v for k, v in entry.items() if k not in used_keys}

    return {
        "timestamp": timestamp,
        "level": level,
        "service": service,
        "message": message,
        "metadata": metadata if metadata else {},
    }


def _normalize_level(level: str) -> str:
    """Normalize log level to standard values."""
    level = level.upper().strip()
    mapping = {
        "DEBUG": "DEBUG",
        "INFO": "INFO",
        "INFORMATION": "INFO",
        "WARN": "WARN",
        "WARNING": "WARN",
        "ERROR": "ERROR",
        "ERR": "ERROR",
        "FATAL": "FATAL",
        "CRITICAL": "FATAL",
        "CRIT": "FATAL",
        "EMERGENCY": "FATAL",
        "EMERG": "FATAL",
    }
    return mapping.get(level, "INFO")
