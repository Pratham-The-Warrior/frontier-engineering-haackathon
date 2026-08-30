# Post-Mortem: Disk Space Exhaustion From Disabled Log Rotation

[![Severity](https://img.shields.io/badge/Severity-SEV1-e11d48?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-RESOLVED-10b981?style=flat-square)](#)
[![Duration](https://img.shields.io/badge/Duration-35m-6366f1?style=flat-square)](#)
[![Evidence](https://img.shields.io/badge/Evidence-100%25_Grounded-0284c7?style=flat-square)](#)
[![Blameless](https://img.shields.io/badge/Culture-Blameless_Verified-8b5cf6?style=flat-square)](#)

> **Blast Radius:** `data-pipeline-01, downstream consumers` | **MTTR:** `35 min after root cause identified`
> **Root Cause (1-line):** `Unrotated debug logs accumulated indefinitely due to a persistent configuration change that disabled log rotation, resulting in complete storage exhaustion (ENOSPC) during high-volume batch ingestion.`

---

## <img src="https://api.iconify.design/lucide:gauge.svg?color=%236366f1" width="18"/> Executive Summary

A debugging configuration change that disabled log rotation persisted in production, leading to the silent accumulation of 180GB of unrotated logs over several days `[Git:a1b2c3d4]`, `[Slack:Maya Singh investigation notes]`. Despite early Datadog disk warnings at 75% and 90% capacity `[Alerts:Datadog warning alert: Disk Usage > 75%]`, no active remediation occurred prior to a scheduled weekly batch ingestion `[Git:Scheduled batch job execution timeline]`. This culminated in a fatal 'No space left on device' (ENOSPC) write failure and a total pipeline halt `[Logs:Write failed: No space left on device]`, which was fully resolved within 35 minutes by clearing old logs, re-enabling log rotation, and processing the backlog `[Slack:Maya Singh communication]`.

---

## <img src="https://api.iconify.design/lucide:shield-alert.svg?color=%23f59e0b" width="18"/> Risk & Systemic Vulnerability Assessment

| Risk Dimension | Risk Level | Finding | Evidence |
|:---|:---:|:---|:---|
| **Deploy Safety** | [![High](https://img.shields.io/badge/HIGH-f97316?style=flat-square)](#) | Temporary debugging configuration changes lacked TTLs or automated review safeguards before landing in production manifests. | `[Git:a1b2c3d4e5f67890123456789abcdef012345678]` |
| **Circuit Breaking** | [![Critical](https://img.shields.io/badge/CRITICAL-ef4444?style=flat-square)](#) | Application lacked resilience or backpressure mechanisms when encountering disk full conditions, resulting in a hard crash. | `[Logs:Write failed: No space left on device]` |
| **Observability** | [![Low](https://img.shields.io/badge/LOW-22c55e?style=flat-square)](#) | Datadog accurately triggered 75% and 90% disk usage warnings and PagerDuty correctly alerted on the pipeline halt. | `[Alerts:Datadog warning alert: Disk Usage > 75%]`, `[Alerts:PagerDuty alert]` |

---

## <img src="https://api.iconify.design/lucide:activity.svg?color=%2306b6d4" width="18"/> Impact

**Affected Services:** `data-pipeline-01`, `data-pipeline service`, `downstream consumers`
**User Impact:** The data pipeline completely halted, causing downstream consumers to stall due to a lack of data feed updates until processing was successfully recovered and backlogs were cleared `[Slack:AlertBot and downstream consumer logs]`.
**Duration:** `35 minutes` (from first critical alert at 09:15:30 UTC to resolution at 09:50:00 UTC)

---

## <img src="https://api.iconify.design/lucide:clock.svg?color=%2364748b" width="18"/> Timeline

| Time (UTC) | Source | Event |
|:---|:---|:---|
| 2025-08-05 01:55 | `Git` | Log rotation was disabled and configuration parameters were updated in config/data-pipeline.yaml during a debugging session. `[Git:a1b2c3d4]` |
| 2025-08-08 14:00 | `Alerts` | Datadog triggered a warning as disk usage reached 75% on host data-pipeline-01. `[Alerts:Disk Usage > 75%]` |
| 2025-08-10 06:00 | `Alerts` | Datadog triggered a warning as disk usage increased to 90% on host data-pipeline-01. `[Alerts:Disk Usage > 90%]` |
| 2025-08-10 09:00 | `Git` | Scheduled weekly high-volume batch ingestion triggered, accelerating resource utilization. `[Git:Batch execution timeline]` |
| 2025-08-10 09:15 | `Logs` | Write failed with 'No space left on device' (ENOSPC) error on data-pipeline. `[Logs:Write failed: No space left on device]` |
| 2025-08-10 09:15:30 | `Alerts` | PagerDuty critical alert triggered for data-pipeline halt due to disk full condition. `[Alerts:PagerDuty alert]` |
| 2025-08-10 09:18 | `Slack` | Maya Singh confirmed disk was 100% full due to 180GB of unrotated log files in /var/log/data-pipeline. `[Slack:Maya Singh notes]` |
| 2025-08-10 09:25 | `Slack` | Maya Singh cleaned old logs and re-enabled log rotation to recover the pipeline. `[Slack:Maya Singh mitigation]` |
| 2025-08-10 09:50 | `Alerts` | PagerDuty resolved alert and Maya Singh reported the pipeline was back and processing the backlog with no data loss. `[Alerts:PagerDuty resolution]` |

<details>
<summary><b>Raw Correlated Event Log</b> (click to expand)</summary>

- `2025-08-05T01:55:00Z` [Git] Commit a1b2c3d4e5f67890123456789abcdef012345678: Log rotation parameters modified in config/data-pipeline.yaml.
- `2025-08-08T14:00:00Z` [Alerts] Datadog warning alert: Disk Usage > 75% on data-pipeline-01.
- `2025-08-10T06:00:00Z` [Alerts] Datadog warning alert: Disk Usage > 90% on data-pipeline-01.
- `2025-08-10T09:00:00Z` [Git] Scheduled weekly high-volume batch ingestion execution started.
- `2025-08-10T09:15:00Z` [Logs] Fatal write error: No space left on device (ENOSPC) in /var/log/data-pipeline.
- `2025-08-10T09:15:30Z` [Alerts] PagerDuty critical alert triggered: data-pipeline Halted.
- `2025-08-10T09:16:00Z` [Slack] AlertBot reported data-pipeline-01 disk full; downstream consumers stalled.
- `2025-08-10T09:18:00Z` [Slack] Maya Singh investigated `/var/log/data-pipeline`, discovering 180GB of unrotated logs.
- `2025-08-10T09:20:00Z` [Slack] Maya Singh identified root cause: un-reverted debugging configuration change from Aug 5.
- `2025-08-10T09:25:00Z` [Slack] Maya Singh purged stale log files and re-enabled log rotation in configuration.
- `2025-08-10T09:50:00Z` [Alerts/Slack] PagerDuty resolved; pipeline resumed normal processing of backlog with zero data loss.

</details>

---

## <img src="https://api.iconify.design/lucide:search.svg?color=%23e11d48" width="18"/> Root Cause Analysis

**Root Cause:** Configuration parameters in `config/data-pipeline.yaml` were updated during a debugging session to disable log rotation and left un-reverted in production, causing 180GB of unrotated logs to accumulate silently until complete storage exhaustion (ENOSPC) halted the pipeline during a scheduled high-volume batch ingestion `[Git:a1b2c3d4]`, `[Slack:Maya Singh investigation notes]`, `[Logs:Write failed: No space left on device]`.

**Causal Chain:**
1. Log rotation was disabled in configuration files during a debugging session. `[Git:a1b2c3d4e5f67890123456789abcdef012345678]`
2. Unrotated log files accumulated continuously, consuming 180GB of disk space over several days. `[Slack:Maya Singh investigation notes]`
3. Datadog issued disk usage warnings at 75% and 90% capacity without triggering active remediation. `[Alerts:Datadog warning alert: Disk Usage > 75%]`, `[Alerts:Datadog warning alert: Disk Usage > 90%]`
4. Scheduled weekly high-volume batch ingestion executed, accelerating resource consumption. `[Git:Scheduled batch job execution timeline]`
5. Host data-pipeline-01 suffered complete disk exhaustion, causing write failures and a pipeline halt. `[Logs:Write failed: No space left on device]`, `[Alerts:PagerDuty alert]`

**Confidence:** High — substantiated by git configuration history, cumulative disk usage telemetry, explicit ENOSPC log errors, and manual verification `[Git:a1b2c3d4]`, `[Alerts:Datadog warnings]`, `[Logs:ENOSPC]`.

---

### <img src="https://api.iconify.design/lucide:file-code-2.svg?color=%238b5cf6" width="18"/> Forensic Code Analysis (Root Cause Diff)

> **Commit:** [`a1b2c3d`] — *Disable log rotation for active debug tracing*  
> **Author:** `Debugging Engineer` | **Primary File:** `config/data-pipeline.yaml`

```diff
 logging:
   level: debug
-  rotation:
-    enabled: true
-    max_size_mb: 500
-    max_files: 10
+  rotation:
+    enabled: false  # [CAUSE: Log rotation disabled for temporary troubleshooting and left un-reverted]
```

#### Code Vulnerability Breakdown:
* **Line 3 (Critical):** Removing the log rotation block entirely or setting `enabled: false` allows unbounded file growth in `/var/log/data-pipeline`.
* **Line 4 (Secondary):** Lack of retention limits or maximum file constraints permits infinite local disk consumption.

#### Preventative Remediation Patch

```diff
 logging:
   level: info
   rotation:
     enabled: true   # [FIX: Enforce active log rotation in all production manifests]
     max_size_mb: 500
     max_files: 10
```

---

## <img src="https://api.iconify.design/lucide:layers.svg?color=%230ea5e9" width="18"/> Contributing Factors

- **Absence of automated configuration guardrails:** No TTLs or validation rules existed to prevent temporary debugging changes from persisting in production manifests `[Git:a1b2c3d4e5f67890123456789abcdef012345678]`.
- **Monitoring gap / alert fatigue:** Early warning telemetry (75% and 90% disk usage alerts) during the multi-day accumulation phase failed to trigger active operational intervention `[Alerts:Datadog warning alert: Disk Usage > 75%]`, `[Alerts:Datadog warning alert: Disk Usage > 90%]`.
- **Design flaw in application resilience:** The data pipeline application lacked backpressure or graceful degradation mechanisms to handle disk constraints cleanly rather than failing hard with ENOSPC `[Logs:Write failed: No space left on device]`.

---

## <img src="https://api.iconify.design/lucide:shield-check.svg?color=%2310b981" width="18"/> Prevention Analysis

> *How could this incident have been prevented or detected earlier?*

| Prevention Point | Safeguard | Expected Outcome |
|:---|:---|:---|
| At PR / CI Stage | Automated configuration linting policies to detect disabled log rotation. | Would have flagged or blocked the PR introducing the disabled log rotation setting before deployment. |
| At Deploy Stage | Policy enforcement tools (e.g., OPA/Gatekeeper) requiring mandatory log rotation parameters. | Would have prevented deployment of configurations violating core infrastructure safety baselines. |
| At Runtime Stage | Application-level disk space monitoring with automated circuit breakers or graceful degradation. | Would have prevented a hard crash, providing a safer buffer for remediation. |

---

## <img src="https://api.iconify.design/lucide:wrench.svg?color=%2364748b" width="18"/> Resolution

Maya Singh identified the root cause via Slack investigation at 09:20 UTC `[Slack:Maya Singh investigation updates]`. Immediate mitigation was performed at 09:25 UTC by purging stale log files from `/var/log/data-pipeline` and re-enabling log rotation in `config/data-pipeline.yaml` `[Slack:Maya Singh mitigation]`. The pipeline was restarted and confirmed healthy by 09:50 UTC, successfully processing its data backlog with zero data loss `[Alerts:PagerDuty resolution notice]`.

---

## <img src="https://api.iconify.design/lucide:check-square.svg?color=%2310b981" width="18"/> Action Items

| Priority | Type | Action | Owner | Est. |
|:---|:---|:---|:---|:---|
| **P0** | Prevent | Implement CI configuration linter rules enforcing mandatory log rotation across all production services. | Core Platform Team | 3 days |
| **P1** | Detect | Escalate disk usage warning alerts (at 90%) to PagerDuty rather than Slack-only warnings. | SRE Team | 2 days |
| **P2** | Mitigate | Add application-level disk space circuit breakers to pause ingestion gracefully when disk falls below 10%. | Data Engineering | 5 days |

---

## <img src="https://api.iconify.design/lucide:book-open.svg?color=%236366f1" width="18"/> Lessons Learned

- Temporary debugging configurations must be accompanied by automated expiration mechanisms or strict peer review before reaching production environments.
- Warning-level alerts without on-call paging can result in deferred maintenance during multi-day accumulation phases.

## What Went Well

- Incident response and mitigation by engineering staff were highly efficient once the root cause was identified, resolving the outage in 35 minutes.
- Zero data loss occurred during the pipeline recovery and backlog processing phase.

## What Could Be Improved

- Operational response processes for multi-day disk warning alerts need refinement to prevent oversight before storage reaches 100%.
- Application resilience should be enhanced to handle storage exhaustion gracefully without hard crashes.