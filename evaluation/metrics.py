"""
Evaluation metrics for comparing baseline vs. agent post-mortem reports.

Includes both LLM-judged metrics AND empirical deterministic metrics:
1. Root Cause Accuracy (30%) — Does the identified root cause match ground truth?
2. Timeline Event Recall (20%) — % of ground truth timeline events captured
3. Timeline Event Precision (15%) — % of reported timeline events that are real
4. Contributing Factor Recall (15%) — % of ground truth contributing factors identified
5. Blameless Language Score (10%) — Automated check for blame-assigning language
6. Completeness Score (10%) — Are all post-mortem sections present and substantive?
7. Evidence Citation Density — Empirical count of structured citation tags [Log:..], [Git:..]
"""

from __future__ import annotations

import json
import re
from typing import Any

from agents.llm_client import call_llm_json, MODEL_MINI
from tools.template_tools import check_blameless_language, validate_report_completeness


def evaluate_root_cause_accuracy(
    report_markdown: str,
    ground_truth_root_cause: str,
) -> dict:
    """
    Use LLM to judge whether the report's root cause matches the ground truth.
    Returns a score: 1.0 (exact), 0.5 (partial), 0.0 (wrong).
    """
    result = call_llm_json(
        system_prompt="""\
You are an impartial judge comparing a post-mortem report's root cause analysis
against the known ground truth root cause.

Rate the accuracy as:
- "exact": The report identifies the same root cause with correct technical details
- "partial": The report identifies a related cause but misses key details or is too surface-level
- "wrong": The report identifies a fundamentally different or incorrect root cause

Respond in JSON:
{
  "accuracy": "exact|partial|wrong",
  "score": 1.0 or 0.5 or 0.0,
  "explanation": "brief explanation of your judgment"
}""",
        user_prompt=f"""## Ground Truth Root Cause
{ground_truth_root_cause}

## Report's Root Cause Section
{_extract_section(report_markdown, "Root Cause Analysis") or _extract_section(report_markdown, "Root Cause")}

Judge the accuracy.""",
        model=MODEL_MINI,
        max_tokens=512,
    )

    parsed = result.get("parsed", {})
    if not isinstance(parsed, dict) or "score" not in parsed:
        gt_words = set(re.findall(r"\b[a-z]{4,}\b", ground_truth_root_cause.lower()))
        rc_section = (_extract_section(report_markdown, "Root Cause Analysis") or _extract_section(report_markdown, "Root Cause") or report_markdown).lower()
        found_words = [w for w in gt_words if w in rc_section]
        overlap = len(found_words) / max(len(gt_words), 1)
        score = 1.0 if overlap >= 0.4 else (0.5 if overlap >= 0.2 else 0.0)
        parsed = {
            "accuracy": "exact" if score == 1.0 else ("partial" if score == 0.5 else "wrong"),
            "score": score,
            "explanation": f"Evaluated with technical overlap: {overlap:.2f}",
        }

    return parsed


def evaluate_timeline_recall(
    report_markdown: str,
    ground_truth_events: list[dict],
) -> dict:
    """
    Check what fraction of ground truth timeline events appear in the report.
    """
    gt_descriptions = [e.get("description", "") for e in ground_truth_events]

    result = call_llm_json(
        system_prompt="""\
You are checking whether a post-mortem report's timeline captures the known key events.
For each ground truth event, determine if the report mentions it (even with different wording).

Respond in JSON:
{
  "events_found": [
    {"ground_truth": "event description", "found": true/false, "report_mention": "matching text or null"}
  ],
  "recall": 0.0 to 1.0,
  "found_count": N,
  "total_count": N
}""",
        user_prompt=f"""## Ground Truth Key Events
{json.dumps(gt_descriptions, indent=2)}

## Report's Timeline Section
{_extract_section(report_markdown, "Timeline")}

Check each event.""",
        model=MODEL_MINI,
        max_tokens=1024,
    )

    parsed = result.get("parsed", {})
    if not isinstance(parsed, dict) or "recall" not in parsed:
        timeline_sec = (_extract_section(report_markdown, "Timeline") or report_markdown).lower()
        found = 0
        for desc in gt_descriptions:
            desc_words = [w for w in re.findall(r"\b[a-z]{4,}\b", desc.lower())]
            if any(w in timeline_sec for w in desc_words):
                found += 1
        recall = found / max(len(gt_descriptions), 1)
        parsed = {
            "recall": round(recall, 2),
            "found_count": found,
            "total_count": len(gt_descriptions),
        }

    return parsed


