"""
Tools for timestamp normalisation and temporal event correlation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def normalise_timestamp(ts: str) -> str:
    """
    Normalise a timestamp string to a consistent ISO-8601 UTC format.
    Handles common variations (with/without Z, timezone offsets, etc.).
    """
    ts = ts.strip()
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return ts  # return as-is if unparseable


def events_in_window(
    events: list[dict],
    centre_time: str,
    window_minutes: int = 5,
    timestamp_key: str = "timestamp",
) -> list[dict]:
    """Return events within ±*window_minutes* of *centre_time*."""
    try:
        centre = datetime.fromisoformat(centre_time.replace("Z", "+00:00"))
    except ValueError:
        return []

    window = timedelta(minutes=window_minutes)
    result = []
    for ev in events:
        try:
            ev_dt = datetime.fromisoformat(ev[timestamp_key].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            continue
        if abs(ev_dt - centre) <= window:
            result.append(ev)
    return result


def correlate_events(
    events_a: list[dict],
    events_b: list[dict],
    window_minutes: int = 5,
    ts_key: str = "timestamp",
) -> list[dict]:
    """
    Find temporally correlated pairs between two event lists.
    Returns pairs where events from A and B occur within *window_minutes*.
    """
    pairs = []
    window = timedelta(minutes=window_minutes)

    for a in events_a:
        try:
            a_dt = datetime.fromisoformat(a[ts_key].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            continue
        for b in events_b:
            try:
                b_dt = datetime.fromisoformat(b[ts_key].replace("Z", "+00:00"))
            except (ValueError, KeyError):
                continue
            if abs(a_dt - b_dt) <= window:
                pairs.append({
                    "event_a": a,
                    "event_b": b,
                    "time_delta_seconds": abs((a_dt - b_dt).total_seconds()),
                })

    pairs.sort(key=lambda p: p["time_delta_seconds"])
    return pairs


def detect_gaps(
    events: list[dict],
    min_gap_minutes: int = 10,
    ts_key: str = "timestamp",
) -> list[dict]:
    """
    Find gaps in the event stream longer than *min_gap_minutes*.
    Useful for identifying periods of missing observability.
    """
    sorted_events = sorted(events, key=lambda e: e.get(ts_key, ""))
    gaps = []
    min_gap = timedelta(minutes=min_gap_minutes)

    for i in range(1, len(sorted_events)):
        try:
            prev = datetime.fromisoformat(sorted_events[i - 1][ts_key].replace("Z", "+00:00"))
            curr = datetime.fromisoformat(sorted_events[i][ts_key].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            continue

        delta = curr - prev
        if delta >= min_gap:
            gaps.append({
                "gap_start": sorted_events[i - 1][ts_key],
                "gap_end": sorted_events[i][ts_key],
                "duration_minutes": round(delta.total_seconds() / 60, 1),
            })

    return gaps


def compute_duration(start_ts: str, end_ts: str) -> int:
    """Return duration in minutes between two timestamps."""
    try:
        start = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_ts.replace("Z", "+00:00"))
        return max(0, int((end - start).total_seconds() / 60))
    except ValueError:
        return 0
