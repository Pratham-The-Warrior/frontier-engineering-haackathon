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


def _get_client() -> OpenAI | None:
    global _client
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-your") or api_key == "mock":
        return None
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client


def _mock_llm_response(system_prompt: str, user_prompt: str, model: str | None, json_mode: bool) -> dict:
    model_used = model or "mock-gpt-4o"
    sys_lower = system_prompt.lower()
    
    if json_mode:
        if "log" in sys_lower:
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
        elif "comms" in sys_lower or "communications" in sys_lower:
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
        elif "timeline" in sys_lower:
            parsed = {
                "unified_timeline": [
                    {
                        "timestamp": "2025-03-15T14:02:00Z",
                        "source": "git",
                        "category": "deploy",
                        "description": "Deploy v2.14.0 deployed",
                        "evidence": "Commit a1b2c3d4",
                        "significance": "Trigger commit"
                    },
                    {
                        "timestamp": "2025-03-15T14:05:00Z",
                        "source": "logs",
                        "category": "error",
                        "description": "DB connection pool exhausted",
                        "evidence": "Log line 42",
                        "significance": "First error"
                    }
                ],
                "incident_phases": {
                    "detection": "2025-03-15T14:05:00Z",
                    "mitigation": "2025-03-15T14:20:00Z"
                },
                "cross_source_correlations": ["Deploy correlates with initial error spike within 3 minutes."],
                "timeline_gaps": [],
                "narrative_summary": "Deployment at 14:02 was followed by connection pool exhaustion at 14:05 and resolution at 14:20."
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
        elif "report" in sys_lower:
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
        else:
            parsed = {"status": "ok", "message": "Mock structured response"}
        
        content = json.dumps(parsed)
    else:
        content = """# Executive Post-Mortem Report: Production Incident

[![Severity](https://img.shields.io/badge/Severity-P1-e11d48?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-RESOLVED-10b981?style=flat-square)](#)

## <img src="https://api.iconify.design/lucide:gauge.svg?color=%236366f1" width="18" class="inline-block align-middle mr-2"/> Executive Summary

The production service experienced a temporary degradation due to database connection pool exhaustion. The incident was detected automatically and resolved within 15 minutes.

## <img src="https://api.iconify.design/lucide:search.svg?color=%23e11d48" width="18" class="inline-block align-middle mr-2"/> Root Cause Analysis

Deployment of v2.14.0 introduced a misconfigured database connection pool size without setting proper connection acquire timeouts, leading to pool exhaustion under standard load.

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

- **14:00 UTC**: Deployment v2.14.0 initiated.
- **14:05 UTC**: PagerDuty alert fired for high HTTP 500 error rates.
- **14:15 UTC**: Hotfix deployed increasing connection pool limit.

## <img src="https://api.iconify.design/lucide:check-square.svg?color=%2310b981" width="18" class="inline-block align-middle mr-2"/> Action Items

| Priority | Type | Description | Owner |
|---|---|---|---|
| P0 | Prevent | Add automated CI test for database pool config limits | @sre |
| P1 | Detect | Configure alert threshold for connection pool usage > 80% | @monitoring |
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


def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    json_mode: bool = False,
    retries: int = 2,
) -> dict:
    """
    Call the LLM and return a structured result with trajectory metadata.
    """
    try:
        client = _get_client()
    except Exception:
        client = None

    if client is None:
        return _mock_llm_response(system_prompt, user_prompt, model, json_mode)

    model = model or MODEL


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
            if attempt < retries:
                time.sleep(2 ** attempt)  # exponential backoff

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
        # Fallback: try to extract JSON from markdown code block
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", result["content"])
        if match:
            parsed = json.loads(match.group(1))
        else:
            raise ValueError(f"LLM did not return valid JSON: {result['content'][:200]}")

    result["parsed"] = parsed
    return result
