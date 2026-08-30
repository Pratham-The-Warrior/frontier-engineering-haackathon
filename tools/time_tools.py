"""
Tools for timestamp normalisation, lag correlation, and temporal clustering.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def normalise_timestamp(ts: str) -> str:
    """
    Normalise a timestamp string to a consistent ISO-8601 UTC format.
    Handles common variations (with/without Z, timezone offsets, etc.).
    """
    if not isinstance(ts, str) or not ts.strip():
        return ""
    ts = ts.strip()
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return ts


def events_in_window(
    events: list[dict],
    centre_time: str,
    window_minutes: int = 5,
    timestamp_key: str = "timestamp",
) -> list[dict]:
    """Return events within ±*window_minutes* of *centre_time*."""
    if not centre_time:
        return []
    try:
        centre = datetime.fromisoformat(str(centre_time).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return []

    window = timedelta(minutes=window_minutes)
    result = []
    for ev in events:
        try:
            val = ev.get(timestamp_key)
            if not val:
                continue
            ev_dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        except (ValueError, KeyError, TypeError):
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
            a_val = a.get(ts_key)
            if not a_val:
                continue
            a_dt = datetime.fromisoformat(str(a_val).replace("Z", "+00:00"))
        except (ValueError, KeyError, TypeError):
            continue
        for b in events_b:
            try:
                b_val = b.get(ts_key)
                if not b_val:
                    continue
                b_dt = datetime.fromisoformat(str(b_val).replace("Z", "+00:00"))
            except (ValueError, KeyError, TypeError):
                continue
            if abs(a_dt - b_dt) <= window:
                pairs.append({
                    "event_a": a,
                    "event_b": b,
                    "time_delta_seconds": abs((a_dt - b_dt).total_seconds()),
                })

    pairs.sort(key=lambda p: p["time_delta_seconds"])
    return pairs


def correlate_events_with_lag(
    cause_candidates: list[dict],
    effect_events: list[dict],
    max_lag_minutes: int = 180,
    ts_key: str = "timestamp",
) -> list[dict]:
    """
    Detect asymmetric causal lag pairs (where cause STRICTLY PRECEDES effect
    within a realistic propagation window, e.g. canary rollout or cache expiry).
    """
    causal_pairs = []
    max_lag = timedelta(minutes=max_lag_minutes)

    for cause in cause_candidates:
        try:
            c_val = cause.get(ts_key)
            if not c_val:
                continue
            c_dt = datetime.fromisoformat(str(c_val).replace("Z", "+00:00"))
        except (ValueError, KeyError, TypeError):
            continue

        for effect in effect_events:
            try:
                e_val = effect.get(ts_key)
                if not e_val:
                    continue
                e_dt = datetime.fromisoformat(str(e_val).replace("Z", "+00:00"))
            except (ValueError, KeyError, TypeError):
                continue

            # Strict precedence: cause must happen before effect
            if timedelta(seconds=0) <= (e_dt - c_dt) <= max_lag:
                causal_pairs.append({
                    "cause_event": cause,
                    "effect_event": effect,
                    "lag_minutes": round((e_dt - c_dt).total_seconds() / 60, 1),
                    "confidence": "high" if (e_dt - c_dt).total_seconds() < 1800 else "medium",
                })

    causal_pairs.sort(key=lambda p: p["lag_minutes"])
    return causal_pairs


def detect_gaps(
    events: list[dict],
    min_gap_minutes: int = 10,
    ts_key: str = "timestamp",
) -> list[dict]:
    """
    Find gaps in the event stream longer than *min_gap_minutes*.
    Useful for identifying periods of missing observability.
    """
    valid_events = [e for e in events if e.get(ts_key)]
    sorted_events = sorted(valid_events, key=lambda e: str(e.get(ts_key, "")))
    gaps = []
    min_gap = timedelta(minutes=min_gap_minutes)

    for i in range(1, len(sorted_events)):
        try:
            prev = datetime.fromisoformat(str(sorted_events[i - 1][ts_key]).replace("Z", "+00:00"))
            curr = datetime.fromisoformat(str(sorted_events[i][ts_key]).replace("Z", "+00:00"))
        except (ValueError, KeyError, TypeError):
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
        if not start_ts or not end_ts:
            return 0
        start = datetime.fromisoformat(str(start_ts).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(end_ts).replace("Z", "+00:00"))
        return max(0, int((end - start).total_seconds() / 60))
    except (ValueError, TypeError):
        return 0
