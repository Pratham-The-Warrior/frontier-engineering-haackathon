"""
Log Collector & Template Miner — ingests and clusters application logs.

Supports:
  1. JSON / JSONL file parsing
  2. Plain text log format parsing
  3. Drain3-style Log Template Mining to cluster 10,000+ logs into canonical templates
  4. Ingestion-time credential and PII sanitization
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from tools.sanitizer import sanitize_dict, sanitize_text


def parse_json_logs(content: str) -> list[dict]:
    """Parse JSON or JSONL formatted log content."""
    content = content.strip()

    if content.startswith("["):
        try:
            logs = json.loads(content)
            return [_normalize_log(l) for l in logs]
        except json.JSONDecodeError:
            pass

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
    """Parse plain text log content using common regex formats."""
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
                    "message": sanitize_text(m.group(4)),
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
                    "message": sanitize_text(m.group(4)),
                    "metadata": {},
                })
            else:
                logs.append({
                    "timestamp": "",
                    "level": "INFO",
                    "service": "unknown",
                    "message": sanitize_text(line),
                    "metadata": {},
                })

    return logs


def parse_uploaded_file(content: str, filename: str) -> list[dict]:
    """Auto-detect format based on filename extension and content."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext in ("json", "jsonl"):
        return parse_json_logs(content)

    if ext in ("log", "txt", ""):
        content_stripped = content.strip()
        if content_stripped.startswith("[") or content_stripped.startswith("{"):
            result = parse_json_logs(content)
            if result:
                return result
        return parse_text_logs(content)

    if ext == "csv":
        return _parse_csv_logs(content)

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
    """Normalize a log entry to the standard schema with sanitization."""
    timestamp_fields = ["timestamp", "time", "ts", "@timestamp", "datetime", "date", "created_at"]
    level_fields = ["level", "severity", "log_level", "loglevel", "priority"]
    service_fields = ["service", "source", "app", "application", "component", "host", "logger"]
    message_fields = ["message", "msg", "text", "log", "body", "description"]

    def _find(entry: dict, candidates: list[str]) -> str:
        for key in candidates:
            if key in entry:
                return str(entry[key])
            for k in entry:
                if k.lower() == key.lower():
                    return str(entry[k])
        return ""

    timestamp = _find(entry, timestamp_fields)
    level = _normalize_level(_find(entry, level_fields) or "INFO")
    service = _find(entry, service_fields) or "unknown"
    raw_message = _find(entry, message_fields)
    message = sanitize_text(raw_message)

    used_keys = set()
    for candidates in [timestamp_fields, level_fields, service_fields, message_fields]:
        for k in entry:
            if k.lower() in [c.lower() for c in candidates]:
                used_keys.add(k)

    metadata = {k: v for k, v in entry.items() if k not in used_keys}
    sanitized_metadata = sanitize_dict(metadata)

    return {
        "timestamp": timestamp,
        "level": level,
        "service": service,
        "message": message,
        "metadata": sanitized_metadata,
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


# ---------------------------------------------------------------------------
# Drain3-Style Log Template Miner
# ---------------------------------------------------------------------------

_VAR_PATTERNS = [
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<HEX>"),
    (re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b"), "<UUID>"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?\b"), "<IP:PORT>"),
    (re.compile(r"\b\d+\b"), "<NUM>"),
    (re.compile(r"\/[a-zA-Z0-9_\-\.\/]+"), "<PATH>"),
]


def extract_log_template(message: str) -> str:
    """
    Mask variable tokens (IPs, numbers, UUIDs, hex addresses, filepaths)
    to reveal the invariant log template.
    """
    template = message
    for pattern, replacement in _VAR_PATTERNS:
        template = pattern.sub(replacement, template)
    return template.strip()


def cluster_log_templates(logs: list[dict], min_count: int = 1) -> list[dict]:
    """
    Group thousands of log entries into high-signal template clusters.
    
    Returns:
        List of clusters with template signature, occurrence count,
        level, affected services, and sample log lines.
    """
    clusters: dict[str, dict] = {}

    for log in logs:
        msg = log.get("message", "")
        level = log.get("level", "INFO")
        service = log.get("service", "unknown")
        ts = log.get("timestamp", "")

        template = extract_log_template(msg)
        key = f"{level}:{service}:{template}"

        if key not in clusters:
            clusters[key] = {
                "template": template,
                "level": level,
                "service": service,
                "count": 0,
                "first_seen": ts,
                "last_seen": ts,
                "sample_messages": [],
            }

        c = clusters[key]
        c["count"] += 1
        if ts:
            if not c["first_seen"] or ts < c["first_seen"]:
                c["first_seen"] = ts
            if not c["last_seen"] or ts > c["last_seen"]:
                c["last_seen"] = ts
        if len(c["sample_messages"]) < 3:
            c["sample_messages"].append(msg)

    result = [c for c in clusters.values() if c["count"] >= min_count]
    # Sort descending by error severity and count
    severity_order = {"FATAL": 0, "ERROR": 1, "WARN": 2, "INFO": 3, "DEBUG": 4}
    result.sort(key=lambda x: (severity_order.get(x["level"], 5), -x["count"]))
    return result
