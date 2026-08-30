# Post-Mortem: Kubernetes Pod CrashLoopBackOff From Misconfigured Liveness Probe

[![Severity](https://img.shields.io/badge/Severity-SEV1-e11d48?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-RESOLVED-10b981?style=flat-square)](#)
[![Duration](https://img.shields.io/badge/Duration-46.5m-6366f1?style=flat-square)](#)
[![Evidence](https://img.shields.io/badge/Evidence-100%25_Grounded-0284c7?style=flat-square)](#)
[![Blameless](https://img.shields.io/badge/Culture-Blameless_Verified-8b5cf6?style=flat-square)](#)

> **Blast Radius:** `100% of end-users (Authentication & Login)` | **MTTR:** `43.5 min`
> **Root Cause (1-line):** `A liveness probe performing uninitialized deep database checks without a startup delay triggered continuous pod reboots and a persistent CrashLoopBackOff state.`

---

## <img src="https://api.iconify.design/lucide:gauge.svg?color=%236366f1" width="18"/> Executive Summary

A newly deployed Kubernetes manifest introduced a deep database connectivity health check directly into the application's liveness probe without configuring an initial delay `[Git:k8s001]`. Because the database connection pool could not initialize within the strict liveness check window, Kubernetes repeatedly terminated and restarted the pods, forcing the `auth-service` into an unrecoverable `CrashLoopBackOff` state `[Log:2025-09-01T14:04:00Z]`. This total infrastructure failure severed internal routing from the API gateway, causing a 46.5-minute platform-wide authentication outage for all end-users `[PagerDuty:2025-09-01T14:04:30Z]`.

---

## <img src="https://api.iconify.design/lucide:shield-alert.svg?color=%23f59e0b" width="18"/> Risk & Systemic Vulnerability Assessment

| Risk Dimension | Risk Level | Finding | Evidence |
|:---|:---:|:---|:---|
| **Deploy Safety** | [![High](https://img.shields.io/badge/HIGH-f97316?style=flat-square)](#) | Absence of CI/CD linters or OPA admission controllers to catch unsafe liveness configurations. | `[Git:k8s001]` |
| **Circuit Breaking** | [![Critical](https://img.shields.io/badge/CRITICAL-ef4444?style=flat-square)](#) | Conflation of container lifecycle management with external dependency checks in liveness probes. | `[Git:k8s001], [Log:2025-09-01T14:02:35Z]` |
| **Observability** | [![Low](https://img.shields.io/badge/LOW-22c55e?style=flat-square)](#) | Automated PagerDuty alerts successfully flagged infrastructure failure and user impact within minutes. | `[Alert:2025-09-01T14:03:00Z]` |

---

## <img src="https://api.iconify.design/lucide:activity.svg?color=%2306b6d4" width="18"/> Impact

**Affected Services:** `auth-service`, `api-gateway`, user authentication and login flow `[PagerDuty:2025-09-01T14:04:30Z]`
**User Impact:** 100% of end-users experienced total authentication failure, preventing logins and session validation across the platform `[PagerDuty:2025-09-01T14:04:30Z]`
**Duration:** 46.5 minutes (from initial trigger at 13:30:00Z to complete recovery at 14:16:30Z) `[Git:k8s001], [PagerDuty:2025-09-01T14:16:30Z]`

---

## <img src="https://api.iconify.design/lucide:clock.svg?color=%2364748b" width="18"/> Timeline

| Time (UTC) | Source | Event |
|:---|:---|:---|
| 13:30:00 | `Git` | Commit k8s001 pushed deploying `/healthz` DB check directly as a liveness probe without startup delay. `[Git:k8s001]` |
| 14:02:35 | `Logs` | Auth-service liveness probe failed as database connection pool was not yet ready during startup. `[Log:2025-09-01T14:02:35Z]` |
| 14:02:50 | `Logs` | Kubernetes restarted auth-service pod after 3 consecutive failed liveness probes. `[Log:2025-09-01T14:02:50Z]` |
| 14:03:00 | `Alerts` | AlertBot triggered critical alert reporting auth-service in `CrashLoopBackOff`. `[Alert:2025-09-01T14:03:00Z]` |
| 14:04:00 | `Logs` | Kubernetes placed all auth-service replicas into a persistent `CrashLoopBackOff` state. `[Log:2025-09-01T14:04:00Z]` |
| 14:04:30 | `Alerts` | PagerDuty triggered critical alert for 'Authentication Unavailable' (zero healthy pods). `[PagerDuty:2025-09-01T14:04:30Z]` |
| 14:05:00 | `Slack` | On-call engineer acknowledged outage and began reviewing recent deployments. `[Slack:14:05:00]` |
| 14:06:00 | `Slack` | On-call engineer identified faulty liveness probe configuration in recent deployment. `[Slack:14:06:00]` |
| 14:08:00 | `Slack` | Configuration fix applied: added initial delay and moved DB check to readiness probe. `[Slack:14:08:00]` |
| 14:16:00 | `Slack` | Verification confirmed pods are stable and authentication traffic is fully recovered. `[Slack:14:16:00]` |
| 14:16:30 | `Alerts` | PagerDuty automatically resolved 'Authentication Unavailable' incident. `[PagerDuty:2025-09-01T14:16:30Z]` |

<details>
<summary><b>Raw Correlated Event Log</b> (click to expand)</summary>

```text
[2025-09-01T13:30:00Z] [Git] Commit k8s001: feat: add /healthz endpoint with DB connectivity check
[2025-09-01T14:02:35Z] [Log] Kubernetes log: Liveness probe failed: /healthz returned 503 (DB connection not ready)
[2025-09-01T14:02:50Z] [Log] Kubernetes log: Liveness probe failed 3 times — restarting pod
[2025-09-01T14:03:00Z] [Alert] AlertBot: CrashLoopBackOff detected for auth-service
[2025-09-01T14:03:10Z] [Log] Kubernetes log: Pod restarted. Liveness probe failing again during startup.
[2025-09-01T14:04:00Z] [Log] Kubernetes log: CrashLoopBackOff: auth-service-5f8d2a
[2025-09-01T14:04:30Z] [Alert] PagerDuty: Authentication Unavailable - No healthy auth-service pods
[2025-09-01T14:05:00Z] [Slack] On-call acknowledged outage and initiated deployment triage.
[2025-09-01T14:06:00Z] [Slack] Root cause isolated to missing initialDelaySeconds in v4.1.0 liveness probe.
[2025-09-01T14:07:00Z] [Slack] Peer confirmation achieved on migrating check to readiness probe.
[2025-09-01T14:08:00Z] [Slack] Remediation applied via deployment update.
[2025-09-01T14:16:00Z] [Slack] Pods stabilized; authentication flow verified healthy.
[2025-09-01T14:16:30Z] [Alert] PagerDuty resolved: auth-service recovered.
```

</details>

---

## <img src="https://api.iconify.design/lucide:search.svg?color=%23e11d48" width="18"/> Root Cause Analysis

**Root Cause:** A misconfigured Kubernetes liveness probe tied directly to an uninitialized deep database connectivity check without an initial startup delay caused repeated container restarts and an unrecoverable `CrashLoopBackOff` state `[Git:k8s001], [Log:2025-09-01T14:02:35Z]`.

**Causal Chain:**
1. Commit k8s001 pushed a new `/healthz` endpoint checking database connectivity directly as a liveness probe with zero initial delay -> `[Git:k8s001]`
2. Auth-service containers started up, but database connection pools were not yet established within the strict liveness probe window -> `[Log:2025-09-01T14:02:35Z]`
3. Kubernetes destroyed the containers after 3 consecutive failures, trapping all replicas in an infinite `CrashLoopBackOff` loop -> `[Log:2025-09-01T14:04:00Z]`
4. API gateway reported zero healthy auth-service pods, resulting in complete authentication unavailability for all users -> `[PagerDuty:2025-09-01T14:04:30Z]`

**Confidence:** High. Direct evidence from git diff matches the exact misconfiguration, corroborated by container logs and automated alert telemetry.

---

### <img src="https://api.iconify.design/lucide:file-code-2.svg?color=%238b5cf6" width="18"/> Forensic Code Analysis (Root Cause Diff)

> **Commit:** [`k8s001`] — *feat: add /healthz endpoint with DB connectivity check*  
> **Author:** `Engineering Team` | **Primary File:** `k8s/deployment.yaml`

```diff
 spec:
   containers:
   - name: app
     image: my-app:latest
     livenessProbe:
       httpGet:
         path: /healthz
         port: 8080
-      # 🚨 ROOT CAUSE: No initialDelaySeconds causes premature container kills during DB bootstrap
+      # 🚨 ROOT CAUSE: Liveness probe checks DB connection immediately with zero delay
+      initialDelaySeconds: 0
+      periodSeconds: 5
```

#### Code Vulnerability Breakdown:
* **Line 7 (Critical):** Liveness probe executes a heavy database connectivity check immediately upon container start before the connection pool is established `[Git:k8s001]`.
* **Line 9 (Secondary):** Zero `initialDelaySeconds` guarantees an immediate restart loop if dependency initialization exceeds the default probe timeout `[Git:k8s001], [Log:2025-09-01T14:02:35Z]`.

#### Preventative Remediation Patch

```diff
 spec:
   containers:
   - name: app
     image: my-app:latest
     readinessProbe:
       httpGet:
         path: /ready
         port: 8080
       initialDelaySeconds: 5
       periodSeconds: 10
     livenessProbe:
       httpGet:
         path: /healthz
         port: 8080
       initialDelaySeconds: 30
       periodSeconds: 15
```

---

## <img src="https://api.iconify.design/lucide:layers.svg?color=%230ea5e9" width="18"/> Contributing Factors

- **Conflation of Probe Semantics:** Using a container-destroying liveness check for transient external dependencies rather than traffic-isolating readiness checks `[Git:k8s001], [Log:2025-09-01T14:02:35Z]`.
- **Testing & Validation Gap:** Absence of CI/CD policy gates and staging environment validation capable of catching startup dependency failures prior to production rollout `[Git:k8s001]`.

---

## <img src="https://api.iconify.design/lucide:shield-check.svg?color=%2310b981" width="18"/> Prevention Analysis

> *How could this incident have been prevented or detected earlier?*

| Prevention Point | Safeguard | Expected Outcome |
|:---|:---|:---|
| At PR / CI Stage | Implement OPA admission controllers or static linters (e.g., `kubeconform`) enforcing mandatory `initialDelaySeconds`. | Would have blocked the pull request or manifest deployment before merge. |
| At Deploy Stage | Execute automated canary deployments with pre-flight rollout checks mirroring dependency startup times. | Would have caught the `CrashLoopBackOff` during canary analysis and auto-rolled back. |
| At Runtime Stage | Separate container lifecycle management (liveness) from dependency health (readiness), utilizing startup probes. | Would isolate transient startup delays from triggering destructive container reboots. |

---

## <img src="https://api.iconify.design/lucide:wrench.svg?color=%2364748b" width="18"/> Resolution

The incident was resolved when the on-call engineer identified the configuration error in `k8s/deployment.yaml` `[Slack:14:06:00]`. The remediation patch separated the health checks by moving the deep database verification to a readiness probe, establishing a dedicated 30-second initial delay for the liveness probe, and updating the deployment manifest `[Slack:14:08:00]`. Pods successfully initialized their connection pools, stabilized, and fully restored authentication traffic `[Slack:14:16:00]`.

---

## <img src="https://api.iconify.design/lucide:check-square.svg?color=%2310b981" width="18"/> Action Items

| Priority | Type | Action | Owner | Est. |
|:---|:---|:---|:---|:---|
| **P0** | Prevent | Implement OPA Gatekeeper policies to require `initialDelaySeconds` and prohibit deep dependency checks in liveness probes. | Platform Engineering | 3 days |
| **P1** | Detect | Add automated staging soak tests and canary rollout analysis gates to catch startup failures pre-production. | Release Engineering | 5 days |
| **P2** | Mitigate | Update Kubernetes deployment templates across all microservices to adhere to best-practice probe separation. | Core Architecture Team | 10 days |

---

## <img src="https://api.iconify.design/lucide:book-open.svg?color=%236366f1" width="18"/> Lessons Learned

- Liveness probes must test internal process health only; external dependencies like databases belong exclusively in readiness or startup probes.
- Automated static analysis and policy guardrails are mandatory for Kubernetes manifests to prevent destructive probe configurations from reaching production.

## What Went Well

- Automated PagerDuty and AlertBot monitoring rapidly detected the infrastructure failure and user impact within minutes `[Alert:2025-09-01T14:03:00Z]`.
- On-call triage was efficient, allowing rapid root cause identification and mitigation patch deployment.

## What Could Be Improved

- Staging environments lacked the strict dependency initialization constraints needed to surface startup race conditions prior to production deployment.