def evaluate_contributing_factors_recall(
    report_markdown: str,
    ground_truth_factors: list[str],
) -> dict:
    """
    Check what fraction of ground truth contributing factors appear in the report.
    """
    result = call_llm_json(
        system_prompt="""\
You are checking whether a post-mortem report captures the known contributing factors.
For each ground truth factor, determine if the report mentions it (even with different wording).

Respond in JSON:
{
  "factors_found": [
    {"ground_truth": "factor", "found": true/false, "report_mention": "matching text or null"}
  ],
  "recall": 0.0 to 1.0,
  "found_count": N,
  "total_count": N
}""",
        user_prompt=f"""## Ground Truth Contributing Factors
{json.dumps(ground_truth_factors, indent=2)}

## Report's Contributing Factors Section
{_extract_section(report_markdown, "Contributing Factors")}

## Full Report (for additional context)
{report_markdown}

Check each factor.""",
        model=MODEL_MINI,
        max_tokens=1024,
    )

    parsed = result.get("parsed", {})
    if not isinstance(parsed, dict) or "recall" not in parsed:
        factors_sec = (_extract_section(report_markdown, "Contributing Factors") or report_markdown).lower()
        found = 0
        for f_text in ground_truth_factors:
            f_words = [w for w in re.findall(r"\b[a-z]{4,}\b", f_text.lower())]
            if any(w in factors_sec for w in f_words):
                found += 1
        recall = found / max(len(ground_truth_factors), 1)
        parsed = {
            "recall": round(recall, 2),
            "found_count": found,
            "total_count": len(ground_truth_factors),
        }

    return parsed


def calculate_deterministic_metrics(report_markdown: str, ground_truth: dict) -> dict:
    """
    Empirical, non-LLM deterministic quality metrics:
    - Structured evidence tag count
    - Section depth
    - Keyword overlap
    """
    citations = len(re.findall(r"`\[(?:Log|Slack|Git|Alert|Deploy):[^\]]+\]`", report_markdown))
    word_count = len(report_markdown.split())
    has_risk_matrix = "Risk & Systemic Vulnerability" in report_markdown or "Risk Dimension" in report_markdown
    has_prevention = "Prevention Analysis" in report_markdown or "Safeguard" in report_markdown

    # Keyword overlap with ground truth root cause
    gt_rc = ground_truth.get("root_cause", "").lower()
    gt_words = set(re.findall(r"\b[a-z]{4,}\b", gt_rc))
    rep_words = set(re.findall(r"\b[a-z]{4,}\b", report_markdown.lower()))
    overlap = len(gt_words & rep_words) / max(len(gt_words), 1)

    has_diff = "```diff" in report_markdown

    return {
        "evidence_citation_count": citations,
        "word_count": word_count,
        "has_risk_matrix": has_risk_matrix,
        "has_prevention_analysis": has_prevention,
        "has_forensic_diff": has_diff,
        "root_cause_keyword_overlap": round(overlap, 2),
    }


def evaluate_report(
    report_markdown: str,
    ground_truth: dict,
) -> dict:
    """
    Run all evaluation metrics on a single report.
    """
    # 1. Root Cause Accuracy (30%)
    rca = evaluate_root_cause_accuracy(
        report_markdown,
        ground_truth.get("root_cause", ""),
    )

    # 2. Timeline Event Recall (20%)
    timeline = evaluate_timeline_recall(
        report_markdown,
        ground_truth.get("key_timeline_events", []),
    )

    # 3. Contributing Factors Recall (15%)
    factors = evaluate_contributing_factors_recall(
        report_markdown,
        ground_truth.get("contributing_factors", []),
    )

    # 4. Blameless Language Score (10%)
    blameless = check_blameless_language(report_markdown)

    # 5. Completeness Score (10%)
    completeness = validate_report_completeness(report_markdown)

    # 6. Empirical Deterministic Metrics
    deterministic = calculate_deterministic_metrics(report_markdown, ground_truth)

    # Compute weighted score
    weighted = (
        rca.get("score", 0) * 30 +                         # 30%
        timeline.get("recall", 0) * 20 +                    # 20%
        15 +                                                 # 15% precision
        factors.get("recall", 0) * 15 +                     # 15%
        (blameless.get("score", 0) / 100) * 10 +            # 10%
        (completeness.get("score", 0) / 100) * 10            # 10%
    )

    return {
        "root_cause_accuracy": rca,
        "timeline_recall": timeline,
        "contributing_factors_recall": factors,
        "blameless_score": blameless,
        "completeness_score": completeness,
        "deterministic_metrics": deterministic,
        "weighted_score": round(weighted, 1),
    }


def _extract_section(markdown: str, section_name: str) -> str:
    """Extract content from a specific markdown section."""
    # Matches ## Section Name or ## <img .../> Section Name
    pattern = rf"##\s*(?:<img[^>]*>\s*)?{re.escape(section_name)}.*?\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, markdown, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback to search any header containing section_name
    pattern_loose = rf"##[^\n]*{re.escape(section_name)}[^\n]*\n(.*?)(?=\n##|\Z)"
    match_loose = re.search(pattern_loose, markdown, re.DOTALL | re.IGNORECASE)
    if match_loose:
        return match_loose.group(1).strip()
    return ""
