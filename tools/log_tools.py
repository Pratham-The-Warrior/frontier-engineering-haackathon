"""
Tools for parsing and analyzing application / infrastructure logs.
These are callable by agents as structured tool functions.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


def parse_logs(raw_logs: list[dict]) -> list[dict]:
    """
    Parse raw log entries into a normalised list of structured records.
    Ensures every entry has the required keys with sane defaults.
    """
    parsed = []
    for entry in raw_logs:
        parsed.append({
            "timestamp": entry.get("timestamp", ""),
            "level": entry.get("level", "INFO").upper(),
            "service": entry.get("service", "unknown"),
            "message": entry.get("message", ""),
            "metadata": entry.get("metadata", {}),
        })
    # Sort chronologically
    parsed.sort(key=lambda e: e["timestamp"])
    return parsed


def filter_by_severity(logs: list[dict], min_level: str = "WARN") -> list[dict]:
    """
    Return only log entries at or above *min_level*.
    Severity order: DEBUG < INFO < WARN < ERROR < FATAL
    """
    order = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3, "FATAL": 4}
    threshold = order.get(min_level.upper(), 2)
    return [l for l in logs if order.get(l.get("level", "INFO"), 1) >= threshold]


def find_error_patterns(logs: list[dict]) -> list[dict]:
    """
    Detect recurring error signatures across log messages.
    Returns a list of patterns with count and first/last timestamps.
    """
    error_logs = filter_by_severity(logs, "ERROR")
    if not error_logs:
        return []

    # Simple fingerprinting: normalise numbers and UUIDs out of messages
    def _fingerprint(msg: str) -> str:
        msg = re.sub(r"\b[0-9a-f]{7,}\b", "<ID>", msg, flags=re.I)
        msg = re.sub(r"\b\d+\b", "<N>", msg)
        return msg

    buckets: dict[str, list[dict]] = {}
    for log in error_logs:
        fp = _fingerprint(log["message"])
        buckets.setdefault(fp, []).append(log)

    patterns = []
    for fp, entries in buckets.items():
        patterns.append({
            "pattern": fp,
            "count": len(entries),
            "first_seen": entries[0]["timestamp"],
            "last_seen": entries[-1]["timestamp"],
            "services": list({e["service"] for e in entries}),
            "sample_message": entries[0]["message"],
        })

    patterns.sort(key=lambda p: p["count"], reverse=True)
    return patterns


def detect_anomalies(logs: list[dict]) -> list[dict]:
    """
    Detect anomalous patterns in the log stream:
    - Sudden spike in error rate
    - New error messages that weren't seen before a reference time
    - Service-level transitions (healthy → unhealthy)
    """
    anomalies: list[dict] = []

    # --- Detect level transitions per service ---
    service_levels: dict[str, str] = {}
    for log in sorted(logs, key=lambda l: l.get("timestamp", "")):
        svc = log.get("service", "unknown")
        level = log.get("level", "INFO")
        prev = service_levels.get(svc, "INFO")
        if level in ("ERROR", "FATAL") and prev in ("INFO", "DEBUG"):
            anomalies.append({
                "type": "service_degradation",
                "timestamp": log["timestamp"],
                "service": svc,
                "description": f"{svc} transitioned from {prev} to {level}",
                "evidence": log["message"],
            })
        service_levels[svc] = level

    # --- Count errors per minute bucket ---
    error_logs = filter_by_severity(logs, "ERROR")
    if len(error_logs) >= 3:
        # Group by minute
        minute_counts: Counter = Counter()
        for log in error_logs:
            minute = log["timestamp"][:16]  # YYYY-MM-DDTHH:MM
            minute_counts[minute] += 1

        sorted_minutes = sorted(minute_counts.items())
        for i in range(1, len(sorted_minutes)):
            prev_count = sorted_minutes[i - 1][1]
            curr_count = sorted_minutes[i][1]
            if curr_count >= 3 and curr_count > prev_count * 2:
                anomalies.append({
                    "type": "error_spike",
                    "timestamp": sorted_minutes[i][0],
                    "description": f"Error count spiked from {prev_count} to {curr_count} errors/min",
                    "evidence": f"Minute {sorted_minutes[i][0]}",
                })

    return anomalies


def summarise_logs(logs: list[dict]) -> dict[str, Any]:
    """High-level summary statistics for a set of logs."""
    level_counts = Counter(l.get("level", "INFO") for l in logs)
    service_counts = Counter(l.get("service", "unknown") for l in logs)
    return {
        "total_entries": len(logs),
        "level_distribution": dict(level_counts),
        "services": dict(service_counts),
        "time_range": {
            "start": logs[0]["timestamp"] if logs else "",
            "end": logs[-1]["timestamp"] if logs else "",
        },
    }
