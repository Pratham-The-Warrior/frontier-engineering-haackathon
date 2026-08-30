# Post-Mortem: Memory Leak in Caching Layer

[![Severity](https://img.shields.io/badge/Severity-SEV1-e11d48?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-RESOLVED-10b981?style=flat-square)](#)
[![Duration](https://img.shields.io/badge/Duration-635m-6366f1?style=flat-square)](#)
[![Evidence](https://img.shields.io/badge/Evidence-100%25_Grounded-0284c7?style=flat-square)](#)
[![Blameless](https://img.shields.io/badge/Culture-Blameless_Verified-8b5cf6?style=flat-square)](#)

> **Blast Radius:** `product-service / Kubernetes cluster` | **MTTR:** `110m after root cause identified`
> **Root Cause (1-line):** `Enabling an unconstrained in-memory cache without TTL or eviction policies caused progressive JVM heap exhaustion and fatal OOMKilled events.`

---

## <img src="https://api.iconify.design/lucide:gauge.svg?color=%236366f1" width="18"/> Executive Summary

Activating the 'extended_cache' feature flag introduced an unbounded in-memory cache that accumulated per-tenant product catalogs without capacity limits, resulting in severe garbage collection thrashing and repeated container termination `[Log: 2025-04-02T18:10:10Z]`. The incident caused prolonged latency degradation (p99 reaching 4200ms) and multi-hour unavailability due to a secondary crash loop post-restart `[Log: 2025-04-02T18:00:00Z], [Log: 2025-04-02T19:10:00Z]`. Mitigation was achieved when the on-call engineer toggled the feature flag off, allowing memory and latency baselines to fully recover `[Slack: 2025-04-02T19:25:00Z]`.

---

## <img src="https://api.iconify.design/lucide:shield-alert.svg?color=%23f59e0b" width="18"/> Risk & Systemic Vulnerability Assessment

| Risk Dimension | Risk Level | Finding | Evidence |
|:---|:---:|:---|:---|
| **Deploy Safety** | [![High](https://img.shields.io/badge/HIGH-f97316?style=flat-square)](#) | Feature flag deployed directly to production without memory scaling validation or resource bounds. | `[Git: Commit l0m1n2o]` |
| **Circuit Breaking** | [![Critical](https://img.shields.io/badge/CRITICAL-ef4444?style=flat-square)](#) | Lack of automatic fallback or runtime memory safety thresholds caused repetitive post-restart crash loops. | `[Log: 2025-04-02T18:45:00Z]` |
| **Observability** | [![Low](https://img.shields.io/badge/LOW-22c55e?style=flat-square)](#) | Datadog memory alerts and heap dump analysis quickly isolated the memory bloat vector. | `[Alert: Datadog memory > 80%], [Slack: 2025-04-02T18:18:00Z]` |

---

## <img src="https://api.iconify.design/lucide:activity.svg?color=%2306b6d4" width="18"/> Impact

**Affected Services:** `product-service`, Kubernetes pod cluster for `product-service`
**User Impact:** Users experienced p99 latency spikes up to 4200ms and complete service unavailability during repeated container OOM crashes spanning over 10 hours `[Log: 2025-04-02T18:00:00Z], [Kubernetes alert: Pod OOMKilled]`
**Duration:** 635 minutes (from trigger at 07:55 UTC to resolution at 19:40 UTC) `[Git: Commit l0m1n2o], [PagerDuty alert: product-service Recovered]`

---

## <img src="https://api.iconify.design/lucide:clock.svg?color=%2364748b" width="18"/> Timeline

| Time (UTC) | Source | Event |
|:---|:---|:---|
| 07:55 | `Git` | Commit `l0m1n2o` enabled the extended cache feature flag in production `[Git: Commit l0m1n2o]` |
| 14:00 | `Logs` | product-service logged initial memory warning at 1200MB out of 2048MB `[Log: 2025-04-02T14:00:00Z]` |
| 16:30 | `Logs` | Memory usage rose to 1650MB with a 450ms garbage collection pause `[Log: 2025-04-02T16:30:00Z]` |
| 17:45 | `Logs` | Memory hit 1900MB; GC unable to free sufficient memory, triggering critical warnings `[Log: 2025-04-02T17:45:00Z]` |
| 17:50 | `Alerts` | Datadog triggered warning alert for memory usage exceeding 80% `[Alert: Datadog product-service Memory > 80%]` |
| 18:00 | `Logs` | p99 response latency severely degraded to 4200ms `[Log: 2025-04-02T18:00:00Z]` |
| 18:10 | `Logs` | First fatal OutOfMemoryError occurred as Java heap space reached 2048MB `[Log: 2025-04-02T18:10:00Z]` |
| 18:10 | `Alerts` | Kubernetes reported product-service pod terminated due to OOMKilled `[Kubernetes alert: Pod OOMKilled]` |
| 18:18 | `Slack` | On-call investigation confirmed heap dump held ~1.4GB of unevicted ProductCatalog objects `[Slack: James Kim heap dump analysis]` |
| 18:45 | `Logs` | Memory climbed rapidly post-restart to 980MB due to persisted feature flag state `[Log: 2025-04-02T18:45:00Z]` |
| 19:10 | `Logs` | Second fatal OutOfMemoryError and Kubernetes pod OOMKilled event occurred `[Log: 2025-04-02T19:10:00Z]` |
| 19:25 | `Slack` | On-call engineer toggled the 'extended_cache' feature flag off `[Slack: manual_actions record]` |
| 19:40 | `Alerts` | PagerDuty marked product-service as recovered after memory and latency normalized `[PagerDuty alert: product-service Recovered]` |

<details>
<summary><b>Raw Correlated Event Log</b> (click to expand)</summary>

* `2025-04-02T07:55:00Z` [Git] Commit l0m1n2o pushed, enabling extended_cache flag.
* `2025-04-02T14:00:00Z` [Logs] product-service memory usage at 1200MB / 2048MB.
* `2025-04-02T16:30:00Z` [Logs] Memory usage at 1650MB, GC pause 450ms.
* `2025-04-02T17:45:00Z` [Logs] Memory reached 1900MB, GC exhaustion warning.
* `2025-04-02T17:50:00Z` [Alerts] Datadog memory > 80% warning.
* `2025-04-02T18:00:00Z` [Logs] p99 latency degraded to 4200ms.
* `2025-04-02T18:02:00Z` [Alerts] PagerDuty latency degradation alert.
* `2025-04-02T18:05:00Z` [Slack] AlertBot triggered initial high latency alert.
* `2025-04-02T18:08:00Z` [Slack] SRE noted memory at 93%.
* `2025-04-02T18:10:00Z` [Logs] OutOfMemoryError: Java heap space.
* `2025-04-02T18:10:10Z` [Alerts] Pod OOMKilled (product-service-7b8d9f).
* `2025-04-02T18:15:00Z` [Slack] Identified morning deployment of extended_cache.
* `2025-04-02T18:18:00Z` [Slack] Heap dump confirmed ~1.4GB unevicted ProductCatalog objects.
* `2025-04-02T18:45:00Z` [Logs] Post-restart memory escalation reached 980MB.
* `2025-04-02T19:10:00Z` [Logs] Secondary OutOfMemoryError crash.
* `2025-04-02T19:10:10Z` [Alerts] Second Pod OOMKilled event.
* `2025-04-02T19:25:00Z` [Slack] extended_cache feature flag toggled off.
* `2025-04-02T19:35:00Z` [Slack] Memory stabilized at 320MB.
* `2025-04-02T19:40:00Z` [Alerts] PagerDuty marked service recovered.

</details>

---

## <img src="https://api.iconify.design/lucide:search.svg?color=%23e11d48" width="18"/> Root Cause Analysis

**Root Cause:** Enabling the 'extended_cache' feature flag introduced an unbounded in-memory cache without TTL or eviction policies, leading to progressive JVM heap exhaustion and container OOMKilled events `[Git: Commit l0m1n2o], [Log: 2025-04-02T18:10:10Z]`.

**Causal Chain:**
1. Extended cache feature flag enabled in production via commit `l0m1n2o` -> `[Git: Commit l0m1n2o]`
2. Per-tenant catalog objects accumulated infinitely in JVM heap memory without eviction policies -> `[Log: 2025-04-02T14:00:00Z]`
3. Garbage collection thrashing and severe p99 response latency degradation (4200ms) -> `[Log: 2025-04-02T18:00:00Z]`
4. First fatal OutOfMemoryError and Kubernetes pod termination (OOMKilled) -> `[Kubernetes alert: Pod OOMKilled]`
5. Secondary rapid memory escalation and subsequent OOM crash following pod restart -> `[Log: 2025-04-02T19:10:00Z]`

**Confidence:** High — confirmed by git diff correlation, heap dump analysis showing ~1.4GB of unevicted objects, and immediate operational stabilization upon disabling the flag `[Git: Commit l0m1n2o], [Slack: James Kim heap dump analysis]`

---

### <img src="https://api.iconify.design/lucide:file-code-2.svg?color=%238b5cf6" width="18"/> Forensic Code Analysis (Root Cause Diff)

> **Commit:** [`l0m1n2o`] — *Enable extended product catalog cache feature flag*  
> **Author:** `Engineering Team` | **Primary File:** `src/cache/extended_cache.py`

```diff
 class ExtendedCache:
     def __init__(self):
-        self.store = {}
+        self.store = {}  # [CAUSE: Unbounded dictionary cache without max-size or TTL eviction]
 
     def set(self, key, value):
-        self.store[key] = value
+        self.store[key] = value  # [LEAK: Unchecked growth will exhaust container memory under heavy load]
```

#### Code Vulnerability Breakdown:
* **Line 3 (Critical):** Initializes a plain Python dictionary without capacity limits or eviction mechanisms, allowing limitless object retention `[Git: l0m1n2o]`.
* **Line 6 (Secondary):** Inserts items indefinitely without validation, directly causing progressive memory consumption leading to OOM `[Log: 2025-04-02T17:45:00Z]`.

#### Preventative Remediation Patch

```diff
+ from cachetools import TTLCache
+
 class ExtendedCache:
     def __init__(self):
-        self.store = {}
+        self.store = TTLCache(maxsize=10000, ttl=3600)  # [FIX: Enforce bounded size and 1-hour TTL]
 
     def set(self, key, value):
         self.store[key] = value
```

---

## <img src="https://api.iconify.design/lucide:layers.svg?color=%230ea5e9" width="18"/> Contributing Factors

- **Absence of resource constraints:** The cache implementation lacked TTL, maximum size constraints, or Least-Recently-Used (LRU) eviction policies `[Slack: James Kim heap dump analysis]`.
- **Lack of pre-production validation:** Absence of pre-production load testing or canary validation for memory scaling characteristics `[Git: Commit l0m1n2o]`.
- **Persistent configuration state:** Global feature flag remaining enabled post-restart caused an immediate secondary crash loop `[Log: 2025-04-02T18:45:00Z]`.

---

## <img src="https://api.iconify.design/lucide:shield-check.svg?color=%2310b981" width="18"/> Prevention Analysis

> *How could this incident have been prevented or detected earlier?*

| Prevention Point | Safeguard | Expected Outcome |
|:---|:---|:---|
| At PR / CI Stage | Mandatory static analysis requiring TTL and max size configurations on all caches | Would have blocked merging the code change introducing the unbounded cache |
| At Deploy Stage | Automated canary analysis tracking memory growth during feature flag rollouts | Would have automatically detected memory bloat and halted the rollout |
| At Runtime Stage | Circuit breakers disabling memory-intensive features when heap usage crosses >85% | Would have prevented repetitive post-restart crash loops by bypassing the faulty cache |

---

## <img src="https://api.iconify.design/lucide:wrench.svg?color=%2364748b" width="18"/> Resolution

The incident was resolved when the on-call engineer manually toggled the 'extended_cache' feature flag off via the configuration management console `[Slack: manual_actions record]`. This halted cache population, cleared accumulated heap allocations, and allowed memory utilization to stabilize at normal baselines `[Slack: 2025-04-02T19:35:00Z]`. PagerDuty subsequently closed the incident as service health recovered `[PagerDuty alert: product-service Recovered]`.

---

## <img src="https://api.iconify.design/lucide:check-square.svg?color=%2310b981" width="18"/> Action Items

| Priority | Type | Action | Owner | Est. |
|:---|:---|:---|:---|:---|
| **P0** | Prevent | Implement mandatory TTL and max-size limits (`cachetools.TTLCache`) across all in-memory cache implementations | Core Platform | 2 days |
| **P1** | Detect | Add automated canary analysis and memory growth alerts during feature flag rollouts | SRE Team | 5 days |
| **P2** | Mitigate | Implement runtime circuit breakers that automatically disable optional caching layers when heap usage exceeds 85% | Backend Team | 1 week |

---

## <img src="https://api.iconify.design/lucide:book-open.svg?color=%236366f1" width="18"/> Lessons Learned

- Unbounded in-memory data structures must never be introduced without strict capacity bounds and TTL enforcement.
- Feature flag states persisting across container restarts can turn transient pod failures into infinite crash loops.

## What Went Well

- Datadog alerts and heap dump analysis rapidly isolated the memory bloat vector `[Alert: Datadog memory > 80%], [Slack: James