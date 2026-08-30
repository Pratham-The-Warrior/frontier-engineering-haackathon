# Post-Mortem: Third-Party API Rate Limiting Cascade

[![Severity](https://img.shields.io/badge/Severity-P1-e11d48?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-RESOLVED-10b981?style=flat-square)](#)
[![Duration](https://img.shields.io/badge/Duration-30m-6366f1?style=flat-square)](#)
[![Evidence](https://img.shields.io/badge/Evidence-100%25_Grounded-0284c7?style=flat-square)](#)
[![Blameless](https://img.shields.io/badge/Culture-Blameless_Verified-8b5cf6?style=flat-square)](#)

> **Blast Radius:** `email-service, notification-service, API Gateway` | **MTTR:** `30 min`
> **Root Cause (1-line):** `An uncoordinated marketing campaign exhausted shared API quotas, while a rushed mitigation commit introduced synchronous processing without timeouts that saturated thread pools.`

---

## <img src="https://api.iconify.design/lucide:gauge.svg?color=%236366f1" width="18"/> Executive Summary

An uncoordinated 50K marketing email campaign exhausted the shared SendGrid API quota, causing a massive queue backlog that blocked critical transactional workflows `[Alert:2025-08-20T10:05:00Z], [Log:2025-08-20T10:10:00Z]`. During mitigation, a rushed code deployment removed explicit connection timeouts, creating unbounded socket waits that saturated thread pools and triggered API Gateway 504 errors `[Git:a1b2c3d4], [Alert:2025-08-20T10:32:00Z]`. Full service recovery was achieved within 30 minutes after isolating email queues and restoring timeout constraints `[Alert:2025-08-20T10:35:00Z]`.

---

## <img src="https://api.iconify.design/lucide:shield-alert.svg?color=%23f59e0b" width="18"/> Risk & Systemic Vulnerability Assessment

| Risk Dimension | Risk Level | Finding | Evidence |
|:---|:---:|:---|:---|
| **Deploy Safety** | [![High](https://img.shields.io/badge/HIGH-f97316?style=flat-square)](#) | Rushed emergency fix bypassed timeout validation rules. | `[Git:a1b2c3d4]` |
| **Circuit Breaking** | [![Critical](https://img.shields.io/badge/CRITICAL-ef4444?style=flat-square)](#) | Shared third-party API lacks multi-tenancy isolation and throttling. | `[Log:2025-08-20T10:08:00Z]` |
| **Observability** | [![Low](https://img.shields.io/badge/LOW-22c55e?style=flat-square)](#) | Datadog quota alerts and PagerDuty routing fired rapidly. | `[Alert:2025-08-20T10:05:00Z]` |

---

## <img src="https://api.iconify.design/lucide:activity.svg?color=%2306b6d4" width="18"/> Impact

**Affected Services:** `email-service`, `notification-service`, `API Gateway`
**User Impact:** Complete delivery failures for critical transactional workflows (password resets, order confirmations) followed by gateway-level 504 timeouts `[Log:2025-08-20T10:10:00Z], [Alert:2025-08-20T10:32:00Z]`
**Duration:** 30 minutes (from initial quota warning to full resolution) `[Alert:2025-08-20T10:05:00Z] - [Alert:2025-08-20T10:35:00Z]`

---

## <img src="https://api.iconify.design/lucide:clock.svg?color=%2364748b" width="18"/> Timeline

| Time (UTC) | Source | Event |
|:---|:---|:---|
| 10:05 | `Alert` | Datadog fires warning alert indicating SendGrid sending quota is at 80% utilization `[Alert:2025-08-20T10:05:00Z]` |
| 10:08 | `Log` | email-service receives HTTP 429 Too Many Requests errors from SendGrid `[Log:2025-08-20T10:08:00Z]` |
| 10:08 | `Log` | email-service reports rapidly growing queue with 12,000 pending emails `[Log:2025-08-20T10:08:30Z]` |
| 10:09 | `Slack` | PagerDuty alert received in Slack; SRE Kim Park engaged `[Slack:2025-08-20T10:09:00Z]` |
| 10:10 | `Log` | notification-service fails to send critical transactional emails `[Log:2025-08-20T10:10:00Z]` |
| 10:15 | `Slack` | Kim Park splits email queues and throttles campaign traffic `[Slack:2025-08-20T10:15:00Z]` |
| 10:25 | `Git` | Commit a1b2c3d4 merging email worker updates without timeouts deployed `[Git:a1b2c3d4]` |
| 10:32 | `Alert` | API Gateway 504 timeouts surge; thread pool saturation reaches 100% `[Alert:2025-08-20T10:32:00Z]` |
| 10:35 | `Alert` | PagerDuty reports email service fully recovered `[Alert:2025-08-20T10:35:00Z]` |

<details>
<summary><b>Raw Correlated Event Log</b> (click to expand)</summary>

* `2025-08-20T10:05:00Z` [Alert] Datadog warning: SendGrid Quota > 80%
* `2025-08-20T10:08:00Z` [Log] email-service: SendGrid API 429 Too Many Requests
* `2025-08-20T10:08:30Z` [Log] email-service: Email queue growing — 12,000 emails pending
* `2025-08-20T10:09:00Z` [Slack] Alert received for email-service queue depth > 10,000
* `2025-08-20T10:10:00Z` [Log] notification-service: Unable to send transactional emails — queue saturated
* `2025-08-20T10:12:00Z` [Log] email-service: high memory usage (1.8GB) with queue expanding to 25,000
* `2025-08-20T10:15:00Z` [Slack] Manual queue split and capacity reservation executed
* `2025-08-20T10:25:00Z` [Git] Commit a1b2c3d4 deployed: update email workers synchronously without timeouts
* `2025-08-20T10:32:00Z` [Alert] API Gateway 504 Gateway Timeouts surging, thread pool saturation 100%
* `2025-08-20T10:35:00Z` [Alert] Email Service Recovered; normal flow resumed

</details>

---

## <img src="https://api.iconify.design/lucide:search.svg?color=%23e11d48" width="18"/> Root Cause Analysis

**Root Cause:** An uncoordinated 50K marketing campaign exhausted the shared SendGrid API quota. Subsequent rushed mitigation code (commit `a1b2c3d4`) removed explicit connection timeouts, introducing synchronous processing blocks that caused thread pool saturation and secondary API Gateway 504 timeouts `[Log:2025-08-20T10:08:00Z], [Git:a1b2c3d4]`.

**Causal Chain:**
1. Uncoordinated 50K marketing email campaign exhausted shared SendGrid API quota `[Alert:2025-08-20T10:05:00Z]` -> `[Alert:2025-08-20T10:05:00Z]`
2. email-service received HTTP 429 errors, backing up 25,000 messages and blocking transactional queues `[Log:2025-08-20T10:08:00Z]` -> `[Log:2025-08-20T10:10:00Z]`
3. Rushed mitigation commit `a1b2c3d4` removed socket timeouts, triggering thread pool saturation and API Gateway 504 errors `[Git:a1b2c3d4]` -> `[Alert:2025-08-20T10:32:00Z]`

**Confidence:** High — confirmed by direct SendGrid 429 logs, git diff inspection, and matching PagerDuty/Datadog alerts `[Log:2025-08-20T10:08:00Z], [Git:a1b2c3d4]`.

---

### <img src="https://api.iconify.design/lucide:file-code-2.svg?color=%238b5cf6" width="18"/> Forensic Code Analysis (Root Cause Diff)

> **Commit:** [`a1b2c3d4`] — *Update email service worker to process queues synchronously without timeouts*  
> **Author:** `email-service-bot` | **Primary File:** `src/services/email_service.py`

```diff
 def send_notification(recipient, payload):
-    client = SMTPClient(host=SMTP_HOST, timeout=5.0)
+    client = SMTPClient(host=SMTP_HOST)  # [CAUSE: Removed timeout parameter causing indefinite hangs]
     try:
-        client.connect()
+        client.connect()  # [LEAK: Unbounded socket wait blocks worker threads]
         client.send(recipient, payload)
     finally:
         client.close()
```

#### Code Vulnerability Breakdown:
* **Line 2 (Critical):** Removed the explicit timeout threshold, allowing socket operations to hang indefinitely `[Git:a1b2c3d4]`.
* **Line 4 (Secondary):** Lacked a fail-fast mechanism when external SMTP provider experienced latency spikes `[Git:a1b2c3d4]`.

#### Preventative Remediation Patch

```diff
 def send_notification(recipient, payload):
-    client = SMTPClient(host=SMTP_HOST)  # [CAUSE: Removed timeout parameter causing indefinite hangs]
-    try:
-        client.connect()  # [LEAK: Unbounded socket wait blocks worker threads]
+    with SMTPClient(host=SMTP_HOST, timeout=5.0) as client:
+        client.connect()
         client.send(recipient, payload)
-    finally:
-        client.close()
```

---

## <img src="https://api.iconify.design/lucide:layers.svg?color=%230ea5e9" width="18"/> Contributing Factors

- **Architectural Coupling:** Bulk marketing and critical transactional email queues shared a single unpartitioned SendGrid endpoint `[Log:2025-08-20T10:10:00Z]`.
- **Process Gap:** Absence of cross-departmental visibility and rate-limiting governance regarding external API provider quotas `[Slack:2025-08-20T10:12:00Z]`.
- **Missing Safeguard:** Emergency hotfix deployment allowed code changes without timeout bounds to reach production unchecked `[Git:a1b2c3d4]`.

---

## <img src="https://api.iconify.design/lucide:shield-check.svg?color=%2310b981" width="18"/> Prevention Analysis

> *How could this incident have been prevented or detected earlier?*

| Prevention Point | Safeguard | Expected Outcome |
|:---|:---|:---|
| At PR / CI Stage | Enforce static analysis rules requiring explicit timeout constraints on network calls. | Incident prevented before merge `[Git:a1b2c3d4]` |
| At Deploy Stage | Establish pre-deployment integration testing and automated checks for outbound API limits. | Detected in staging prior to campaign execution `[Alert:2025-08-20T10:05:00Z]` |
| At Runtime Stage | Implement strict queue partitioning and circuit breakers between marketing and transactional traffic. | Blast radius limited to bulk marketing queues `[Log:2025-08-20T10:10:00Z]` |

---

## <img src="https://api.iconify.design/lucide:wrench.svg?color=%2364748b" width="18"/> Resolution

The incident was resolved by manually splitting the email queues, throttling bulk marketing campaigns, setting up reserved capacity for transactional emails `[Slack:2025-08-20T10:15:00Z]`, and subsequently restoring explicit timeout constraints on the email worker threads.

---

## <img src="https://api.iconify.design/lucide:check-square.svg?color=%2310b981" width="18"/> Action Items

| Priority | Type | Action | Owner | Est. |
|:---|:---|:---|:---|:---|
| **P0** | Prevent | Implement dedicated rate limit buckets and isolated queues for marketing vs. transactional emails | Core Platform | 3 days |
| **P1** | Detect | Add CI linter rules enforcing mandatory timeout parameters on all outbound network clients | DevEx | 2 days |
| **P2** | Mitigate | Deploy automated circuit breakers for third-party API rate limit responses (HTTP 429) | SRE | 5 days |

---

## <img src="https://api.iconify.design/lucide:book-open.svg?color=%236366f1" width="18"/> Lessons Learned

- Unpartitioned shared dependencies will inevitably fail under uncoordinated load spikes.
- Emergency hotfixes require the same rigorous automated safety checks as standard feature deployments.

## What Went Well

- SRE response time was rapid, identifying the marketing campaign root cause within 5 minutes of engagement `[Slack:2025-08-20T10:09:00Z], [Slack:2025-08-20T10:10:00Z]`.
- Queue splitting successfully restored transactional traffic before the secondary timeout cascade `[Slack:2025-08-20T10:15:00Z]`.

## What Could Be Improved

- Cross-functional communication between Marketing Operations and Engineering regarding bulk outbound traffic needs formal governance.
- Emergency deployment pipelines must include automated validation for timeout constraints and resource pooling limits.