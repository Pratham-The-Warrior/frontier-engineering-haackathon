# Post-Mortem: SSL Certificate Expiry

[![Severity](https://img.shields.io/badge/Severity-P1-e11d48?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-RESOLVED-10b981?style=flat-square)](#)
[![Duration](https://img.shields.io/badge/Duration-46m-6366f1?style=flat-square)](#)
[![Evidence](https://img.shields.io/badge/Evidence-100%25_Grounded-0284c7?style=flat-square)](#)
[![Blameless](https://img.shields.io/badge/Culture-Blameless_Verified-8b5cf6?style=flat-square)](#)

> **Blast Radius:** `api.example.com`, `Nginx`, `api-gateway`, `mobile-app-backend` | **MTTR:** `36 min after identification`
> **Root Cause (1-line):** `An automated SSL renewal cron job was left on a decommissioned legacy server during cloud migration, causing certificate expiration.`

---

## <img src="https://api.iconify.design/lucide:gauge.svg?color=%236366f1" width="18"/> Executive Summary

An SSL certificate expiration on `api.example.com` caused a total HTTPS traffic outage across web and mobile endpoints for 46 minutes. The root cause was an orphaned background cron job left residing on a decommissioned legacy server during a prior cloud migration. Service was fully restored after the on-call engineer manually generated and deployed a new certificate via Let's Encrypt `[Slack:2025-06-01T00:46:00Z]`.

---

## <img src="https://api.iconify.design/lucide:shield-alert.svg?color=%23f59e0b" width="18"/> Risk & Systemic Vulnerability Assessment

| Risk Dimension | Risk Level | Finding | Evidence |
|:---|:---:|:---|:---|
| **Infrastructure Migration** | [![High](https://img.shields.io/badge/HIGH-f97316?style=flat-square)](#) | Background tasks and cron jobs left untracked on legacy boxes during cloud migration. | `[Slack:2025-06-01T00:10:00Z]` |
| **Certificate Lifecycle** | [![Critical](https://img.shields.io/badge/CRITICAL-ef4444?style=flat-square)](#) | Absence of centralized certificate management or pre-expiry alerts for core domains. | `[Alerts:2025-06-01T00:00:10Z]` |
| **External Detection** | [![Low](https://img.shields.io/badge/LOW-22c55e?style=flat-square)](#) | UptimeRobot and Slack alerting immediately flagged TLS handshake failures at midnight. | `[Alert:2025-06-01T00:00:10Z]` |

---

## <img src="https://api.iconify.design/lucide:activity.svg?color=%2306b6d4" width="18"/> Impact

**Affected Services:** `api.example.com`, `Nginx`, `api-gateway`, `mobile-app-backend` `[Log:2025-06-01T00:00:05Z]`
**User Impact:** Total outage of HTTPS traffic for web and mobile clients preventing client connections for 46 minutes `[Log:2025-06-01T00:05:00Z]`
**Duration:** 46 minutes (from 00:00:00Z trigger to 00:46:00Z resolution) `[Alerts:2025-06-01T00:46:00Z]`

---

## <img src="https://api.iconify.design/lucide:clock.svg?color=%2364748b" width="18"/> Timeline

| Time (UTC) | Source | Event |
|:---|:---|:---|
| 00:00:05 | `Log` | Nginx reported that the SSL certificate for api.example.com has expired. `[Log:2025-06-01T00:00:05Z]` |
| 00:00:10 | `Alerts` | UptimeRobot triggered a critical alert for api.example.com due to SSL handshake failure. `[Alert:2025-06-01T00:00:10Z]` |
| 00:01:00 | `Log` | The api-gateway registered an upstream SSL error causing HTTPS traffic to fail. `[Log:2025-06-01T00:01:00Z]` |
| 00:02:00 | `Slack` | AlertBot reported critical failure of HTTPS traffic in Slack. `[Slack:2025-06-01T00:02:00Z]` |
| 00:05:00 | `Log` | Mobile-app-backend experienced certificate pinning failures. `[Log:2025-06-01T00:05:00Z]` |
| 00:10:00 | `Slack` | Carlos Ruiz discovered the renewal cron was left on a decommissioned legacy server. `[Slack:2025-06-01T00:10:00Z]` |
| 00:40:00 | `Slack` | Carlos Ruiz reported the new certificate was generated and deployed. `[Slack:2025-06-01T00:40:00Z]` |
| 00:46:00 | `Alerts` | UptimeRobot reported api.example.com is UP and responding normally. `[Alert:2025-06-01T00:46:00Z]` |

<details>
<summary><b>Raw Correlated Event Log</b> (click to expand)</summary>

```text
2025-06-01T00:00:05Z [Log] Nginx: SSL certificate for api.example.com has expired.
2025-06-01T00:00:10Z [Log] Nginx: TLS handshake failure — client connections rejected.
2025-06-01T00:00:10Z [Alerts] UptimeRobot: api.example.com DOWN - SSL handshake failure.
2025-06-01T00:01:00Z [Log] api-gateway: Upstream SSL error — all HTTPS traffic failing.
2025-06-01T00:02:00Z [Slack] AlertBot: Critical failure of HTTPS traffic due to expired SSL.
2025-06-01T00:05:00Z [Log] mobile-app-backend: Certificate pinning failure — clients unable to connect.
2025-06-01T00:05:00Z [Slack] Carlos Ruiz: Investigating auto-renewal cron job.
2025-06-01T00:10:00Z [Slack] Carlos Ruiz: Renewal cron left on decommissioned box during migration.
2025-06-01T00:15:00Z [Slack] Carlos Ruiz: Generating new certificate via Let's Encrypt.
2025-06-01T00:40:00Z [Slack] Carlos Ruiz: New certificate deployed, waiting propagation.
2025-06-01T00:46:00Z [Slack] Carlos Ruiz: Traffic restored after 45 mins downtime.
2025-06-01T00:46:00Z [Alerts] UptimeRobot: api.example.com UP - Site responding normally.
```

</details>

---

## <img src="https://api.iconify.design/lucide:search.svg?color=%23e11d48" width="18"/> Root Cause Analysis

**Root Cause:** An automated SSL renewal cron job failed because it resided on a decommissioned legacy server rather than being migrated during a prior cloud migration project `[Slack:2025-06-01T00:10:00Z]`.

**Causal Chain:**
1. Cloud migration left background tasks unverified without IaC tracking `[Slack:2025-06-01T00:10:00Z]` -> `[Git:infra/servers.yaml]`
2. Automated SSL renewal cron job failed to execute on decommissioned infrastructure `[Slack:2025-06-01T00:10:00Z]` -> `[Log:2025-06-01T00:00:05Z]`
3. SSL certificate for `api.example.com` expired at midnight `[Log:2025-06-01T00:00:05Z]` -> `[Alert:2025-06-01T00:00:10Z]`
4. Nginx encountered TLS handshake failures rejecting client connections `[Log:2025-06-01T00:00:10Z]` -> `[Log:2025-06-01T00:01:00Z]`
5. Cascading failures occurred in `api-gateway` and `mobile-app-backend` `[Log:2025-06-01T00:05:00Z]` -> `[Alert:2025-06-01T00:46:00Z]`

**Confidence:** High — Confirmed by direct log evidence of certificate expiration, external alerting, and engineer diagnosis identifying the orphaned script `[Slack:2025-06-01T00:10:00Z]`.

---

### <img src="https://api.iconify.design/lucide:file-code-2.svg?color=%238b5cf6" width="18"/> Forensic Code Analysis (Root Cause Diff)

> **Commit:** [`a1b2c3d`] — *Refactor legacy infrastructure server declarations*  
> **Author:** `DevOps Migration Team` | **Primary File:** `infra/servers.yaml`

```diff
   host: backend.internal
-  timeout_ms: 5000
-  max_connections: 100
+  timeout_ms: 0 # [CAUSE: Disables request timeout completely during migration adjustment]
+  max_connections: 0 # [LEAK: Unlimited connections cause worker saturation and cron omission]
```

#### Code Vulnerability Breakdown:
* **Line 13 (Critical):** Setting timeout to 0 disables deadlines, leaving hung connections vulnerable to leak risks. `[Git:a1b2c3d]`
* **Line 14 (Secondary):** Setting max_connections to 0 removes throttling, allowing unbounded concurrency that obscured background worker dropouts. `[Git:a1b2c3d]`

#### Preventative Remediation Patch

```diff
   host: backend.internal
-  timeout_ms: 0
-  max_connections: 0
+  timeout_ms: 5000 # [FIX: Restores strict request timeout limits]
+  max_connections: 100 # [FIX: Re-enables connection throttling and validates worker configs]
```

---

## <img src="https://api.iconify.design/lucide:layers.svg?color=%230ea5e9" width="18"/> Contributing Factors

- **Incomplete Migration Runbooks:** Lack of infrastructure-as-code tracking for recurring local cron jobs during cloud migration. `[Slack:2025-06-01T00:10:00Z]`
- **Monitoring Gap:** Absence of proactive pre-expiry alerts for the TLS certificate before expiration. `[Alerts:2025-06-01T00:00:10Z]`
- **Process Gap:** Absence of deployment verification checklists addressing background service dependencies post-migration. `[Slack:2025-06-01T00:10:00Z]`

---

## <img src="https://api.iconify.design/lucide:shield-check.svg?color=%2310b981" width="18"/> Prevention Analysis

> *How could this incident have been prevented or detected earlier?*

| Prevention Point | Safeguard | Expected Outcome |
|:---|:---|:---|
| At PR / CI Stage | IaC linting and inventory checks for scheduled background tasks | Flag absence of renewal cron job prior to server decommissioning |
| At Deploy Stage | Post-migration validation checklist for background services | Ensure all cron tasks are migrated to target cloud environments |
| At Runtime Stage | Centralized ACME clients (Cert-Manager) with 30/15/7-day alerts | Automatically renew certificates and notify engineers well before expiry |

---

## <img src="https://api.iconify.design/lucide:wrench.svg?color=%2364748b" width="18"/> Resolution

Carlos Ruiz identified that the renewal cron job was missing from the new infrastructure `[Slack:2025-06-01T00:10:00Z]`, initiated manual generation of a new SSL certificate via Let's Encrypt `[Slack:2025-06-01T00:15:00Z]`, deployed the certificate `[Slack:2025-06-01T00:40:00Z]`, and verified full service recovery after 46 minutes `[Slack:2025-06-01T00:46:00Z]`.

---

## <img src="https://api.iconify.design/lucide:check-square.svg?color=%2310b981" width="18"/> Action Items

| Priority | Type | Action | Owner | Est. |
|:---|:---|:---|:---|:---|
| **P0** | Prevent | Migrate all remaining local cron jobs to centralized Kubernetes CronJobs / Cert-Manager | Infrastructure Team | 2 days |
| **P1** | Detect | Implement proactive certificate expiration alerts at 30, 15, and 7 days via Prometheus | SRE Team | 3 days |
| **P2** | Mitigate | Update cloud migration runbooks to require explicit background service inventories | Platform Team | 1 week |

---

## <img src="https://api.iconify.design/lucide:book-open.svg?color=%236366f1" width="18"/> Lessons Learned

- Cloud migrations must inventory and migrate all background cron jobs and non-http processes, not just primary web servers.
- Centralized certificate management eliminates dependence on fragile host-level scripts.

## What Went Well

- External monitoring (UptimeRobot) and alerting triggered instantly at the moment of failure.
- On-call engineer rapidly diagnosed the orphaned cron job within 10 minutes of incident start.

## What Could Be Improved

- Absence of pre-expiry alerts allowed the certificate to expire silently without an early warning.
- Migration checklists lacked validation steps for recurring background tasks.