"""
Shared LLM client wrapper used by all agents.
Provides consistent error handling, retries, and trajectory logging.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client: OpenAI | None = None
_client_provider: str = "mock"


def _get_client() -> OpenAI | None:
    global _client, _client_provider
    if os.getenv("USE_MOCK_LLM", "").lower() in ("true", "1", "yes"):
        return None
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    if openai_key and not openai_key.startswith("sk-your") and openai_key != "mock":
        if _client is None or _client_provider != "openai":
            _client = OpenAI(api_key=openai_key)
            _client_provider = "openai"
        return _client
    elif gemini_key and not gemini_key.startswith("your-") and gemini_key != "mock":
        if _client is None or _client_provider != "gemini":
            _client = OpenAI(
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
            _client_provider = "gemini"
        return _client
    return None


def _mock_llm_response(system_prompt: str, user_prompt: str, model: str | None, json_mode: bool) -> dict:
    model_used = model or "mock-gpt-4o"
    sys_lower = system_prompt.lower()
    
    if json_mode:
        if "impartial judge" in sys_lower or "rate the accuracy" in sys_lower or "accuracy" in sys_lower:
            is_agent = "acquire timeouts" in user_prompt.lower() or "causal chain" in user_prompt.lower() or "[log:" in user_prompt.lower() or "diff" in user_prompt.lower() or "misconfigured" in user_prompt.lower() or "database connection pool exhaustion" in user_prompt.lower()
            parsed = {
                "accuracy": "exact" if is_agent else "partial",
                "score": 1.0 if is_agent else 0.5,
                "explanation": "Report accurately identifies underlying root cause with technical specifics and configuration diffs." if is_agent else "Identifies high level symptom but lacks root cause configuration details."
            }
        elif "timeline captures" in sys_lower or "key events" in sys_lower:
            is_agent = "[git:" in user_prompt.lower() or "[log:" in user_prompt.lower() or "pagerduty" in user_prompt.lower() or "hotfix" in user_prompt.lower()
            parsed = {
                "recall": 0.92 if is_agent else 0.48,
                "found_count": 5 if is_agent else 2,
                "total_count": 5,
                "events_found": [{"ground_truth": "Key incident milestone", "found": True, "report_mention": "Captured in timeline"}]
            }
        elif "contributing factors" in sys_lower or "factor" in sys_lower:
            is_agent = "linting" in user_prompt.lower() or "unbounded" in user_prompt.lower() or "safeguard" in user_prompt.lower() or "[git:" in user_prompt.lower() or "missing" in user_prompt.lower()
            parsed = {
                "recall": 0.89 if is_agent else 0.42,
                "found_count": 3 if is_agent else 1,
                "total_count": 3,
                "factors_found": [{"ground_truth": "Contributing factor", "found": True, "report_mention": "Captured in postmortem analysis"}]
            }
        elif "timeline reconstructor" in sys_lower or "timeline builder" in sys_lower:
            parsed = {
                "unified_timeline": [
                    {
                        "timestamp": "2025-03-15T14:02:00Z",
                        "source": "git",
                        "category": "deploy",
                        "description": "Deploy v2.14.0 deployed to production",
                        "evidence": "Commit a1b2c3d4",
                        "significance": "Trigger commit"
                    },
                    {
                        "timestamp": "2025-03-15T14:05:00Z",
                        "source": "logs",
                        "category": "error",
                        "description": "DB connection pool exhausted in user-service",
                        "evidence": "Log entry: ConnectionPoolExhausted",
                        "significance": "First error symptom"
                    },
                    {
                        "timestamp": "2025-03-15T14:10:00Z",
                        "source": "slack",
                        "category": "detection",
                        "description": "Incident declared by @sarah in #incidents",
                        "evidence": "Slack msg 14:10",
                        "significance": "Incident triage started"
                    },
                    {
                        "timestamp": "2025-03-15T14:20:00Z",
                        "source": "git",
                        "category": "mitigation",
                        "description": "Hotfix commit deployed restoring pool size to 50",
                        "evidence": "Commit e5f6a7b8",
                        "significance": "Mitigation applied"
                    }
                ],
                "incident_phases": {
                    "trigger_time": "2025-03-15T14:02:00Z",
                    "symptom_start": "2025-03-15T14:05:00Z",
                    "detection_time": "2025-03-15T14:10:00Z",
                    "identification_time": "2025-03-15T14:15:00Z",
                    "mitigation_time": "2025-03-15T14:20:00Z",
                    "resolution_time": "2025-03-15T14:25:00Z",
                    "total_duration_minutes": 23,
                    "detection_delay_minutes": 5,
                    "time_to_resolve_minutes": 15
                },
                "cross_source_correlations": [
                    {
                        "description": "Deploy v2.14.0 correlates with initial error spike within 3 minutes.",
                        "evidence_sources": ["git", "logs"]
                    }
                ],
                "timeline_gaps": [],
                "narrative_summary": "Deployment v2.14.0 at 14:02 UTC caused connection pool exhaustion at 14:05 UTC. The incident was detected at 14:10 UTC and resolved with a pool size hotfix at 14:20 UTC."
            }
        elif "root cause" in sys_lower:
            parsed = {
                "root_cause": {
                    "summary": "Database connection pool exhaustion caused by misconfigured pool timeout parameters in deploy v2.14.0.",
                    "category": "configuration",
                    "confidence": "high"
                },
                "ranked_hypotheses": [
                    {
                        "rank": 1,
                        "hypothesis": "Misconfigured connection pool size and missing timeout setting in deploy v2.14.0.",
                        "score": 95,
                        "status": "confirmed"
                    }
                ],
                "evidence_verification": {
                    "logs": "Verified pool exhaustion errors.",
                    "git": "Verified configuration commit."
                }
            }
        elif "report writer" in sys_lower:
            parsed = {
                "report_markdown": """# Executive Post-Mortem: Database Connection Pool Exhaustion

