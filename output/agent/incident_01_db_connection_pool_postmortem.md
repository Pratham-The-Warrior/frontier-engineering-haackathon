# Executive Post-Mortem Report: Production Incident

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
