"""
Agent 6: Report Writer
Generates the final, polished, blameless post-mortem report.
Incorporates Lucide vector icons and Shields.io dynamic badges for a modern, CodeRabbit-grade aesthetic.
"""

from __future__ import annotations

import json
import re
from typing import Any

from agents.llm_client import call_llm, MODEL
from tools.template_tools import check_blameless_language, validate_report_completeness, get_postmortem_template

SYSTEM_PROMPT = """\
You are an expert technical writer specializing in incident post-mortem reports
at top-tier engineering organisations (Google, Stripe, Cloudflare).

Your job is to take the root cause analysis, unified timeline, and git forensic diff data
to produce a polished, professional, blameless post-mortem report styled with modern Lucide vector icons
and Shields.io dynamic badges.

## OUTPUT FORMAT — FOLLOW THIS EXACTLY

You MUST follow the template structure provided below. Do NOT deviate.

### 1. Vector Badge Banner (mandatory)
Start with the title, then standard operational badges:
- [![Severity](https://img.shields.io/badge/Severity-[SEV_LEVEL]-e11d48?style=flat-square)](#)
- [![Status](https://img.shields.io/badge/Status-RESOLVED-10b981?style=flat-square)](#)
- [![Duration](https://img.shields.io/badge/Duration-[X]m-6366f1?style=flat-square)](#)

### 2. Lucide Vector Icon Headers (mandatory)
Use the exact Lucide icon HTML tags inside the section headers as demonstrated in the template:
- `## <img src="https://api.iconify.design/lucide:gauge.svg?color=%236366f1" width="18"/> Executive Summary`
- `## <img src="https://api.iconify.design/lucide:shield-alert.svg?color=%23f59e0b" width="18"/> Risk & Systemic Vulnerability Assessment`
- `## <img src="https://api.iconify.design/lucide:activity.svg?color=%2306b6d4" width="18"/> Impact`
- `## <img src="https://api.iconify.design/lucide:clock.svg?color=%2364748b" width="18"/> Timeline`
- `## <img src="https://api.iconify.design/lucide:search.svg?color=%23e11d48" width="18"/> Root Cause Analysis`
- `### <img src="https://api.iconify.design/lucide:file-code-2.svg?color=%238b5cf6" width="18"/> Forensic Code Analysis (Root Cause Diff)`
- `## <img src="https://api.iconify.design/lucide:layers.svg?color=%230ea5e9" width="18"/> Contributing Factors`
- `## <img src="https://api.iconify.design/lucide:shield-check.svg?color=%2310b981" width="18"/> Prevention Analysis`
- `## <img src="https://api.iconify.design/lucide:check-square.svg?color=%2310b981" width="18"/> Action Items`

### 3. Risk & Vulnerability Table with Vector Badges (mandatory)
In the Risk table, use Shields.io badges for the levels:
- `[![Critical](https://img.shields.io/badge/CRITICAL-ef4444?style=flat-square)](#)`
- `[![High](https://img.shields.io/badge/HIGH-f97316?style=flat-square)](#)`
- `[![Medium](https://img.shields.io/badge/MEDIUM-eab308?style=flat-square)](#)`
- `[![Low](https://img.shields.io/badge/LOW-22c55e?style=flat-square)](#)`

### 4. Forensic Code Analysis (Root Cause Diff) (mandatory)
Embed a dedicated sub-section under Root Cause with:
- Culprit commit metadata (Commit hash, author, primary file modified)
- The exact syntax-highlighted `diff` code block showing the problematic lines (`-` safe removed lines, `+` added risky lines) with inline comments like `# [CAUSE: ...]` or `# [LEAK: ...]`
- Clear breakdown bullet points explaining the line-by-line vulnerability
- The clean `diff` Remediation Patch (`# [FIX: ...]`)

### 5. Evidence Citations (mandatory throughout)
Every factual claim MUST include an evidence tag in backticks:
- Log citations: `[Log:HH:MM:SS]` or `[Log:service-name:HH:MM]`
- Slack citations: `[Slack:@username:HH:MM]`
- Git citations: `[Git:short-hash]` or `[Deploy:version]`
- Alert citations: `[Alert:alert-name]`

### 6. Conciseness Rules
- Executive Summary: MAXIMUM 3 sentences
- Total report core content: under 900 words (excluding tables and details blocks)
- Use <details> blocks for raw data or verbose supporting evidence
- 100% Blameless: focus on systems and processes, never on individuals.
"""