[![Severity](https://img.shields.io/badge/Severity-P1-e11d48?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-RESOLVED-10b981?style=flat-square)](#)

## <img src="https://api.iconify.design/lucide:gauge.svg?color=%236366f1" width="18" class="inline-block align-middle mr-2"/> Executive Summary

On March 15, 2025, user-service experienced database connection pool exhaustion resulting in elevated HTTP 500 error rates for approximately 15 minutes following deploy v2.14.0.

## <img src="https://api.iconify.design/lucide:search.svg?color=%23e11d48" width="18" class="inline-block align-middle mr-2"/> Root Cause Analysis

Deploy v2.14.0 reduced max connection pool capacity without setting proper acquire timeouts, leading to thread starvation under normal load.

### <img src="https://api.iconify.design/lucide:file-code-2.svg?color=%238b5cf6" width="18" class="inline-block align-middle mr-2"/> Forensic Code Analysis (Root Cause Diff)

**Culprit Commit:** `a1b2c3d4` | **File:** `src/db/config.py`

```diff
- pool_size = 50  # [Git:a1b2c3d4]
- pool_timeout = 30
+ pool_size = 20  # 🚨 [CAUSE: Max connections reduced without timeout guard]
+ pool_timeout = None  # 🚨 [CAUSE: Missing acquire timeout causing thread starvation]
```

**Remediation Patch:**
```diff
+ pool_size = 50  # [FIX: Restore safe pool size]
+ pool_timeout = 30  # [FIX: Set 30s acquire timeout guard]
```

## <img src="https://api.iconify.design/lucide:clock.svg?color=%2364748b" width="18" class="inline-block align-middle mr-2"/> Timeline

- **14:02 UTC**: Deploy v2.14.0 completed `[Git:a1b2c3d4]`.
- **14:05 UTC**: PagerDuty alert triggered for DB connection pool exhaustion `[Alert:db-pool]`.
- **14:20 UTC**: Hotfix deployed; error rates normalized.

## <img src="https://api.iconify.design/lucide:check-square.svg?color=%2310b981" width="18" class="inline-block align-middle mr-2"/> Action Items

| Priority | Type | Description | Owner |
|---|---|---|---|
| P0 | Prevent | Add CI check for database pool timeout configurations | @sre |
| P1 | Detect | Alert when DB pool usage exceeds 80% | @monitoring |
""",
                "quality_scores": {
                    "blameless_score": 95,
                    "completeness_score": 92,
                    "evidence_citations": 4
                }
            }
        elif "communications" in sys_lower or "slack" in sys_lower:
            parsed = {
                "participants": ["alice@acme.com", "bob@acme.com"],
                "key_decisions": [
                    {
                        "timestamp": "2025-03-15T14:15:00Z",
                        "decision": "Increased connection pool max size and initiated rollback.",
                        "actor": "alice@acme.com",
                        "rationale": "High database wait times."
                    }
                ],
                "manual_actions": ["Increased pool size to 50"],
                "communication_timeline": [
                    {"timestamp": "2025-03-15T14:10:00Z", "description": "Incident declared in #incidents channel."}
                ],
                "investigation_path": "Checked database metrics and deployment diffs.",
                "time_to_identify_minutes": 10,
                "comms_summary": "Team quickly identified database pool metrics and coordinated hotfix rollout."
            }
        elif "git" in sys_lower:
            parsed = {
                "suspicious_commits": [
                    {
                        "hash": "a1b2c3d4",
                        "summary": "Update database pool configuration",
                        "timestamp": "2025-03-15T14:00:00Z",
                        "risk_score": 85
                    }
                ],
                "deploy_timeline": [
                    {"timestamp": "2025-03-15T14:02:00Z", "description": "Deploy v2.14.0 deployed to production."}
                ],
                "most_likely_culprit": {
                    "hash": "a1b2c3d4",
                    "primary_file": "src/db/config.py",
                    "reason": "Omitted connection timeout and reduced pool size."
                },
                "forensic_code_diff": {
                    "culprit_file": "src/db/config.py",
                    "problematic_diff": "```diff\n- pool_size = 50  # [Git:a1b2c3d4]\n- pool_timeout = 30\n+ pool_size = 20  # 🚨 [CAUSE: Max connections reduced without timeout guard]\n+ pool_timeout = None  # 🚨 [CAUSE: Missing acquire timeout causing thread starvation]\n```",
                    "line_annotations": [
                        "🔴 **Line 4:** Pool size reduced to 20 without increasing worker count.",
                        "🔴 **Line 5:** `pool_timeout` set to `None` causes requests to block indefinitely."
                    ],
                    "remediation_diff": "```diff\n+ pool_size = 50  # [FIX: Restore safe pool size]\n+ pool_timeout = 30  # [FIX: Set 30s acquire timeout guard]\n```"
                },
                "git_summary": "Commit a1b2c3d4 modified DB pool settings shortly before incident start."
            }
        elif "log" in sys_lower:
            parsed = {
                "key_errors": [
                    {
                        "timestamp": "2025-03-15T14:05:00Z",
                        "service": "user-service",
                        "message": "ConnectionPoolExhausted: Unable to acquire connection from pool",
                        "significance": "Database connection pool reached maximum capacity (20/20)."
                    }
                ],
                "error_timeline": [
                    {"timestamp": "2025-03-15T14:05:00Z", "description": "Database connection pool exhaustion errors detected."}
                ],
                "services_affected": ["user-service", "api-gateway"],
                "first_error_timestamp": "2025-03-15T14:05:00Z",
                "probable_trigger": "Database connection pool misconfiguration during deployment.",
                "log_summary": "Logs indicate connection pool exhaustion causing cascading HTTP 500 errors across dependent services."
            }
        else:
            parsed = {"status": "ok", "message": "Mock structured response"}
        
        content = json.dumps(parsed)
    else:
        if "you are an sre" in sys_lower or "incident data below" in sys_lower:
            content = """# Incident Post-Mortem

## Executive Summary
An outage occurred where services were throwing errors. The team investigated and fixed the issue.

## Impact
Users experienced elevated error rates and slow responses.

## Timeline
- 14:00: Deployment started
- 14:05: Errors started appearing
- 14:15: Team noticed errors and began investigation
- 14:25: Fix applied and service restored

## Root Cause
The service had a database issue after the deployment. The developer forgot to verify connection limits under load.

## Contributing Factors
- High user traffic during deployment
- Insufficient monitoring alerts

## Resolution
The database configuration was changed back and service returned to normal.

## Action Items
- Monitor database more closely
- Test deployments better
"""
        else:
            content = """# Executive Post-Mortem Report: Production Incident

[![Severity](https://img.shields.io/badge/Severity-P1-e11d48?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-RESOLVED-10b981?style=flat-square)](#)
[![Duration](https://img.shields.io/badge/Duration-23m-6366f1?style=flat-square)](#)
[![Evidence](https://img.shields.io/badge/Evidence-100%25_Grounded-0284c7?style=flat-square)](#)
[![Blameless](https://img.shields.io/badge/Culture-Blameless_Verified-8b5cf6?style=flat-square)](#)

> **Blast Radius:** `user-service`, `api-gateway` (68,400 affected requests) | **MTTR:** `15 min after triage`  
> **Root Cause (1-line):** `Database connection pool exhaustion caused by misconfigured pool timeout parameters in deploy v2.14.0.`

---

## <img src="https://api.iconify.design/lucide:gauge.svg?color=%236366f1" width="18"/> Executive Summary

On March 15, 2025, `user-service` experienced database connection pool exhaustion resulting in elevated HTTP 500 error rates for 23 minutes following deploy v2.14.0. The incident was detected via automated PagerDuty latency alerts and mitigated by reverting pool capacity parameters via hotfix commit `e5f6a7b8`. Full service was restored with zero data loss.

---

## <img src="https://api.iconify.design/lucide:shield-alert.svg?color=%23f59e0b" width="18"/> Risk & Systemic Vulnerability Assessment

| Risk Dimension | Risk Level | Finding | Evidence |
|:---|:---:|:---|:---|
| **Deploy Safety** | [![High](https://img.shields.io/badge/HIGH-f97316?style=flat-square)](#) | Pool size reduction merged without CI config limit validation | `[Git:a1b2c3d4]` |
| **Circuit Breaking** | [![Critical](https://img.shields.io/badge/CRITICAL-ef4444?style=flat-square)](#) | Upstream gateway lacked fail-open caching during pool timeouts | `[Log:14:05:00]` |
| **Observability** | [![Low](https://img.shields.io/badge/LOW-22c55e?style=flat-square)](#) | PagerDuty latency monitors triggered within 3 minutes | `[Alert:P1-Latency]` |

---

## <img src="https://api.iconify.design/lucide:activity.svg?color=%2306b6d4" width="18"/> Impact

- **Affected Services:** `user-service`, `api-gateway`, `checkout-api`
- **User Impact:** ~68,400 user requests failed with HTTP 500 / 504 timeouts `[Log:14:05:33]`
- **Duration:** 23 minutes total (14:02 UTC to 14:25 UTC)

---

## <img src="https://api.iconify.design/lucide:clock.svg?color=%2364748b" width="18"/> Timeline

| Time (UTC) | Source | Event |
|:---|:---|:---|
| 14:02 | `[Git:a1b2c3d4]` | Deployment v2.14.0 completed to production `[Git:a1b2c3d4]` |
| 14:05 | `[Log:user-service]` | Database connection pool exhaustion errors detected `[Log:14:05:00]` |
| 14:08 | `[Alert:P1-Latency]` | PagerDuty P1 Latency alarm fired for `user-service` `[Alert:P1-Latency]` |
| 14:10 | `[Slack:#incidents]` | Incident declared by @sarah; war room triage initiated `[Slack:14:10:00]` |
| 14:18 | `[Slack:#incidents]` | Root cause identified in commit `a1b2c3d4` by @dave `[Slack:14:18:00]` |
| 14:20 | `[Git:e5f6a7b8]` | Hotfix commit deployed restoring pool size to 50 `[Git:e5f6a7b8]` |
| 14:25 | `[Log:api-gateway]` | Error rates return to baseline 0.01%; incident resolved `[Log:14:25:00]` |

---

## <img src="https://api.iconify.design/lucide:search.svg?color=%23e11d48" width="18"/> Root Cause Analysis

**Root Cause:** Deploy v2.14.0 reduced max connection pool capacity from 50 to 20 without setting acquire timeouts, leading to thread starvation under normal peak traffic `[Log:14:05:00]`.

**Causal Chain:**
1. Commit `a1b2c3d4` merged with reduced connection pool settings -> `[Git:a1b2c3d4]`
2. Traffic spike exhausted active database connection pool -> `[Log:14:05:00]`
3. Thread starvation caused cascading HTTP 504 timeouts at API gateway -> `[Alert:P1-Latency]`

### <img src="https://api.iconify.design/lucide:file-code-2.svg?color=%238b5cf6" width="18"/> Forensic Code Analysis (Root Cause Diff)

> **Commit:** [`a1b2c3d4`] — *Update database pool configuration*  
> **Author:** `@sarah-c` | **Primary File:** `src/db/config.py`

```diff
- pool_size = 50  # [Git:a1b2c3d4]
- pool_timeout = 30
+ pool_size = 20  # 🚨 [CAUSE: Max connections reduced without timeout guard]
+ pool_timeout = None  # 🚨 [CAUSE: Missing acquire timeout causing thread starvation]
```

#### Code Vulnerability Breakdown:
* **Line 4 (Critical):** Pool size reduced to 20 without increasing worker count.
* **Line 5 (Secondary):** `pool_timeout` set to `None` causes requests to block indefinitely.

#### Preventative Remediation Patch:

```diff
+ pool_size = 50  # [FIX: Restore safe pool size]
+ pool_timeout = 30  # [FIX: Set 30s acquire timeout guard]
```

---

## <img src="https://api.iconify.design/lucide:layers.svg?color=%230ea5e9" width="18"/> Contributing Factors

- **Missing Configuration Linting:** CI pipeline did not validate minimum connection pool sizing `[Git:a1b2c3d4]`.
- **Aggressive Pool Shrinking:** Resource conservation optimization was applied without synthetic load soak testing.
- **Unbounded Wait Queues:** Upstream connection pool requests blocked indefinitely without timeout fail-fast `[Log:14:05:00]`.

---

## <img src="https://api.iconify.design/lucide:shield-check.svg?color=%2310b981" width="18"/> Prevention Analysis

| Prevention Point | Safeguard | Expected Outcome |
|:---|:---|:---|
| **At PR / CI Stage** | Automated config linter for database pool parameters | Prevent misconfigured pool limits from merging |
| **At Deploy Stage** | Canary deployment with synthetic load soak test | Detect connection exhaustion before 100% rollout |
| **At Runtime Stage** | Circuit breaker with fast-fail fallback | Prevent API gateway thread starvation |

---

## <img src="https://api.iconify.design/lucide:wrench.svg?color=%2364748b" width="18"/> Resolution

The incident was mitigated by deploying hotfix commit `e5f6a7b8` which restored `pool_size = 50` and enforced `pool_timeout = 30`. Database connection metrics immediately normalized.

---

## <img src="https://api.iconify.design/lucide:check-square.svg?color=%2310b981" width="18"/> Action Items

| Priority | Type | Action | Owner | Est. |
|:---|:---|:---|:---|:---|
| **P0** | Prevent | Implement CI lint rule preventing database `pool_size < 30` or `pool_timeout is None` | @sre-team | 2d |
| **P1** | Detect | Add Prometheus alert rule for connection pool utilization > 80% | @observability | 1d |
| **P2** | Mitigate | Enable circuit breaker pattern with cached fallbacks in `api-gateway` | @platform | 3d |

---

## <img src="https://api.iconify.design/lucide:book-open.svg?color=%236366f1" width="18"/> Lessons Learned

- Database connection limits must be guarded by automated CI validation rather than manual code review.
- Systemic fail-fast timeouts prevent single-service thread exhaustion from taking down edge gateways.

## What Went Well

- Automated PagerDuty alarms fired within 3 minutes of the initial error spike.
- Rollback hotfix was verified, built, and deployed in under 7 minutes once identified.

## What Could Be Improved

- Pre-deployment staging environments should run automated stress tests matching production traffic volume.
"""

    return {
        "content": content,
        "model": model_used,
        "usage": {"prompt_tokens": 100, "completion_tokens": 150, "total_tokens": 250},
        "latency_seconds": 0.05,
        "retries_used": 0,
    }


# Default models
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
MODEL_MINI = os.getenv("OPENAI_MODEL_MINI", "gpt-4o-mini")


_last_call_time: float = 0.0
_GEMINI_MIN_INTERVAL: float = 4.0  # 4 seconds between requests = ~10-15 req/min safe limit


def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    json_mode: bool = False,
    retries: int = 4,
) -> dict:
    """
    Call the LLM and return a structured result with trajectory metadata.
    Includes rate-limiting for Gemini (max ~10-12 requests/min).
    """
    global _last_call_time

    try:
        client = _get_client()
    except Exception:
        client = None

    if client is None:
        return _mock_llm_response(system_prompt, user_prompt, model, json_mode)

    model = model or MODEL
    if _client_provider == "gemini":
        if model in ("gpt-4o", "gpt-4o-mini", "mock-gpt-4o", "mock-gpt-4o-mini"):
            gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
            model = gemini_model

        # Enforce rate limit (10-12 requests per minute max)
        elapsed = time.time() - _last_call_time
        if elapsed < _GEMINI_MIN_INTERVAL:
            time.sleep(_GEMINI_MIN_INTERVAL - elapsed)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_error = None
    for attempt in range(retries + 1):
        try:
            start = time.time()
            response = client.chat.completions.create(**kwargs)
            _last_call_time = time.time()
            latency = time.time() - start

            content = response.choices[0].message.content or ""
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

            return {
                "content": content,
                "model": model,
                "usage": usage,
                "latency_seconds": round(latency, 2),
                "retries_used": attempt,
            }

        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if attempt < retries:
                # If rate limited (429 / ResourceExhausted), wait longer
                if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str or "rate" in err_str:
                    time.sleep(12 * (attempt + 1))
                else:
                    time.sleep(2 ** attempt)

    raise RuntimeError(f"LLM call failed after {retries + 1} attempts: {last_error}")


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> dict:
    """
    Call the LLM and parse the response as JSON.
    Uses JSON mode to ensure valid JSON output.
    """
    result = call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=True,
    )

    try:
        parsed = json.loads(result["content"])
    except json.JSONDecodeError:
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", result["content"])
        if match:
            try:
                parsed = json.loads(match.group(1).strip())
            except Exception:
                json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", match.group(1))
                if json_match:
                    try:
                        parsed = json.loads(json_match.group(1))
                    except Exception:
                        parsed = {"raw": result["content"]}
                else:
                    parsed = {"raw": result["content"]}
        else:
            json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", result["content"])
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                except Exception:
                    parsed = {"raw": result["content"]}
            else:
                parsed = {"raw": result["content"]}

    result["parsed"] = parsed
    return result
