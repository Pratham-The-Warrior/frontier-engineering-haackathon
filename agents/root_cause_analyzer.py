"""
Agent 5: Root Cause Analyzer (Agentic Multi-Hypothesis & Evidence Verification)
Performs causal reasoning on the unified timeline and IncidentContext to identify
the root cause, contributing factors, and causal chain.

Operates with an agentic loop:
1. Generates candidate root cause hypotheses
2. Runs evidence validation tools against each hypothesis
3. Ranks hypotheses by corroborating vs. contradicting signals
4. Synthesizes deep causal chain and prevention analysis
5. Self-verifies against timeline grounding and blameless language
"""

from __future__ import annotations

import json
from typing import Any

from agents.llm_client import call_llm_json, MODEL
from tools.evidence_tools import rank_hypotheses, assess_causal_chain, check_evidence

HYPOTHESIS_GENERATION_PROMPT = """\
You are an elite principal SRE and incident forensic investigator.
Your job is to examine an incident timeline and context to generate 2-3 distinct candidate hypotheses for the root cause.

For each hypothesis:
- Focus on the deepest systemic failure (not just the surface symptom).
- Account for all observed anomalies, timing of errors, and recent changes.
- Distinguish between code bugs, configuration drift, capacity exhaustion, race conditions, or external dependencies.

Respond in JSON:
{
  "hypotheses": [
    "Hypothesis 1: concise, detailed statement of what failed and why",
    "Hypothesis 2: alternative explanation or contributing mechanism",
    "Hypothesis 3: secondary or cascade failure hypothesis"
  ]
}
"""

DEEP_ANALYSIS_PROMPT = """\
You are an expert root cause analyst for production systems.
You are given:
1. The ranked candidate hypotheses backed by empirical evidence scores
2. The unified incident timeline with cross-source findings
3. Verification tool outputs and corroborating signals

Your task is to produce a deep, exhaustive root cause analysis JSON with zero hallucinations:

{
  "root_cause": {
    "summary": "One precise, technical sentence identifying the root cause.",
    "detail": "Comprehensive technical breakdown of exactly how the defect/misconfiguration manifested, propagated, and impacted the system.",
    "category": "configuration|code_bug|infrastructure|architecture|race_condition|external_dependency",
    "evidence": ["Specific evidence tags supporting this conclusion, e.g. [Log:14:05:12], [Git:8f3d1a]"],
    "confidence": "high|medium|low",
    "confidence_justification": "Why this confidence rating is warranted based on evidence density."
  },
  "causal_chain": [
    {
      "step": 1,
      "event": "Description of trigger / change",
      "caused_by": "Initial trigger or condition",
      "evidence": "Citation e.g. [Git:hash] or [Log:HH:MM:SS]"
    }
  ],
  "contributing_factors": [
    {
      "factor": "Systemic gap (e.g. missing validation, lack of circuit breaker, telemetry blindspot)",
      "type": "process_gap|missing_safeguard|design_flaw|testing_gap|monitoring_gap",
      "evidence": "Evidence citation"
    }
  ],
  "blast_radius": {
    "affected_components": ["service-a", "service-b"],
    "impact_severity": "P1|P2|P3",
    "estimated_user_impact": "Details of user/request impact"
  },
  "prevention_safeguards": [
    {
      "stage": "CI/PR|Canary/Deploy|Runtime",
      "safeguard": "Specific automated check or architectural control",
      "outcome": "How it would have neutralized the failure before or during the incident"
    }
  ]
}

Rules:
- Never assign personal blame (e.g., 'the developer forgot'). Focus purely on systemic and process factors.
- Ensure no subtle bug, cascade effect, or race condition is overlooked.
- Every causal link must be strictly grounded in the timeline data.
"""

VERIFICATION_PROMPT = """\
You are an adversarial SRE quality auditor reviewing a draft Root Cause Analysis.
Evaluate the analysis against the original timeline:

1. EVIDENCE GROUNDING: Are there any speculative claims lacking empirical support?
2. SUBTLE BUGS CHECK: Did the analysis miss any underlying race condition, timeout misconfiguration, or cascading failure?
3. BLAMELESS CULTURE: Is the analysis 100% focused on system vulnerabilities rather than individual engineer mistakes?
4. CAUSAL LOGIC: Does the cause strictly precede the effect in time?

Respond in JSON:
{
  "issues_found": [
    {
      "type": "unsupported_claim|shallow_analysis|missed_subtle_factor|blame_language",
      "description": "Exact issue identified",
      "suggestion": "How to refine the analysis"
    }
  ],
  "overall_quality": "good|needs_improvement",
  "refined_root_cause_summary": "If improved summary is needed, provide here, else null"
}
"""


