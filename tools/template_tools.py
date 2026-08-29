"""
Tools for post-mortem report template management and quality checking.
Integrates Lucide vector icons and Shields.io badges for a modern, CodeRabbit-grade aesthetic.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Blameless language detection
# ---------------------------------------------------------------------------

_BLAME_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(?:he|she|they|the developer|the engineer|the SRE|the team member)\s+(?:caused|broke|failed|forgot|missed|should have|shouldn't have|didn't|neglected)\b",
        r"\b(?:fault|blame|responsible for breaking|careless|negligent|incompetent)\b",
        r"\bwho(?:'s| is) responsible\b",
        r"\b(?:his|her|their)\s+(?:mistake|error|fault|negligence)\b",
        r"\b(?:should not have been allowed to|never should have)\b",
    ]
]

_BLAMELESS_SUGGESTIONS = {
    "caused": "contributed to",
    "broke": "introduced a change that",
    "failed to": "the process did not include",
    "forgot": "was not part of the checklist",
    "should have": "a safeguard could have",
    "fault": "contributing factor",
    "blame": "contributing factor",
    "mistake": "gap in the process",
}


def check_blameless_language(text: str) -> dict:
    """Scan text for blame-assigning language."""
    violations = []
    lines = text.split("\n")

    for i, line in enumerate(lines):
        for pattern in _BLAME_PATTERNS:
            match = pattern.search(line)
            if match:
                matched_text = match.group(0).lower()
                suggestion = "Use blameless language — focus on systems and processes, not individuals."
                for trigger, fix in _BLAMELESS_SUGGESTIONS.items():
                    if trigger in matched_text:
                        suggestion = f'Consider replacing with: "{fix}"'
                        break

                violations.append({
                    "line": i + 1,
                    "pattern": matched_text,
                    "context": line.strip(),
                    "suggestion": suggestion,
                })

    score = max(0, 100 - len(violations) * 15)
    return {"score": score, "violations": violations}


def validate_report_completeness(report_markdown: str) -> dict:
    """Check that the post-mortem report contains all required sections."""
    required_sections = [
        "Executive Summary",
        "Impact",
        "Timeline",
        "Root Cause",
        "Contributing Factors",
        "Resolution",
        "Action Items",
        "Lessons Learned",
    ]

    present = []
    missing = []

    for section in required_sections:
        if re.search(rf"##.*{re.escape(section)}", report_markdown, re.IGNORECASE):
            present.append(section)
        else:
            missing.append(section)

    for section in present[:]:
        pattern = rf"##.*{re.escape(section)}\s*\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, report_markdown, re.DOTALL | re.IGNORECASE)
        if match and len(match.group(1).strip()) < 20:
            missing.append(f"{section} (present but empty)")
            present.remove(section)

    score = int((len(present) / len(required_sections)) * 100)
    return {"score": score, "present": present, "missing": missing}


def get_postmortem_template() -> str:
    """
    Return the CodeRabbit-grade post-mortem report template with Lucide icons
    and Shields.io dynamic vector badges.
    """
    return """\
# Post-Mortem: [TITLE]