def run(
    root_cause_data: dict,
    timeline_data: dict,
    git_findings: dict | None = None,
    incident_title: str = "Incident",
    trajectory: list[dict] | None = None,
) -> dict:
    """
    Run the Report Writer agent to generate the final post-mortem with Lucide icons and forensic code diffs.
    """
    if trajectory is None:
        trajectory = []

    # Clean inputs
    clean_rca = {k: v for k, v in root_cause_data.items() if k != "_trajectory"}
    clean_timeline = {k: v for k, v in timeline_data.items() if k != "_trajectory"}
    clean_git = {k: v for k, v in (git_findings or {}).items() if k != "_trajectory"}

    template = get_postmortem_template()

    user_prompt = f"""Write a complete post-mortem report for: "{incident_title}"

## Root Cause Analysis
{json.dumps(clean_rca, indent=2)}

## Unified Timeline & Incident Phases
{json.dumps(clean_timeline, indent=2)}

## Forensic Git & Code Diff Findings
{json.dumps(clean_git.get("forensic_code_diff", clean_git.get("most_likely_culprit", {})), indent=2)}

## Template — FOLLOW THIS STRUCTURE EXACTLY
{template}

IMPORTANT REMINDERS:
- Include the top dynamic Shields.io badge banner
- Include the Lucide icon HTML tags on every section header as demonstrated in the template
- In the Risk Assessment TABLE, use Shields.io vector badges for risk levels
- Include the Forensic Code Analysis syntax-highlighted `diff` code block with inline `# [CAUSE: ...]` comments and the remediation patch
- Include evidence citation tags on EVERY factual claim: `[Log:HH:MM]`, `[Slack:@user]`, `[Git:hash]`
- Include the Prevention Analysis TABLE
- Keep Executive Summary to 3 sentences MAX
- Use <details> blocks for raw/verbose data
- Output pure Markdown only — no JSON."""

    result = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=MODEL,
        max_tokens=4096,
        json_mode=False,
    )

    report_markdown = result["content"]

    trajectory.append({
        "agent": "report_writer",
        "step": "report_generation",
        "model": result["model"],
        "usage": result["usage"],
        "latency_seconds": result["latency_seconds"],
        "report_length_chars": len(report_markdown),
    })

    # Quality verification using tools
    blameless_check = check_blameless_language(report_markdown)
    completeness_check = validate_report_completeness(report_markdown)
    citation_count = len(re.findall(r"`\[(?:Log|Slack|Git|Alert|Deploy):[^\]]+\]`", report_markdown))
    has_diff_block = "```diff" in report_markdown

    trajectory.append({
        "agent": "report_writer",
        "step": "quality_verification",
        "tools_used": ["check_blameless_language", "validate_report_completeness", "citation_count", "diff_check"],
        "blameless_score": blameless_check["score"],
        "completeness_score": completeness_check["score"],
        "blameless_violations": len(blameless_check["violations"]),
        "missing_sections": completeness_check["missing"],
        "evidence_citations_found": citation_count,
        "has_forensic_diff": has_diff_block,
    })

    # Revision if needed
    needs_revision = (
        blameless_check["score"] < 80 or
        completeness_check["score"] < 80 or
        citation_count < 3 or
        not has_diff_block
    )

    if needs_revision:
        revision_issues = []
        if blameless_check["violations"]:
            revision_issues.append(
                "BLAMELESS LANGUAGE ISSUES:\n" +
                "\n".join(
                    f"- Line {v['line']}: '{v['pattern']}' in '{v['context']}'. {v['suggestion']}"
                    for v in blameless_check["violations"]
                )
            )
        if completeness_check["missing"]:
            revision_issues.append(
                "MISSING SECTIONS:\n" +
                "\n".join(f"- {s}" for s in completeness_check["missing"])
            )
        if citation_count < 3:
            revision_issues.append(
                f"INSUFFICIENT EVIDENCE CITATIONS: Add at least 5 citation tags like `[Log:14:05:12]`, `[Slack:@user]`, `[Git:hash]`."
            )
        if not has_diff_block:
            revision_issues.append(
                "MISSING FORENSIC DIFF: Ensure you include the ```diff block showing the culprit code change with inline # [CAUSE: ...] comments and remediation patch."
            )

        revision_prompt = f"""Revise this post-mortem report to fix these quality issues:

{chr(10).join(revision_issues)}

## Current Report
{report_markdown}

Output the complete revised report in Markdown. Keep the same structure."""

        revision_result = call_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=revision_prompt,
            model=MODEL,
            max_tokens=4096,
            json_mode=False,
        )

        report_markdown = revision_result["content"]

        # Re-check quality
        blameless_check = check_blameless_language(report_markdown)
        completeness_check = validate_report_completeness(report_markdown)
        citation_count = len(re.findall(r"`\[(?:Log|Slack|Git|Alert|Deploy):[^\]]+\]`", report_markdown))
        has_diff_block = "```diff" in report_markdown

        trajectory.append({
            "agent": "report_writer",
            "step": "revision",
            "model": revision_result["model"],
            "usage": revision_result["usage"],
            "latency_seconds": revision_result["latency_seconds"],
            "revised_blameless_score": blameless_check["score"],
            "revised_completeness_score": completeness_check["score"],
            "revised_evidence_citations": citation_count,
            "has_forensic_diff": has_diff_block,
        })

    return {
        "report_markdown": report_markdown,
        "quality_scores": {
            "blameless_score": blameless_check["score"],
            "completeness_score": completeness_check["score"],
            "evidence_citations": citation_count,
            "has_forensic_diff": has_diff_block,
            "blameless_violations": blameless_check["violations"],
            "missing_sections": completeness_check["missing"],
        },
        "_trajectory": trajectory,
    }
