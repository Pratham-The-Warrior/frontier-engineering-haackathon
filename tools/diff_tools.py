"""
Forensic Diff & Code Risk Tools.
Enables the system to isolate, format, and highlight risky code blocks and diffs
with inline annotations, exactly like CodeRabbit and Git diff viewers.
"""

from __future__ import annotations

import re
from typing import Any


def detect_diff_risk_patterns(diff_text: str, files_changed: list[str] | None = None) -> list[dict]:
    """
    Scan a diff or commit summary for high-risk systemic anti-patterns.
    """
    risks = []
    text_lower = diff_text.lower()
    files = files_changed or []

    # 1. Connection / Resource Leak Risk
    if any(kw in text_lower for kw in ["removed timeout", "dropped timeout", "connection pool", "acquire", "pool settings"]):
        risks.append({
            "pattern": "Resource Management / Connection Pool Leak",
            "severity": "CRITICAL",
            "risk_type": "leak_vulnerability",
            "description": "Modification or removal of connection timeout/pool limits can cause unbounded pool exhaustion under load.",
        })

    # 2. Concurrency / Race Condition Risk
    if any(kw in text_lower for kw in ["thread", "async", "lock", "mutex", "race", "concurrent", "atomic"]):
        risks.append({
            "pattern": "Concurrency / State Synchronization Risk",
            "severity": "HIGH",
            "risk_type": "concurrency_flaw",
            "description": "Changes to state mutation without atomic locks or synchronized transactions can introduce race conditions.",
        })

    # 3. Memory / Cache Growth Risk
    if any(kw in text_lower for kw in ["cache", "memoize", "global dict", "ttl", "eviction", "leak", "unbounded"]):
        risks.append({
            "pattern": "Unbounded Memory Accumulation",
            "severity": "HIGH",
            "risk_type": "memory_leak",
            "description": "Cache or in-memory dictionary additions without TTL eviction policies cause progressive memory leaks.",
        })

    # 4. Database Query / Join Latency Risk
    if any(kw in text_lower for kw in ["join", "query", "unindexed", "scan", "select *", "n+1"]):
        risks.append({
            "pattern": "High Latency Database Query / N+1 Risk",
            "severity": "MEDIUM",
            "risk_type": "performance_degradation",
            "description": "Complex JOINs or unindexed queries hold database connections longer, accelerating resource depletion.",
        })

    # 5. Missing Error Handling / Fallback
    if any(kw in text_lower for kw in ["removed try", "catch all", "pass", "except: pass", "fallback removed"]):
        risks.append({
            "pattern": "Suppressed Error / Missing Fallback",
            "severity": "HIGH",
            "risk_type": "resilience_gap",
            "description": "Unhandled exceptions propagate to upstream services, causing cascading 500/503 errors.",
        })

    return risks


def build_forensic_diff_markdown(
    culprit_commit: dict,
    culprit_file: str = "",
    problematic_diff: str = "",
    remediation_diff: str = "",
    line_annotations: list[str] | None = None,
) -> str:
    """
    Format the complete Forensic Code Analysis markdown section.
    """
    sha = culprit_commit.get("sha", "unknown")[:7]
    author = culprit_commit.get("author", "Unknown Author")
    message = culprit_commit.get("message", "Commit change")
    file_path = culprit_file or (culprit_commit.get("files_changed", ["service.py"])[0] if culprit_commit.get("files_changed") else "unknown_file.py")

    annotations_md = ""
    if line_annotations:
        annotations_md = "\n#### Code Vulnerability Breakdown:\n" + "\n".join(f"* {ann}" for ann in line_annotations)

    md = f"""### <img src="https://api.iconify.design/lucide:file-code-2.svg?color=%238b5cf6" width="18"/> Forensic Code Analysis: Root Cause Diff

> **Commit:** [`{sha}`] — *{message}*  
> **Author:** `{author}` | **Primary File:** `{file_path}`

```diff
{problematic_diff.strip()}
```
{annotations_md}

#### <img src="https://api.iconify.design/lucide:shield-check.svg?color=%2310b981" width="18"/> Preventative Remediation Patch

```diff
{remediation_diff.strip()}
```
"""
    return md