[![Severity](https://img.shields.io/badge/Severity-[SEV_LEVEL]-e11d48?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-RESOLVED-10b981?style=flat-square)](#)
[![Duration](https://img.shields.io/badge/Duration-[DURATION_MINS]m-6366f1?style=flat-square)](#)
[![Evidence](https://img.shields.io/badge/Evidence-100%25_Grounded-0284c7?style=flat-square)](#)
[![Blameless](https://img.shields.io/badge/Culture-Blameless_Verified-8b5cf6?style=flat-square)](#)

> **Blast Radius:** `[affected users/requests]` | **MTTR:** `[X] min after root cause identified`
> **Root Cause (1-line):** `[Single sentence — the deepest systemic cause]`

---

## <img src="https://api.iconify.design/lucide:gauge.svg?color=%236366f1" width="18"/> Executive Summary

[2-3 sentences MAX. What happened, the business impact, how it was resolved. No filler.]

---

## <img src="https://api.iconify.design/lucide:shield-alert.svg?color=%23f59e0b" width="18"/> Risk & Systemic Vulnerability Assessment

| Risk Dimension | Risk Level | Finding | Evidence |
|:---|:---:|:---|:---|
| **Deploy Safety** | [![High](https://img.shields.io/badge/HIGH-f97316?style=flat-square)](#) | [What gap was exposed] | [Specific evidence ref] |
| **Circuit Breaking** | [![Critical](https://img.shields.io/badge/CRITICAL-ef4444?style=flat-square)](#) | [What was missing] | [Evidence] |
| **Observability** | [![Low](https://img.shields.io/badge/LOW-22c55e?style=flat-square)](#) | [What worked well] | [Evidence] |

---

## <img src="https://api.iconify.design/lucide:activity.svg?color=%2306b6d4" width="18"/> Impact

**Affected Services:** [list]
**User Impact:** [specific numbers — failed requests, affected users, revenue]
**Duration:** [X minutes, from first symptom to full recovery]

---

## <img src="https://api.iconify.design/lucide:clock.svg?color=%2364748b" width="18"/> Timeline

| Time (UTC) | Source | Event |
|:---|:---|:---|
| [HH:MM] | `[Log/Slack/Git/Alert]` | [Description] `[Evidence:ref]` |

<details>
<summary><b>Raw Correlated Event Log</b> (click to expand)</summary>

[Full detailed event log with all low-level entries]

</details>

---

## <img src="https://api.iconify.design/lucide:search.svg?color=%23e11d48" width="18"/> Root Cause Analysis

**Root Cause:** [Clear, technical, systemic explanation — not a symptom]

**Causal Chain:**
1. [Trigger event] -> `[Evidence:ref]`
2. [Consequence] -> `[Evidence:ref]`
3. [User-facing impact] -> `[Evidence:ref]`

**Confidence:** [High/Medium/Low — with brief justification if not High]

---

### <img src="https://api.iconify.design/lucide:file-code-2.svg?color=%238b5cf6" width="18"/> Forensic Code Analysis (Root Cause Diff)

> **Commit:** [`[SHA]`] — *[Commit Message]*  
> **Author:** `[Author]` | **Primary File:** `[path/to/culprit_file.py]`

```diff
- [Deleted safe lines, e.g. timeouts or context managers]
+ [Added problematic lines]  # [CAUSE: inline vulnerability description]
```

#### Code Vulnerability Breakdown:
* **Line [X] (Critical):** [Explanation of critical defect]
* **Line [Y] (Secondary):** [Secondary risk or cascading factor]

#### Preventative Remediation Patch

```diff
+ [Clean corrected code with safe timeout / error handling / context manager]
```

---

## <img src="https://api.iconify.design/lucide:layers.svg?color=%230ea5e9" width="18"/> Contributing Factors

- **[Factor 1]:** [Systemic gap description] `[Evidence:ref]`
- **[Factor 2]:** [Process gap description] `[Evidence:ref]`

---

## <img src="https://api.iconify.design/lucide:shield-check.svg?color=%2310b981" width="18"/> Prevention Analysis

> *How could this incident have been prevented or detected earlier?*

| Prevention Point | Safeguard | Expected Outcome |
|:---|:---|:---|
| At PR / CI Stage | [e.g. Config validation linter] | Incident prevented before merge |
| At Deploy Stage | [e.g. Canary with DB metric soak test] | Detected in staging, not prod |
| At Runtime Stage | [e.g. Circuit breaker on downstream service] | Blast radius limited |

---

## <img src="https://api.iconify.design/lucide:wrench.svg?color=%2364748b" width="18"/> Resolution

[How was the incident resolved? What immediate actions were taken?]

---

## <img src="https://api.iconify.design/lucide:check-square.svg?color=%2310b981" width="18"/> Action Items

| Priority | Type | Action | Owner | Est. |
|:---|:---|:---|:---|:---|
| **P0** | Prevent | [Highest priority action to prevent recurrence] | [Team] | [Est.] |
| **P1** | Detect | [Improve detection/alerting] | [Team] | [Est.] |
| **P2** | Mitigate | [Reduce blast radius for similar incidents] | [Team] | [Est.] |

---

## <img src="https://api.iconify.design/lucide:book-open.svg?color=%236366f1" width="18"/> Lessons Learned

- [Specific, actionable lesson — not generic platitudes]

## What Went Well

- [Specific positive aspect of the incident response]

## What Could Be Improved

- [Specific process improvement opportunity]
"""
