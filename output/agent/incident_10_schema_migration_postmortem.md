# Post-Mortem: Data Pipeline Corruption From Out-of-Order Schema Migration

[![Severity](https://img.shields.io/badge/Severity-SEV1-e11d48?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-RESOLVED-10b981?style=flat-square)](#)
[![Duration](https://img.shields.io/badge/Duration-305m-6366f1?style=flat-square)](#)
[![Evidence](https://img.shields.io/badge/Evidence-100%25_Grounded-0284c7?style=flat-square)](#)
[![Blameless](https://img.shields.io/badge/Culture-Blameless_Verified-8b5cf6?style=flat-square)](#)

> **Blast Radius:** `migration-runner, database, data-pipeline, reporting-service, analytics dashboards` | **MTTR:** `130 min after root cause identified`
> **Root Cause (1-line):** `An out-of-order schema migration sequence numbering defect caused migration 043 to reference a function defined in migration 044, leading to a partial rollback and unpopulated status data that corrupted downstream ETL pipelines.`

---

## <img src="https://api.iconify.design/lucide:gauge.svg?color=%236366f1" width="18"/> Executive Summary

An out-of-order database migration sequence numbering defect caused migration 043 to reference a function defined in migration 044, leading to a partial deployment failure and unpopulated status column data `[Log:2025-09-15T03:01:05Z]`. This unpopulated schema state cascaded into critical ETL NOT NULL constraint violations and reporting division-by-zero errors for over three hours `[Log:2025-09-15T06:00:00Z], [Log:2025-09-15T06:30:00Z]`. The incident was fully resolved when an engineer manually executed the correct migration sequence and re-ran the pipeline `[Slack:Maya Singh:06:25:00]`.

---

## <img src="https://api.iconify.design/lucide:shield-alert.svg?color=%23f59e0b" width="18"/> Risk & Systemic Vulnerability Assessment

| Risk Dimension | Risk Level | Finding | Evidence |
|:---|:---:|:---|:---|
| **Deploy Safety** | [![High](https://img.shields.io/badge/HIGH-f97316?style=flat-square)](#) | Absence of CI validation checks for forward-referencing function dependencies across SQL files. | `[Git: Commit mig001]` |
| **Circuit Breaking** | [![Critical](https://img.shields.io/badge/CRITICAL-ef4444?style=flat-square)](#) | Migration runner lacked schema-health liveness probes to halt downstream scheduled workloads upon rollback. | `[Log:2025-09-15T03:01:05Z]` |
| **Observability** | [![Medium](https://img.shields.io/badge/MEDIUM-eab308?style=flat-square)](#) | Downstream services lacked defensive input aggregation logic, causing cascading failures on NULL data. | `[Log:2025-09-15T06:30:00Z]` |

---

## <img src="https://api.iconify.design/lucide:activity.svg?color=%2306b6d4" width="18"/> Impact

**Affected Services:** `migration-runner`, `database`, `data-pipeline`, `reporting-service`, `analytics dashboards`
**User Impact:** Downstream analytics dashboards showed blank data, daily reports failed to generate, and automated data pipelines were halted for 305 minutes `[Log:2025-09-15T06:01:00Z]`.
**Duration:** 305 minutes, from trigger time (2025-09-14T15:00:00Z) to full recovery (2025-09-15T08:10:00Z).

---

## <img src="https://api.iconify.design/lucide:clock.svg?color=%2364748b" width="18"/> Timeline

| Time (UTC) | Source | Event |
|:---|:---|:---|
| 2025-09-14 15:00 | `Git` | Migration commits merged containing incorrect numbering sequence where migration 043 references a function in migration 044 `[Git:Commit mig001]` |
| 2025-09-15 03:01 | `Log` | migration-runner failed migration_043 because it referenced a non-existent function in migration_044 `[Log:2025-09-15T03:01:00Z]` |
| 2025-09-15 03:01 | `Log` | migration_043 rolled back, leaving migration_042 committed with an empty status column `[Log:2025-09-15T03:01:05Z]` |
| 2025-09-15 06:00 | `Log` | data-pipeline ETL job failed with a NOT NULL constraint violation on analytics table `[Log:2025-09-15T06:00:00Z]` |
| 2025-09-15 06:00 | `Alert` | PagerDuty fired critical alert for ETL Pipeline Failure due to NULL constraint violations `[Alert:ETL Pipeline Failed]` |
| 2025-09-15 06:15 | `Slack` | Maya Singh discovered migration_043 function dependency mismatch `[Slack:Maya Singh:06:15:00]` |
| 2025-09-15 06:25 | `Slack` | Maya Singh initiated manual remediation to execute migration 044 first and re-run pipeline `[Slack:Maya Singh:06:25:00]` |
| 2025-09-15 06:30 | `Log` | reporting-service failed to generate daily reports due to division by zero `[Log:2025-09-15T06:30:00Z]` |
| 2025-09-15 08:10 | `Slack` | Maya Singh confirmed all migrations, pipelines, and dashboards were fully restored `[Slack:Maya Singh:08:10:00]` |

<details>
<summary><b>Raw Correlated Event Log</b> (click to expand)</summary>

* `2025-09-14T15:00:00Z` [Git] Commit mig001: files migrations/042_add_status_column.sql, migrations/043_backfill_status.sql, migrations/044_compute_status_function.sql
* `2025-09-15T03:01:00Z` [Log] migration_043 failed: cannot backfill — references migration_044 function that doesn't exist yet
* `2025-09-15T03:01:05Z` [Log] migration_043 rolled back, leaving migration_042 committed with an empty status column
* `2025-09-15T06:00:00Z` [Log] data-pipeline ETL job failed with a NOT NULL constraint violation on 'status' column in analytics table
* `2025-09-15T06:00:30Z` [Alert] PagerDuty alert: ETL Pipeline Failed
* `2025-09-15T06:01:00Z` [Log] Pipeline writing NULL status values. Downstream analytics dashboards showing blank data.
* `2025-09-15T06:05:00Z` [Slack] AlertBot reported a data-pipeline ETL job failure with NULL constraint violations
* `2025-09-15T06:10:00Z` [Slack] Maya Singh noted that the 'status' column from last night's migration was all NULLs and the backfill failed
* `2025-09-15T06:15:00Z` [Slack] Maya Singh discovered that migration_043 depended on a function in migration_044
* `2025-09-15T06:20:00Z` [Slack] Jake Brown acknowledged that the migration was split into 3 parts and incorrectly numbered
* `2025-09-15T06:25:00Z` [Slack] Maya Singh proposed and initiated the fix to manually execute migration 044 first
* `2025-09-15T06:30:00Z` [Log] Daily report generation failed: division by zero — status counts are all NULL
* `2025-09-15T06:30:30Z` [Alert] Datadog alert: Daily Reports Failed
* `2025-09-15T08:10:00Z` [Slack] Maya Singh confirmed migrations, pipeline, analytics data, and dashboards were fully fixed

</details>

---

## <img src="https://api.iconify.design/lucide:search.svg?color=%23e11d48" width="18"/> Root Cause Analysis

**Root Cause:** An out-of-order database migration sequence numbering defect caused migration 043 to reference a function defined in migration 044, resulting in a partial migration rollback that left unpopulated column data and triggered downstream ETL failures `[Log:2025-09-15T03:01:05Z]`.

**Causal Chain:**
1. Migration commits merged containing incorrect numbering sequence where migration 043 references a function in migration 044 `[Git:2025-09-14T15:00:00Z]` -> `[Git:Commit mig001]`
2. migration-runner fails migration 043 and executes rollback, leaving migration 042 committed with an empty status column `[Log:2025-09-15T03:01:05Z]` -> `[Log:2025-09-15T03:01:05Z]`
3. data-pipeline ETL job fails due to NOT NULL constraint violations on the unpopulated status column `[Log:2025-09-15T06:00:00Z]` -> `[Log:2025-09-15T06:00:00Z]`
4. reporting-service fails to generate daily reports due to division by zero errors `[Log:2025-09-15T06:30:00Z]` -> `[Log:2025-09-15T06:30:00Z]`

**Confidence:** High — supported by explicit git commit logs, unambiguous migration runner errors, and direct team investigation notes `[Git:Commit mig001], [Log:2025-09-15T03:01:00Z], [Slack:Maya Singh:06:15:00]`.

---

### <img src="https://api.iconify.design/lucide:file-code-2.svg?color=%238b5cf6" width="18"/> Forensic Code Analysis (Root Cause Diff)

> **Commit:** [`mig001`] — *Add status column, backfill, and compute status function*  
> **Author:** `Development Team` | **Primary File:** `migrations/043_backfill_status.sql`

```diff
--- a/migrations/043_backfill_status.sql
+++ b/migrations/043_backfill_status.sql
@@ -1,3 +1,3 @@
 UPDATE orders
-SET status = compute_status(id);
+SET status = compute_status(id); # 🚨 CAUSE: function compute_status() does not exist yet (defined in migration 044)
```

#### Code Vulnerability Breakdown:
* **Line 2 (Critical):** Calls function `compute_status()` before it is defined in sequence, causing the migration execution to fail and trigger an incomplete schema rollback `[Log:2025-09-15T03:01:00Z]`.

#### Preventative Remediation Patch

```diff
--- a/migrations/043_backfill_status.sql
+++ b/migrations/043_backfill_status.sql
@@ -1,3 +1,3 @@
 UPDATE orders
--- FIX: Ensure function definition precedes usage, or combine migration files
-SET status = compute_status(id);
+SET status = compute_status(id);
```

---

## <img src="https://api.iconify.design/lucide:layers.svg?color=%230ea5e9" width="18"/> Contributing Factors

- **Lack of CI Validation Checks:** Absence of automated checks for forward-referencing function dependencies across SQL migration files `[Git:2025-09-14T15:00:00Z]`.
- **Missing Deployment Safeguards:** Absence of migration runner health-gates to halt dependent scheduled workloads upon partial rollbacks `[Log:2025-09-15T03:01:05Z], [Log:2025-09-15T06:00:00Z]`.
- **Defensive Coding Gaps:** Downstream reporting and analytics services assumed non-null status values and safe aggregation denominators `[Log:2025-09-15T06:30:00Z]`.

---

## <img src="https://api.iconify.design/lucide:shield-check.svg?color=%2310b981" width="18"/> Prevention Analysis

> *How could this incident have been prevented or detected earlier?*

| Prevention Point | Safeguard | Expected Outcome |
|:---|:---|:---|
| At PR / CI Stage | Automated SQL migration dependency validator checking sequence order. | Intercept numbering defect before merge `[Git:2025-09-14T15:00:00Z]` |
| At Deploy Stage | Migration runner circuit breaker pausing dependent scheduled tasks on rollback. | Prevent ETL execution against unpopulated schema `[Log:2025-09-15T03:01:05Z]` |
| At Runtime Stage | Defensive null-handling and safe division wrappers in reporting services. | Prevent cascading division-by-zero errors `[Log:2025-09-15T06:30:00Z]` |

---

## <img src="https://api.iconify.design/lucide:wrench.svg?color=%2364748b" width="18"/> Resolution

Data engineer Maya Singh identified the dependency mismatch in Slack `[Slack:Maya Singh:06:15:00]`, manually executed migration 044 to provide the missing function, successfully re-ran migration 043, and triggered the data pipeline recovery `[Slack:Maya Singh:06:25:00]`. Full system health, dashboards, and reporting services were verified and restored by 08:10 UTC `[Slack:Maya Singh:08:10:00]`.

---

## <img src="https://api.iconify.design/lucide:check-square.svg?color=%2310b981" width="18"/> Action Items

| Priority | Type | Action | Owner | Est. |
|:---|:---|:---|:---|:---|
| **P0** | Prevent | Implement CI migration linter to validate sequence order and function dependencies. | Database Team | 3 days |
| **P1** | Detect | Add migration runner circuit breaker to pause dependent ETL jobs on rollback. | Data Engineering | 5 days |
| **P2** | Mitigate | Add defensive null-handling and safe division wrappers to reporting service. | Analytics Team | 4 days |

---

## <img src="https://api.iconify.design/lucide:book-open.svg?color=%236366f1" width="18"/> Lessons Learned

- Complex database migrations split across multiple files must be validated for inter-file function dependencies before merge `[Git:Commit mig001]`.
- Downstream scheduled tasks must not operate on unverified schema assumptions following partial deployment rollbacks `[Log:2025-09-15T03:01:05Z]`.

## What Went Well

- Automated PagerDuty and Datadog alerts successfully notified the team of ETL and reporting failures `[Alert:ETL Pipeline Failed], [Alert:Daily Reports Failed]`.
- Cross-functional investigation in Slack rapidly pinpointed the root cause within 15 minutes of detection `[Slack:Maya Singh:06:15:00]`.

## What Could Be Improved

- Pre-deployment CI checks lacked SQL semantic and function