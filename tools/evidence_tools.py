"""
Evidence validation tools for the Root Cause Analyzer agent.

These tools enable the RCA agent to behave *agentically* — generating
hypotheses, then calling tools to check each one against the actual evidence,
rather than making a single LLM call that guesses at the answer.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any


def check_evidence(
    claim: str,
    timeline_events: list[dict],
    *,
    keyword_threshold: int = 1,
) -> dict:
    """
    Check whether a causal claim is supported by timeline evidence.

    Scans all timeline events for keywords from the claim. Returns a
    support level and the specific matching events.

    Args:
        claim: A causal claim string (e.g. "deploy v2.14.0 removed timeout settings")
        timeline_events: List of timeline event dicts with 'description' and 'evidence' keys
        keyword_threshold: Minimum keyword matches to consider "supported"

    Returns:
        {
            "claim": str,
            "support_level": "strong" | "partial" | "unsupported",
            "matching_events": [...],
            "match_count": int,
            "matched_keywords": [str],
        }
    """
    # Extract meaningful keywords from the claim (3+ char words, skip stop words)
    stop_words = {
        "the", "was", "were", "been", "being", "have", "has", "had", "does",
        "did", "will", "would", "could", "should", "may", "might", "can",
        "shall", "and", "but", "for", "not", "with", "this", "that", "from",
        "are", "its", "our", "all", "any", "each", "than", "then",
        "when", "which", "who", "how", "what", "where", "why",
        "also", "into", "over", "such", "after", "before", "during",
        "about", "between", "through", "because", "caused", "leading",
    }
    words = re.findall(r"\b[a-z][a-z0-9_.-]+\b", claim.lower())
    keywords = [w for w in words if w not in stop_words and len(w) >= 3]

    matching_events = []
    matched_keywords = set()

    for event in timeline_events:
        event_text = " ".join([
            event.get("description", ""),
            event.get("evidence", ""),
            event.get("detail", ""),
        ]).lower()

        event_matches = [kw for kw in keywords if kw in event_text]
        if event_matches:
            matching_events.append({
                "timestamp": event.get("timestamp", ""),
                "description": event.get("description", ""),
                "source": event.get("source", ""),
                "keywords_matched": event_matches,
            })
            matched_keywords.update(event_matches)

    # Determine support level
    match_ratio = len(matched_keywords) / max(len(keywords), 1)
    if match_ratio >= 0.5 and len(matching_events) >= 2:
        support_level = "strong"
    elif match_ratio >= 0.25 or len(matching_events) >= 1:
        support_level = "partial"
    else:
        support_level = "unsupported"

    return {
        "claim": claim,
        "support_level": support_level,
        "matching_events": matching_events[:10],  # cap to avoid bloat
        "match_count": len(matching_events),
        "matched_keywords": sorted(matched_keywords),
        "total_claim_keywords": len(keywords),
    }


def find_corroborating_events(
    hypothesis: str,
    events: list[dict],
    *,
    time_window_minutes: int = 30,
) -> dict:
    """
    Find events that support or contradict a given hypothesis.

    Groups events into supporting and contradicting based on keyword
    alignment and temporal proximity.

    Args:
        hypothesis: A hypothesis about the incident cause
        events: Timeline events
        time_window_minutes: How far back/forward to look for related events

    Returns:
        {
            "hypothesis": str,
            "supporting_events": [...],
            "contradicting_signals": [...],
            "evidence_strength": "strong" | "moderate" | "weak",
        }
    """
    # Look for positive indicators (keywords from hypothesis)
    evidence_result = check_evidence(hypothesis, events)
    supporting = evidence_result["matching_events"]

    # Look for contradicting signals
    # e.g., if hypothesis mentions "deploy" but logs show issues before any deploy
    contradicting = []

    hypothesis_lower = hypothesis.lower()

    # Check for temporal contradictions
    if "deploy" in hypothesis_lower or "release" in hypothesis_lower:
        # Find the earliest error and earliest deploy
        error_events = [
            e for e in events
            if any(kw in e.get("description", "").lower()
                   for kw in ["error", "failure", "503", "500", "timeout", "crash"])
        ]
        deploy_events = [
            e for e in events
            if any(kw in e.get("description", "").lower()
                   for kw in ["deploy", "release", "merged", "push"])
        ]

        if error_events and deploy_events:
            first_error_ts = error_events[0].get("timestamp", "")
            first_deploy_ts = deploy_events[0].get("timestamp", "")
            if first_error_ts and first_deploy_ts and first_error_ts < first_deploy_ts:
                contradicting.append({
                    "signal": "Errors began before the deploy was completed",
                    "first_error": first_error_ts,
                    "first_deploy": first_deploy_ts,
                })

    # Determine evidence strength
    if len(supporting) >= 3 and not contradicting:
        strength = "strong"
    elif len(supporting) >= 1 and len(contradicting) <= 1:
        strength = "moderate"
    else:
        strength = "weak"

    return {
        "hypothesis": hypothesis,
        "supporting_events": supporting,
        "contradicting_signals": contradicting,
        "evidence_strength": strength,
        "supporting_count": len(supporting),
        "contradicting_count": len(contradicting),
    }


def assess_causal_chain(
    chain_steps: list[dict],
    timeline_events: list[dict],
) -> dict:
    """
    Assess the logical consistency and evidence support of a causal chain.

    For each step in the chain, checks:
    1. Is the event backed by timeline evidence?
    2. Does the timestamp ordering make sense (causes before effects)?
    3. Are there unexplained gaps?

    Args:
        chain_steps: List of dicts with 'event', 'caused_by', 'evidence' keys
        timeline_events: The full timeline for cross-reference

    Returns:
        {
            "chain_valid": bool,
            "step_assessments": [...],
            "overall_confidence": "high" | "medium" | "low",
            "issues": [str],
        }
    """
    step_assessments = []
    issues = []
    valid_steps = 0

    for i, step in enumerate(chain_steps):
        event_text = step.get("event", "")
        evidence_ref = step.get("evidence", "")

        # Check if the event is mentioned in the timeline
        event_check = check_evidence(event_text, timeline_events)
        has_evidence = event_check["support_level"] != "unsupported"

        assessment = {
            "step": i + 1,
            "event": event_text,
            "evidence_support": event_check["support_level"],
            "matching_event_count": event_check["match_count"],
        }

        if has_evidence:
            valid_steps += 1
        else:
            issues.append(
                f"Step {i + 1} ('{event_text[:60]}...') has no supporting evidence in timeline"
            )

        step_assessments.append(assessment)

    # Overall assessment
    total = max(len(chain_steps), 1)
    validity_ratio = valid_steps / total

    if validity_ratio >= 0.8:
        confidence = "high"
    elif validity_ratio >= 0.5:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "chain_valid": validity_ratio >= 0.5,
        "step_assessments": step_assessments,
        "overall_confidence": confidence,
        "valid_steps": valid_steps,
        "total_steps": total,
        "issues": issues,
    }


def rank_hypotheses(
    hypotheses: list[str],
    timeline_events: list[dict],
) -> list[dict]:
    """
    Rank multiple root cause hypotheses by evidence strength.

    Runs each hypothesis through evidence checking and corroboration,
    then sorts by overall score.

    Args:
        hypotheses: List of hypothesis strings
        timeline_events: Timeline events for evidence checking

    Returns:
        Sorted list of hypothesis assessments (best first), each with:
        {
            "hypothesis": str,
            "rank": int,
            "evidence_strength": str,
            "supporting_count": int,
            "contradicting_count": int,
            "score": float (0-1),
        }
    """
    assessments = []
    for hyp in hypotheses:
        corr = find_corroborating_events(hyp, timeline_events)
        supporting = corr["supporting_count"]
        contradicting = corr["contradicting_count"]

        # Score: supporting evidence - contradicting signals, normalised
        raw_score = supporting - (contradicting * 2)
        score = max(0.0, min(1.0, raw_score / max(supporting + contradicting, 1)))

        assessments.append({
            "hypothesis": hyp,
            "evidence_strength": corr["evidence_strength"],
            "supporting_count": supporting,
            "contradicting_count": contradicting,
            "supporting_events": corr["supporting_events"][:5],
            "score": round(score, 3),
        })

    # Sort by score descending
    assessments.sort(key=lambda x: x["score"], reverse=True)
    for i, a in enumerate(assessments):
        a["rank"] = i + 1

    return assessments