def run(
    timeline_data: dict,
    incident_context: Any = None,
    trajectory: list[dict] | None = None,
) -> dict:
    """
    Run the Root Cause Analyzer agent with an agentic hypothesis-testing and evidence-validation loop.
    """
    if trajectory is None:
        trajectory = []

    clean_timeline = {k: v for k, v in timeline_data.items() if k != "_trajectory"}
    timeline_events = clean_timeline.get("unified_timeline", [])

    # =========================================================================
    # Step 1: Agentic Hypothesis Generation
    # =========================================================================
    hyp_prompt = f"""Review the incident timeline below and formulate 2-3 candidate hypotheses:

{json.dumps(clean_timeline, indent=2)}
"""
    hyp_result = call_llm_json(
        system_prompt=HYPOTHESIS_GENERATION_PROMPT,
        user_prompt=hyp_prompt,
        model=MODEL,
        max_tokens=1024,
    )
    raw_hypotheses = hyp_result.get("parsed", {}).get("hypotheses", [])
    if not raw_hypotheses:
        raw_hypotheses = ["Incident caused by primary service anomaly during recent configuration or code change."]

    trajectory.append({
        "agent": "root_cause_analyzer",
        "step": "hypothesis_generation",
        "hypotheses_count": len(raw_hypotheses),
        "hypotheses": raw_hypotheses,
        "latency_seconds": hyp_result["latency_seconds"],
    })

    # =========================================================================
    # Step 2: Agentic Tool Use — Empirical Evidence Checking & Ranking
    # =========================================================================
    ranked_hypotheses = rank_hypotheses(raw_hypotheses, timeline_events)

    trajectory.append({
        "agent": "root_cause_analyzer",
        "step": "evidence_validation_tool",
        "tools_used": ["rank_hypotheses", "check_evidence", "find_corroborating_events"],
        "ranked_results": [
            {
                "rank": h["rank"],
                "hypothesis": h["hypothesis"][:80],
                "score": h["score"],
                "evidence_strength": h["evidence_strength"],
                "supporting_count": h["supporting_count"],
            }
            for h in ranked_hypotheses
        ],
    })

    # =========================================================================
    # Step 3: Deep Causal Synthesis
    # =========================================================================
    synthesis_prompt = f"""## Unified Timeline
{json.dumps(clean_timeline, indent=2)}

## Ranked Hypotheses & Evidence Support (from Evidence Tools)
{json.dumps(ranked_hypotheses, indent=2)}

Perform a thorough, deep root cause analysis based on the highest-ranking evidence."""

    analysis_result = call_llm_json(
        system_prompt=DEEP_ANALYSIS_PROMPT,
        user_prompt=synthesis_prompt,
        model=MODEL,
        max_tokens=4096,
    )
    analysis = analysis_result["parsed"]

    trajectory.append({
        "agent": "root_cause_analyzer",
        "step": "deep_causal_synthesis",
        "root_cause_category": analysis.get("root_cause", {}).get("category"),
        "confidence": analysis.get("root_cause", {}).get("confidence"),
        "latency_seconds": analysis_result["latency_seconds"],
    })

    # =========================================================================
    # Step 4: Causal Chain Consistency Check Tool
    # =========================================================================
    causal_chain = analysis.get("causal_chain", [])
    chain_assessment = assess_causal_chain(causal_chain, timeline_events)

    trajectory.append({
        "agent": "root_cause_analyzer",
        "step": "causal_chain_validation_tool",
        "tools_used": ["assess_causal_chain"],
        "chain_valid": chain_assessment["chain_valid"],
        "overall_confidence": chain_assessment["overall_confidence"],
        "issues_found": chain_assessment["issues"],
    })

    # =========================================================================
    # Step 5: Adversarial Verification & Self-Correction
    # =========================================================================
    verification_input = {
        "analysis": analysis,
        "chain_assessment": chain_assessment,
        "timeline_sample": timeline_events[:15],
    }
    verification_result = call_llm_json(
        system_prompt=VERIFICATION_PROMPT,
        user_prompt=f"Audit this analysis:\n{json.dumps(verification_input, indent=2)}",
        model=MODEL,
        max_tokens=2048,
    )
    verification = verification_result["parsed"]

    if verification.get("refined_root_cause_summary") and verification["refined_root_cause_summary"] != "null":
        analysis["root_cause"]["summary"] = verification["refined_root_cause_summary"]

    analysis["ranked_hypotheses"] = ranked_hypotheses
    analysis["chain_assessment"] = chain_assessment
    analysis["verification"] = {
        "quality": verification.get("overall_quality", "good"),
        "issues_found": verification.get("issues_found", []),
    }

    # Record to shared IncidentContext if available
    if incident_context is not None:
        rc = analysis.get("root_cause", {})
        incident_context.add_finding(
            source_agent="root_cause_analyzer",
            category="root_cause",
            summary=rc.get("summary", ""),
            detail=rc.get("detail", ""),
            severity="critical",
            evidence="; ".join(rc.get("evidence", [])),
            metadata={"category": rc.get("category"), "confidence": rc.get("confidence")},
        )
        for factor in analysis.get("contributing_factors", []):
            incident_context.add_finding(
                source_agent="root_cause_analyzer",
                category="contributing_factor",
                summary=factor.get("factor", ""),
                severity="warning",
                evidence=factor.get("evidence", ""),
                metadata={"type": factor.get("type")},
            )

    analysis["_trajectory"] = trajectory
    return analysis
