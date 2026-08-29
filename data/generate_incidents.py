"""
Synthetic incident data generator.

Creates 10 realistic incident scenarios with logs, Slack threads,
git commits, alerts, and ground truth for evaluation.
"""

import json
import os

INCIDENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "incidents")


def _write_incident(incident_id: str, data: dict) -> None:
    """Write incident data files to disk."""
    folder = os.path.join(INCIDENTS_DIR, incident_id)
    os.makedirs(folder, exist_ok=True)
    for filename, content in data.items():
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)


# ============================================================================
# Incident 01 — Database Connection Pool Exhaustion
# ============================================================================
INCIDENT_01 = {
    "metadata.json": {
        "incident_id": "INC-001",
        "title": "Database Connection Pool Exhaustion"
    },
    "logs.jsonl": [
        {"timestamp": "2025-03-15T14:00:12Z", "level": "INFO", "service": "api-gateway", "message": "Deploy v2.14.0 started", "metadata": {"deploy_id": "dep-8821"}},
        {"timestamp": "2025-03-15T14:02:45Z", "level": "INFO", "service": "api-gateway", "message": "Deploy v2.14.0 completed successfully", "metadata": {"deploy_id": "dep-8821"}},
        {"timestamp": "2025-03-15T14:15:33Z", "level": "WARN", "service": "user-service", "message": "Database connection pool usage at 75%", "metadata": {"pool_size": 50, "active": 38}},
        {"timestamp": "2025-03-15T14:22:18Z", "level": "WARN", "service": "user-service", "message": "Database connection pool usage at 85%", "metadata": {"pool_size": 50, "active": 43}},
        {"timestamp": "2025-03-15T14:28:05Z", "level": "ERROR", "service": "user-service", "message": "Database connection pool usage at 95%", "metadata": {"pool_size": 50, "active": 48}},
        {"timestamp": "2025-03-15T14:30:12Z", "level": "ERROR", "service": "user-service", "message": "Failed to acquire database connection: pool exhausted", "metadata": {"wait_time_ms": 30000}},
        {"timestamp": "2025-03-15T14:30:14Z", "level": "ERROR", "service": "api-gateway", "message": "HTTP 503 returned to client", "metadata": {"endpoint": "/api/users", "request_id": "req-a1b2c3"}},
        {"timestamp": "2025-03-15T14:30:45Z", "level": "ERROR", "service": "user-service", "message": "Failed to acquire database connection: pool exhausted", "metadata": {"wait_time_ms": 30000}},
        {"timestamp": "2025-03-15T14:31:02Z", "level": "ERROR", "service": "order-service", "message": "Upstream dependency user-service returning 503", "metadata": {"retry_count": 3}},
        {"timestamp": "2025-03-15T14:31:15Z", "level": "ERROR", "service": "api-gateway", "message": "HTTP 503 returned to client", "metadata": {"endpoint": "/api/orders", "request_id": "req-d4e5f6"}},
        {"timestamp": "2025-03-15T14:31:30Z", "level": "FATAL", "service": "user-service", "message": "Connection pool completely exhausted. All 50 connections in use, 127 requests waiting.", "metadata": {"pool_size": 50, "waiting": 127}},
        {"timestamp": "2025-03-15T14:32:00Z", "level": "ERROR", "service": "user-service", "message": "Database query timeout after 30s", "metadata": {"query": "SELECT * FROM users WHERE ...", "duration_ms": 30000}},
        {"timestamp": "2025-03-15T14:33:10Z", "level": "WARN", "service": "postgres", "message": "High number of idle connections detected", "metadata": {"idle_connections": 42, "active_connections": 8}},
        {"timestamp": "2025-03-15T14:45:00Z", "level": "INFO", "service": "user-service", "message": "Configuration hotfix applied: connection_timeout=5s, idle_timeout=60s", "metadata": {}},
        {"timestamp": "2025-03-15T14:47:30Z", "level": "INFO", "service": "user-service", "message": "Database connection pool usage normalized at 30%", "metadata": {"pool_size": 50, "active": 15}},
        {"timestamp": "2025-03-15T14:48:00Z", "level": "INFO", "service": "api-gateway", "message": "All endpoints returning 200", "metadata": {}}
    ],
    "slack_thread.json": [
        {"timestamp": "2025-03-15T14:29:00Z", "user": "AlertBot", "role": "Bot", "message": "🚨 ALERT: user-service error rate >5% — current: 12%. Dashboard: https://grafana.internal/d/user-svc"},
        {"timestamp": "2025-03-15T14:30:00Z", "user": "Sarah Chen", "role": "SRE On-Call", "message": "Ack. Looking at it now. Seeing a spike in 503s from user-service."},
        {"timestamp": "2025-03-15T14:31:00Z", "user": "Sarah Chen", "role": "SRE On-Call", "message": "DB connection pool is at 100%. All connections seem stuck. Checking what changed."},
        {"timestamp": "2025-03-15T14:32:00Z", "user": "Mike Torres", "role": "Backend Engineer", "message": "I deployed v2.14.0 about 30 minutes ago. It had a change to the user lookup query — added a JOIN to the preferences table."},
        {"timestamp": "2025-03-15T14:33:00Z", "user": "Sarah Chen", "role": "SRE On-Call", "message": "Found it. The deploy removed the connection timeout setting from the config. Connections are being acquired but never released when queries hang."},
        {"timestamp": "2025-03-15T14:34:00Z", "user": "Mike Torres", "role": "Backend Engineer", "message": "Oh no. I refactored the DB config module and the timeout wasn't in the new config schema. It was in a legacy block I removed."},
        {"timestamp": "2025-03-15T14:35:00Z", "user": "Sarah Chen", "role": "SRE On-Call", "message": "I'm going to hotfix the config to add connection_timeout=5s and idle_timeout=60s. Not rolling back the full deploy since the query change itself is fine."},
        {"timestamp": "2025-03-15T14:36:00Z", "user": "Priya Patel", "role": "Engineering Manager", "message": "Sounds good. Customer support is getting tickets. Can we get an ETA?"},
        {"timestamp": "2025-03-15T14:38:00Z", "user": "Sarah Chen", "role": "SRE On-Call", "message": "Hotfix deployed. Pool is draining. Should be back to normal in 2-3 minutes."},
        {"timestamp": "2025-03-15T14:42:00Z", "user": "Sarah Chen", "role": "SRE On-Call", "message": "Confirmed: error rate back to 0%. All endpoints healthy. Total impact was about 18 minutes."},
        {"timestamp": "2025-03-15T14:43:00Z", "user": "Priya Patel", "role": "Engineering Manager", "message": "Thanks everyone. Let's write up a post-mortem. We should add a config validation check in CI."}
    ],
    "git_commits.json": [
        {"sha": "a1b2c3d", "timestamp": "2025-03-15T11:30:00Z", "author": "Mike Torres", "message": "refactor: migrate DB config to new schema module", "files_changed": ["src/config/database.py", "src/config/schema.py"], "diff_summary": "Moved database configuration from legacy config block to new typed schema. Removed deprecated fields including connection pool settings that were in the legacy block."},
        {"sha": "e4f5g6h", "timestamp": "2025-03-15T12:15:00Z", "author": "Mike Torres", "message": "feat: add user preferences JOIN to lookup query", "files_changed": ["src/services/user_service.py", "src/models/user.py"], "diff_summary": "Added LEFT JOIN to user_preferences table in the main user lookup query. New query returns preferences alongside user data."},
        {"sha": "i7j8k9l", "timestamp": "2025-03-15T13:00:00Z", "author": "Mike Torres", "message": "test: update user service tests for preferences", "files_changed": ["tests/test_user_service.py"], "diff_summary": "Updated test fixtures and assertions for the new preferences JOIN."},
        {"sha": "m0n1o2p", "timestamp": "2025-03-15T13:45:00Z", "author": "CI Bot", "message": "chore: bump version to v2.14.0", "files_changed": ["version.txt"], "diff_summary": "Version bump for release."},
        {"sha": "q3r4s5t", "timestamp": "2025-03-15T14:45:00Z", "author": "Sarah Chen", "message": "hotfix: restore connection pool timeout settings", "files_changed": ["src/config/schema.py"], "diff_summary": "Added connection_timeout=5s and idle_timeout=60s to the new config schema. These were accidentally dropped during the config migration in a1b2c3d."}
    ],
    "alerts.json": [
        {"timestamp": "2025-03-15T14:28:30Z", "severity": "warning", "source": "Datadog", "title": "DB Connection Pool > 90%", "description": "user-service database connection pool utilization exceeded 90% threshold."},
        {"timestamp": "2025-03-15T14:30:15Z", "severity": "critical", "source": "PagerDuty", "title": "user-service Error Rate > 5%", "description": "Error rate for user-service has exceeded 5% for 2 consecutive minutes. Current: 12%."},
        {"timestamp": "2025-03-15T14:31:45Z", "severity": "critical", "source": "PagerDuty", "title": "order-service Degraded", "description": "order-service reporting upstream failures. Cascading impact detected."},
        {"timestamp": "2025-03-15T14:48:00Z", "severity": "info", "source": "PagerDuty", "title": "user-service Recovered", "description": "Error rate returned to normal levels."}
    ],
    "ground_truth.json": {
        "root_cause": "Database connection pool timeout settings were accidentally removed during a config schema migration in deploy v2.14.0. Without timeouts, connections acquired by slow queries were never released, causing pool exhaustion.",
        "root_cause_category": "configuration",
        "contributing_factors": [
            "The new config schema did not include connection pool timeout settings that existed in the legacy config block",
            "No config validation in CI to catch missing required database settings",
            "The new user preferences JOIN query was slower than the original, accelerating pool exhaustion",
            "No connection pool monitoring alert at lower thresholds (e.g. 50%) to provide earlier warning"
        ],
        "key_timeline_events": [
            {"timestamp": "2025-03-15T14:02:45Z", "description": "Deploy v2.14.0 completed — config migration removed timeout settings"},
            {"timestamp": "2025-03-15T14:15:33Z", "description": "Connection pool usage begins climbing (75%)"},
            {"timestamp": "2025-03-15T14:28:30Z", "description": "First alert: pool at 90%"},
            {"timestamp": "2025-03-15T14:30:12Z", "description": "Pool exhausted — first user-facing 503 errors"},
            {"timestamp": "2025-03-15T14:33:00Z", "description": "Root cause identified — missing timeout config"},
            {"timestamp": "2025-03-15T14:45:00Z", "description": "Hotfix deployed — timeouts restored"},
            {"timestamp": "2025-03-15T14:48:00Z", "description": "Full recovery confirmed"}
        ],
        "severity": "SEV2",
        "impact_summary": "18 minutes of degraded service. Users experienced 503 errors on user and order endpoints. Estimated ~2,000 failed requests.",
        "resolution": "Hotfix applied to restore connection_timeout=5s and idle_timeout=60s in the new config schema.",
        "duration_minutes": 18
    }
}

# ============================================================================
# Incident 02 — Memory Leak in Caching Layer
# ============================================================================
INCIDENT_02 = {
    "metadata.json": {
        "incident_id": "INC-002",
        "title": "Memory Leak in Caching Layer"
    },
    "logs.jsonl": [
        {"timestamp": "2025-04-02T08:00:00Z", "level": "INFO", "service": "product-service", "message": "Feature flag 'enable_extended_cache' toggled ON", "metadata": {"flag_id": "ff-2201"}},
        {"timestamp": "2025-04-02T10:30:00Z", "level": "INFO", "service": "product-service", "message": "Memory usage: 512MB / 2048MB", "metadata": {"heap_used_mb": 512}},
        {"timestamp": "2025-04-02T14:00:00Z", "level": "WARN", "service": "product-service", "message": "Memory usage: 1200MB / 2048MB", "metadata": {"heap_used_mb": 1200}},
        {"timestamp": "2025-04-02T16:30:00Z", "level": "WARN", "service": "product-service", "message": "Memory usage: 1650MB / 2048MB — GC pause 450ms", "metadata": {"heap_used_mb": 1650, "gc_pause_ms": 450}},
        {"timestamp": "2025-04-02T17:45:00Z", "level": "ERROR", "service": "product-service", "message": "Memory usage: 1900MB / 2048MB — GC unable to free sufficient memory", "metadata": {"heap_used_mb": 1900, "gc_freed_mb": 12}},
        {"timestamp": "2025-04-02T18:00:00Z", "level": "ERROR", "service": "product-service", "message": "Response latency degraded: p99 = 4200ms (normal: 200ms)", "metadata": {"p99_ms": 4200}},
        {"timestamp": "2025-04-02T18:10:00Z", "level": "FATAL", "service": "product-service", "message": "OutOfMemoryError: Java heap space", "metadata": {"heap_used_mb": 2048}},
        {"timestamp": "2025-04-02T18:10:05Z", "level": "INFO", "service": "kubernetes", "message": "Pod product-service-7b8d9f restarted (OOMKilled)", "metadata": {"restart_count": 1}},
        {"timestamp": "2025-04-02T18:15:00Z", "level": "INFO", "service": "product-service", "message": "Memory usage: 480MB / 2048MB (after restart)", "metadata": {"heap_used_mb": 480}},
        {"timestamp": "2025-04-02T18:45:00Z", "level": "WARN", "service": "product-service", "message": "Memory usage: 980MB / 2048MB (climbing again)", "metadata": {"heap_used_mb": 980}},
        {"timestamp": "2025-04-02T19:10:00Z", "level": "FATAL", "service": "product-service", "message": "OutOfMemoryError: Java heap space (second occurrence)", "metadata": {"heap_used_mb": 2048}},
        {"timestamp": "2025-04-02T19:10:05Z", "level": "INFO", "service": "kubernetes", "message": "Pod product-service-7b8d9f restarted (OOMKilled)", "metadata": {"restart_count": 2}},
        {"timestamp": "2025-04-02T19:30:00Z", "level": "INFO", "service": "product-service", "message": "Feature flag 'enable_extended_cache' toggled OFF", "metadata": {"flag_id": "ff-2201"}},
        {"timestamp": "2025-04-02T19:35:00Z", "level": "INFO", "service": "product-service", "message": "Cache cleared. Memory usage: 320MB / 2048MB", "metadata": {"heap_used_mb": 320}},
        {"timestamp": "2025-04-02T20:30:00Z", "level": "INFO", "service": "product-service", "message": "Memory usage stable: 350MB / 2048MB", "metadata": {"heap_used_mb": 350}}
    ],
    "slack_thread.json": [
        {"timestamp": "2025-04-02T18:05:00Z", "user": "AlertBot", "role": "Bot", "message": "🚨 ALERT: product-service p99 latency > 2000ms — current: 4200ms."},
        {"timestamp": "2025-04-02T18:08:00Z", "user": "James Kim", "role": "SRE On-Call", "message": "Looking at it. product-service memory is at 93%. Looks like it's about to OOM."},
        {"timestamp": "2025-04-02T18:11:00Z", "user": "AlertBot", "role": "Bot", "message": "🚨 ALERT: product-service pod restarted (OOMKilled)."},
        {"timestamp": "2025-04-02T18:12:00Z", "user": "James Kim", "role": "SRE On-Call", "message": "Pod restarted but memory is climbing fast again. Something is leaking. Checking recent changes."},
        {"timestamp": "2025-04-02T18:15:00Z", "user": "Lisa Wang", "role": "Backend Engineer", "message": "We enabled the 'extended_cache' feature flag this morning. It caches full product catalogs per-tenant. Could that be it?"},
        {"timestamp": "2025-04-02T18:18:00Z", "user": "James Kim", "role": "SRE On-Call", "message": "Heap dump shows the cache is holding ~1.4GB of ProductCatalog objects. There's no TTL or max-size set on the extended cache. It just grows unbounded."},
        {"timestamp": "2025-04-02T18:20:00Z", "user": "Lisa Wang", "role": "Backend Engineer", "message": "That's the bug. The regular cache has TTL and eviction. The extended cache was a quick prototype — eviction wasn't implemented yet."},
        {"timestamp": "2025-04-02T19:12:00Z", "user": "AlertBot", "role": "Bot", "message": "🚨 ALERT: product-service OOMKilled again (2nd time)."},
        {"timestamp": "2025-04-02T19:25:00Z", "user": "James Kim", "role": "SRE On-Call", "message": "Toggling the feature flag off now. That should stop the bleeding."},
        {"timestamp": "2025-04-02T19:35:00Z", "user": "James Kim", "role": "SRE On-Call", "message": "Flag is off, cache cleared. Memory stable at 320MB. Crisis over."},
        {"timestamp": "2025-04-02T19:40:00Z", "user": "Lisa Wang", "role": "Backend Engineer", "message": "I'll add TTL and max-size to the extended cache before we re-enable the flag. Should have done that from the start."}
    ],
    "git_commits.json": [
        {"sha": "f1a2b3c", "timestamp": "2025-03-28T10:00:00Z", "author": "Lisa Wang", "message": "feat: add extended product cache (behind feature flag)", "files_changed": ["src/cache/extended_cache.py", "src/services/product_service.py"], "diff_summary": "Added new ExtendedCache class that caches full ProductCatalog objects per tenant. No TTL or eviction policy implemented yet — marked as TODO. Gated behind 'enable_extended_cache' feature flag."},
        {"sha": "d4e5f6g", "timestamp": "2025-03-29T14:00:00Z", "author": "Lisa Wang", "message": "test: add basic tests for extended cache", "files_changed": ["tests/test_extended_cache.py"], "diff_summary": "Added unit tests for cache insertion and retrieval. No tests for eviction (not implemented)."},
        {"sha": "h7i8j9k", "timestamp": "2025-04-01T16:00:00Z", "author": "Priya Patel", "message": "chore: enable extended cache flag in staging", "files_changed": ["config/feature_flags.yaml"], "diff_summary": "Enabled enable_extended_cache in staging environment for testing."},
        {"sha": "l0m1n2o", "timestamp": "2025-04-02T07:55:00Z", "author": "Priya Patel", "message": "chore: enable extended cache flag in production", "files_changed": ["config/feature_flags.yaml"], "diff_summary": "Enabled enable_extended_cache in production after 1 day of staging without issues. Note: staging has fewer tenants so memory impact was minimal."}
    ],
    "alerts.json": [
        {"timestamp": "2025-04-02T17:50:00Z", "severity": "warning", "source": "Datadog", "title": "product-service Memory > 80%", "description": "Memory utilization at 82%. GC pause times increasing."},
        {"timestamp": "2025-04-02T18:02:00Z", "severity": "critical", "source": "PagerDuty", "title": "product-service Latency Degraded", "description": "p99 latency at 4200ms (threshold: 2000ms)."},
        {"timestamp": "2025-04-02T18:10:10Z", "severity": "critical", "source": "Kubernetes", "title": "Pod OOMKilled", "description": "product-service-7b8d9f terminated due to OOMKilled."},
        {"timestamp": "2025-04-02T19:10:10Z", "severity": "critical", "source": "Kubernetes", "title": "Pod OOMKilled (2nd)", "description": "product-service-7b8d9f terminated due to OOMKilled for the 2nd time in 1 hour."},
        {"timestamp": "2025-04-02T19:40:00Z", "severity": "info", "source": "PagerDuty", "title": "product-service Recovered", "description": "Memory and latency returned to normal after feature flag disabled."}
    ],
    "ground_truth.json": {
        "root_cause": "The 'enable_extended_cache' feature flag was enabled in production without eviction policies (TTL or max-size) on the extended cache. The cache grew unbounded, holding full ProductCatalog objects per tenant, until the service ran out of heap memory.",
        "root_cause_category": "code_bug",
        "contributing_factors": [
            "Extended cache was a prototype without TTL or eviction — marked as TODO but shipped anyway",
            "Feature flag was enabled in production after only 1 day in staging, which had fewer tenants and didn't surface the memory issue",
            "No memory growth rate alerting — only triggered at 80% threshold, too late for gradual leaks",
            "Kubernetes restart masked the problem temporarily, delaying diagnosis"
        ],
        "key_timeline_events": [
            {"timestamp": "2025-04-02T08:00:00Z", "description": "Feature flag enabled in production"},
            {"timestamp": "2025-04-02T14:00:00Z", "description": "Memory at 60% and climbing steadily"},
            {"timestamp": "2025-04-02T17:50:00Z", "description": "Memory alert triggered at 80%"},
            {"timestamp": "2025-04-02T18:10:00Z", "description": "First OOMKill"},
            {"timestamp": "2025-04-02T19:10:00Z", "description": "Second OOMKill — pattern confirmed"},
            {"timestamp": "2025-04-02T19:30:00Z", "description": "Feature flag disabled"},
            {"timestamp": "2025-04-02T19:35:00Z", "description": "Memory stabilized — incident resolved"}
        ],
        "severity": "SEV2",
        "impact_summary": "~90 minutes of degraded service with two complete outage periods during OOMKill restarts. Product catalog API returned errors or timed out. Estimated ~5,000 affected requests.",
        "resolution": "Disabled the 'enable_extended_cache' feature flag. Planned fix: add TTL and max-size eviction before re-enabling.",
        "duration_minutes": 90
    }
}


# ============================================================================
# Incident 03 — Cascading Microservice Failure
# ============================================================================
INCIDENT_03 = {
    "metadata.json": {
        "incident_id": "INC-003",
        "title": "Cascading Microservice Failure Due to Circuit Breaker Misconfiguration"
    },
    "logs.jsonl": [
        {"timestamp": "2025-05-10T09:00:00Z", "level": "INFO", "service": "payment-service", "message": "Deploy v3.2.0 completed — updated circuit breaker library to v2.0", "metadata": {"deploy_id": "dep-9102"}},
        {"timestamp": "2025-05-10T09:30:00Z", "level": "WARN", "service": "inventory-service", "message": "Experiencing intermittent database slowness", "metadata": {"avg_query_ms": 850}},
        {"timestamp": "2025-05-10T09:32:00Z", "level": "WARN", "service": "payment-service", "message": "Request to inventory-service timed out after 5000ms", "metadata": {"upstream": "inventory-service"}},
        {"timestamp": "2025-05-10T09:33:00Z", "level": "INFO", "service": "payment-service", "message": "Circuit breaker for inventory-service: CLOSED (1/10 failures)", "metadata": {"state": "CLOSED", "failure_count": 1, "threshold": 10}},
        {"timestamp": "2025-05-10T09:35:00Z", "level": "WARN", "service": "payment-service", "message": "Multiple timeouts to inventory-service", "metadata": {"failure_count": 5}},
        {"timestamp": "2025-05-10T09:38:00Z", "level": "ERROR", "service": "payment-service", "message": "Circuit breaker for inventory-service OPENED — but requests still being sent!", "metadata": {"state": "OPEN", "failure_count": 10, "bug": "v2.0 circuit breaker open state not blocking requests"}},
        {"timestamp": "2025-05-10T09:39:00Z", "level": "ERROR", "service": "payment-service", "message": "Thread pool exhausted — all 200 threads waiting on inventory-service responses", "metadata": {"active_threads": 200, "max_threads": 200}},
        {"timestamp": "2025-05-10T09:40:00Z", "level": "ERROR", "service": "checkout-service", "message": "payment-service returning 503 — cannot process checkouts", "metadata": {}},
        {"timestamp": "2025-05-10T09:40:30Z", "level": "ERROR", "service": "api-gateway", "message": "Multiple backend services degraded: payment-service, checkout-service", "metadata": {"degraded_services": ["payment-service", "checkout-service"]}},
        {"timestamp": "2025-05-10T09:41:00Z", "level": "ERROR", "service": "notification-service", "message": "Unable to send order confirmation emails — payment-service unavailable", "metadata": {}},
        {"timestamp": "2025-05-10T09:55:00Z", "level": "INFO", "service": "payment-service", "message": "Rollback to v3.1.9 initiated", "metadata": {"deploy_id": "dep-9103"}},
        {"timestamp": "2025-05-10T09:58:00Z", "level": "INFO", "service": "payment-service", "message": "Rollback complete. Circuit breaker v1.x restored.", "metadata": {}},
        {"timestamp": "2025-05-10T10:00:00Z", "level": "INFO", "service": "payment-service", "message": "Thread pool recovered. Requests flowing normally.", "metadata": {"active_threads": 25}},
        {"timestamp": "2025-05-10T10:02:00Z", "level": "INFO", "service": "inventory-service", "message": "Database performance recovered", "metadata": {"avg_query_ms": 45}},
        {"timestamp": "2025-05-10T10:05:00Z", "level": "INFO", "service": "api-gateway", "message": "All services healthy", "metadata": {}}
    ],
    "slack_thread.json": [
        {"timestamp": "2025-05-10T09:38:30Z", "user": "AlertBot", "role": "Bot", "message": "🚨 SEV1 ALERT: payment-service thread pool exhaustion. Checkout flow DOWN."},
        {"timestamp": "2025-05-10T09:39:00Z", "user": "Alex Rivera", "role": "SRE On-Call", "message": "This is bad. Payment is down. Checkout is cascading. Let me check what happened."},
        {"timestamp": "2025-05-10T09:40:00Z", "user": "Alex Rivera", "role": "SRE On-Call", "message": "inventory-service is slow (DB issues), and payment-service is piling up requests to it. Shouldn't the circuit breaker be catching this?"},
        {"timestamp": "2025-05-10T09:42:00Z", "user": "David Park", "role": "Backend Engineer", "message": "We upgraded the circuit breaker library to v2.0 this morning. Let me check if the config is compatible."},
        {"timestamp": "2025-05-10T09:44:00Z", "user": "David Park", "role": "Backend Engineer", "message": "Found it. The v2.0 library changed the config format. Our OPEN state handler isn't being registered — requests pass through even when the circuit is 'open'. It's a breaking change they didn't document well."},
        {"timestamp": "2025-05-10T09:46:00Z", "user": "Alex Rivera", "role": "SRE On-Call", "message": "Rolling back to v3.1.9 (circuit breaker v1.x). That's the fastest fix."},
        {"timestamp": "2025-05-10T09:50:00Z", "user": "Priya Patel", "role": "Engineering Manager", "message": "How many customers affected?"},
        {"timestamp": "2025-05-10T09:52:00Z", "user": "Alex Rivera", "role": "SRE On-Call", "message": "Looking at 22 minutes of zero checkout capability. Rough estimate: 3,000-5,000 failed checkout attempts."},
        {"timestamp": "2025-05-10T09:58:00Z", "user": "Alex Rivera", "role": "SRE On-Call", "message": "Rollback complete. Payment is processing. Checkout is back. Monitoring closely."},
        {"timestamp": "2025-05-10T10:05:00Z", "user": "Alex Rivera", "role": "SRE On-Call", "message": "All clear. inventory-service DB also recovered on its own — it was a transient slow query issue. The real problem was our broken circuit breaker."}
    ],
    "git_commits.json": [
        {"sha": "x1y2z3a", "timestamp": "2025-05-09T16:00:00Z", "author": "David Park", "message": "chore: upgrade circuit-breaker library from v1.8 to v2.0", "files_changed": ["requirements.txt", "src/resilience/circuit_breaker.py"], "diff_summary": "Updated circuit-breaker dependency to v2.0. Config format changed from dict-based to builder pattern. Adapted constructor but did not update the OPEN state fallback handler registration (breaking change in v2.0)."},
        {"sha": "b4c5d6e", "timestamp": "2025-05-09T17:00:00Z", "author": "David Park", "message": "test: update circuit breaker unit tests", "files_changed": ["tests/test_circuit_breaker.py"], "diff_summary": "Updated tests for new constructor. Tests check CLOSED→OPEN transition but don't verify that requests are actually blocked in OPEN state."},
        {"sha": "f7g8h9i", "timestamp": "2025-05-10T09:55:00Z", "author": "Alex Rivera", "message": "revert: rollback to circuit-breaker v1.8", "files_changed": ["requirements.txt", "src/resilience/circuit_breaker.py"], "diff_summary": "Reverted circuit breaker library to v1.8 and restored original config."}
    ],
    "alerts.json": [
        {"timestamp": "2025-05-10T09:35:00Z", "severity": "warning", "source": "Datadog", "title": "payment-service Timeout Rate Elevated", "description": "Timeout rate to inventory-service at 50%."},
        {"timestamp": "2025-05-10T09:38:30Z", "severity": "critical", "source": "PagerDuty", "title": "payment-service Thread Pool Exhausted", "description": "All 200 threads in use. Service unable to accept new requests."},
        {"timestamp": "2025-05-10T09:40:00Z", "severity": "critical", "source": "PagerDuty", "title": "Checkout Flow DOWN", "description": "checkout-service returning 503. Revenue impact."},
        {"timestamp": "2025-05-10T10:05:00Z", "severity": "info", "source": "PagerDuty", "title": "All Services Recovered", "description": "Payment, checkout, and notification services all healthy."}
    ],
    "ground_truth.json": {
        "root_cause": "The circuit breaker library was upgraded from v1.8 to v2.0 with a breaking configuration change. The v2.0 library required a new method to register the OPEN state fallback handler, but the existing config only adapted the constructor. As a result, when inventory-service became slow and the circuit opened, requests were not blocked — they continued to be sent, exhausting the payment-service thread pool and cascading to checkout and notification services.",
        "root_cause_category": "code_bug",
        "contributing_factors": [
            "Circuit breaker v2.0 had a breaking change in how OPEN state handlers are registered — poorly documented by the library",
            "Unit tests verified the CLOSED→OPEN transition but not that requests were actually blocked in OPEN state",
            "No integration test that simulated upstream failure and verified circuit breaker behavior end-to-end",
            "inventory-service had transient DB slowness that triggered the cascade — the original issue was minor but amplified by the broken circuit breaker",
            "Thread pool had no timeout on pending requests, allowing unbounded accumulation"
        ],
        "key_timeline_events": [
            {"timestamp": "2025-05-10T09:00:00Z", "description": "Deploy v3.2.0 with upgraded circuit breaker library"},
            {"timestamp": "2025-05-10T09:30:00Z", "description": "inventory-service starts experiencing DB slowness"},
            {"timestamp": "2025-05-10T09:38:00Z", "description": "Circuit breaker opens but fails to block requests — thread pool exhaustion"},
            {"timestamp": "2025-05-10T09:40:00Z", "description": "Cascade: checkout-service and notification-service go down"},
            {"timestamp": "2025-05-10T09:44:00Z", "description": "Root cause identified — broken circuit breaker config"},
            {"timestamp": "2025-05-10T09:58:00Z", "description": "Rollback complete — services recovering"},
            {"timestamp": "2025-05-10T10:05:00Z", "description": "Full recovery"}
        ],
        "severity": "SEV1",
        "impact_summary": "22 minutes of complete checkout outage. Payment, checkout, and notification services all degraded. Estimated 3,000-5,000 failed checkout attempts with direct revenue impact.",
        "resolution": "Rolled back payment-service to v3.1.9 with circuit breaker v1.8. inventory-service DB issue resolved independently.",
        "duration_minutes": 27
    }
}

# ============================================================================
# Incidents 04-10 — Remaining incidents (condensed for space)
# ============================================================================

INCIDENT_04 = {
    "metadata.json": {"incident_id": "INC-004", "title": "SSL Certificate Expiry"},
    "logs.jsonl": [
        {"timestamp": "2025-06-01T00:00:05Z", "level": "ERROR", "service": "nginx", "message": "SSL certificate for api.example.com has expired", "metadata": {"domain": "api.example.com", "expiry": "2025-06-01T00:00:00Z"}},
        {"timestamp": "2025-06-01T00:00:10Z", "level": "ERROR", "service": "nginx", "message": "TLS handshake failure — client connections rejected", "metadata": {"error": "certificate_expired"}},
        {"timestamp": "2025-06-01T00:01:00Z", "level": "ERROR", "service": "api-gateway", "message": "Upstream SSL error — all HTTPS traffic failing", "metadata": {}},
        {"timestamp": "2025-06-01T00:05:00Z", "level": "ERROR", "service": "mobile-app-backend", "message": "Certificate pinning failure — mobile clients unable to connect", "metadata": {}},
        {"timestamp": "2025-06-01T00:45:00Z", "level": "INFO", "service": "nginx", "message": "New SSL certificate installed for api.example.com", "metadata": {"new_expiry": "2026-06-01T00:00:00Z"}},
        {"timestamp": "2025-06-01T00:46:00Z", "level": "INFO", "service": "nginx", "message": "TLS handshakes succeeding — traffic restored", "metadata": {}}
    ],
    "slack_thread.json": [
        {"timestamp": "2025-06-01T00:02:00Z", "user": "AlertBot", "role": "Bot", "message": "🚨 CRITICAL: All HTTPS traffic to api.example.com failing. SSL certificate expired."},
        {"timestamp": "2025-06-01T00:05:00Z", "user": "Carlos Ruiz", "role": "SRE On-Call", "message": "Cert expired at midnight. Our auto-renewal cron job hasn't run. Checking why."},
        {"timestamp": "2025-06-01T00:10:00Z", "user": "Carlos Ruiz", "role": "SRE On-Call", "message": "Found it. The cert renewal cron was running on the old infra box that was decommissioned last month during the cloud migration. Nobody moved the cron to the new infra."},
        {"timestamp": "2025-06-01T00:15:00Z", "user": "Carlos Ruiz", "role": "SRE On-Call", "message": "Manually generating a new cert via Let's Encrypt now."},
        {"timestamp": "2025-06-01T00:40:00Z", "user": "Carlos Ruiz", "role": "SRE On-Call", "message": "New cert generated and deployed. Waiting for propagation."},
        {"timestamp": "2025-06-01T00:46:00Z", "user": "Carlos Ruiz", "role": "SRE On-Call", "message": "Traffic restored. Total downtime ~45 minutes. Need to set up cert renewal on the new infra and add expiry monitoring."}
    ],
    "git_commits.json": [
        {"sha": "ssl001", "timestamp": "2025-05-01T10:00:00Z", "author": "Ops Team", "message": "chore: decommission legacy infra servers", "files_changed": ["infra/servers.yaml"], "diff_summary": "Removed legacy-infra-01 through legacy-infra-05 from server inventory. Migrated services to cloud instances. Note: cron jobs on these servers were not audited before decommission."}
    ],
    "alerts.json": [
        {"timestamp": "2025-06-01T00:00:10Z", "severity": "critical", "source": "UptimeRobot", "title": "api.example.com DOWN", "description": "SSL handshake failure. Site unreachable via HTTPS."},
        {"timestamp": "2025-06-01T00:46:00Z", "severity": "info", "source": "UptimeRobot", "title": "api.example.com UP", "description": "Site responding normally."}
    ],
    "ground_truth.json": {
        "root_cause": "The SSL certificate auto-renewal cron job was running on a legacy infrastructure server that was decommissioned during a cloud migration. The cron was not migrated to the new infrastructure, so the certificate expired without renewal.",
        "root_cause_category": "infrastructure",
        "contributing_factors": [
            "No audit of cron jobs on legacy servers before decommission",
            "No certificate expiry monitoring/alerting (only caught when it actually expired)",
            "Cloud migration checklist did not include certificate management tasks"
        ],
        "key_timeline_events": [
            {"timestamp": "2025-06-01T00:00:00Z", "description": "SSL certificate expired"},
            {"timestamp": "2025-06-01T00:00:10Z", "description": "All HTTPS traffic begins failing"},
            {"timestamp": "2025-06-01T00:10:00Z", "description": "Root cause identified — renewal cron on decommissioned server"},
            {"timestamp": "2025-06-01T00:45:00Z", "description": "New certificate installed"},
            {"timestamp": "2025-06-01T00:46:00Z", "description": "Traffic restored"}
        ],
        "severity": "SEV1",
        "impact_summary": "45 minutes of complete API outage. All HTTPS traffic rejected. Mobile and web clients unable to connect. All downstream services affected.",
        "resolution": "Manually generated and installed new SSL certificate. Set up cert renewal on new infrastructure.",
        "duration_minutes": 46
    }
}

INCIDENT_05 = {
    "metadata.json": {"incident_id": "INC-005", "title": "DNS Resolution Failure After Provider Migration"},
    "logs.jsonl": [
        {"timestamp": "2025-06-15T03:00:00Z", "level": "INFO", "service": "infra", "message": "DNS provider migration from Route53 to CloudflareD NS started", "metadata": {}},
        {"timestamp": "2025-06-15T03:05:00Z", "level": "INFO", "service": "infra", "message": "NS records updated at registrar — propagation expected 24-48h", "metadata": {}},
        {"timestamp": "2025-06-15T06:00:00Z", "level": "ERROR", "service": "api-gateway", "message": "DNS resolution failure for internal-db.example.internal", "metadata": {"error": "NXDOMAIN"}},
        {"timestamp": "2025-06-15T06:00:30Z", "level": "ERROR", "service": "user-service", "message": "Cannot resolve internal-db.example.internal — falling back failed", "metadata": {}},
        {"timestamp": "2025-06-15T06:01:00Z", "level": "ERROR", "service": "order-service", "message": "DNS resolution failure for cache.example.internal", "metadata": {"error": "NXDOMAIN"}},
        {"timestamp": "2025-06-15T06:30:00Z", "level": "INFO", "service": "infra", "message": "Internal DNS zone example.internal added to Cloudflare", "metadata": {}},
        {"timestamp": "2025-06-15T06:35:00Z", "level": "INFO", "service": "api-gateway", "message": "DNS resolution restored for all internal domains", "metadata": {}}
    ],
    "slack_thread.json": [
        {"timestamp": "2025-06-15T06:01:00Z", "user": "AlertBot", "role": "Bot", "message": "🚨 CRITICAL: Multiple services reporting DNS resolution failures for internal domains."},
        {"timestamp": "2025-06-15T06:03:00Z", "user": "Nina Ivanova", "role": "SRE On-Call", "message": "All internal .example.internal domains are failing DNS resolution. External domains seem fine. Was there an infra change?"},
        {"timestamp": "2025-06-15T06:05:00Z", "user": "Tom Chen", "role": "Infrastructure Engineer", "message": "We started migrating DNS from Route53 to Cloudflare at 3 AM. External zones were migrated but I forgot to migrate the internal zone (example.internal). Route53 was the authoritative resolver for it."},
        {"timestamp": "2025-06-15T06:07:00Z", "user": "Nina Ivanova", "role": "SRE On-Call", "message": "So once the NS records propagated and traffic shifted to Cloudflare, internal DNS broke because the zone doesn't exist there yet?"},
        {"timestamp": "2025-06-15T06:08:00Z", "user": "Tom Chen", "role": "Infrastructure Engineer", "message": "Exactly. Adding the internal zone to Cloudflare now. Should be quick since it's a private zone."},
        {"timestamp": "2025-06-15T06:35:00Z", "user": "Tom Chen", "role": "Infrastructure Engineer", "message": "Internal zone is live on Cloudflare. All services should be resolving now."},
        {"timestamp": "2025-06-15T06:38:00Z", "user": "Nina Ivanova", "role": "SRE On-Call", "message": "Confirmed, all services healthy. ~35 minutes of internal DNS outage."}
    ],
    "git_commits.json": [
        {"sha": "dns001", "timestamp": "2025-06-14T16:00:00Z", "author": "Tom Chen", "message": "infra: prepare DNS migration to Cloudflare", "files_changed": ["infra/dns/migration_plan.md", "infra/dns/cloudflare_zones.tf"], "diff_summary": "Terraform config for Cloudflare DNS zones. Includes public zones (example.com, api.example.com) but missing internal zone (example.internal). Migration plan document also doesn't mention internal zones."}
    ],
    "alerts.json": [
        {"timestamp": "2025-06-15T06:00:10Z", "severity": "critical", "source": "PagerDuty", "title": "DNS Resolution Failures", "description": "Multiple services unable to resolve internal domain names."},
        {"timestamp": "2025-06-15T06:38:00Z", "severity": "info", "source": "PagerDuty", "title": "DNS Restored", "description": "All internal DNS resolution working."}
    ],
    "ground_truth.json": {
        "root_cause": "During DNS provider migration from Route53 to Cloudflare, the internal DNS zone (example.internal) was not included in the migration plan or Terraform configuration. When NS records propagated and traffic shifted to Cloudflare, internal domain resolution failed because the zone didn't exist on the new provider.",
        "root_cause_category": "infrastructure",
        "contributing_factors": [
            "Migration plan and Terraform config only covered public-facing DNS zones",
            "No pre-migration audit of all DNS zones, including private/internal zones",
            "Migration was started at 3 AM with limited oversight",
            "No DNS resolution health check that would have caught the issue before propagation completed"
        ],
        "key_timeline_events": [
            {"timestamp": "2025-06-15T03:00:00Z", "description": "DNS migration started"},
            {"timestamp": "2025-06-15T06:00:00Z", "description": "NS records propagate — internal DNS starts failing"},
            {"timestamp": "2025-06-15T06:05:00Z", "description": "Root cause identified — internal zone not migrated"},
            {"timestamp": "2025-06-15T06:30:00Z", "description": "Internal zone added to Cloudflare"},
            {"timestamp": "2025-06-15T06:35:00Z", "description": "Full recovery"}
        ],
        "severity": "SEV1",
        "impact_summary": "35 minutes of internal service communication failure. All services depending on internal DNS were affected. External-facing services partially degraded.",
        "resolution": "Added internal DNS zone (example.internal) to Cloudflare configuration.",
        "duration_minutes": 35
    }
}

INCIDENT_06 = {
    "metadata.json": {"incident_id": "INC-006", "title": "Race Condition in Payment Processing"},
    "logs.jsonl": [
        {"timestamp": "2025-07-20T11:00:00Z", "level": "INFO", "service": "payment-service", "message": "Flash sale event started — traffic surge expected", "metadata": {"event": "summer_flash_sale"}},
        {"timestamp": "2025-07-20T11:02:00Z", "level": "INFO", "service": "payment-service", "message": "Request rate: 450 req/s (normal: 50 req/s)", "metadata": {"rps": 450}},
        {"timestamp": "2025-07-20T11:05:00Z", "level": "ERROR", "service": "payment-service", "message": "Duplicate payment detected — order ORD-88421 charged twice", "metadata": {"order_id": "ORD-88421", "amount": 79.99, "charges": 2}},
        {"timestamp": "2025-07-20T11:06:00Z", "level": "ERROR", "service": "payment-service", "message": "Duplicate payment detected — order ORD-88435 charged twice", "metadata": {"order_id": "ORD-88435", "amount": 149.99, "charges": 2}},
        {"timestamp": "2025-07-20T11:08:00Z", "level": "ERROR", "service": "payment-service", "message": "Race condition: concurrent requests both passed idempotency check for ORD-88450", "metadata": {"order_id": "ORD-88450", "thread_1": "t-201", "thread_2": "t-204"}},
        {"timestamp": "2025-07-20T11:10:00Z", "level": "WARN", "service": "payment-service", "message": "32 duplicate charges detected in last 10 minutes", "metadata": {"duplicate_count": 32}},
        {"timestamp": "2025-07-20T11:15:00Z", "level": "INFO", "service": "payment-service", "message": "Emergency: idempotency enforcement switched to database-level UNIQUE constraint", "metadata": {}},
        {"timestamp": "2025-07-20T11:16:00Z", "level": "INFO", "service": "payment-service", "message": "Duplicate charges stopped. Beginning refund process for affected orders.", "metadata": {}}
    ],
    "slack_thread.json": [
        {"timestamp": "2025-07-20T11:06:30Z", "user": "AlertBot", "role": "Bot", "message": "🚨 ALERT: Duplicate payment charges detected. 5 orders double-charged in last 2 minutes."},
        {"timestamp": "2025-07-20T11:07:00Z", "user": "Sarah Chen", "role": "SRE On-Call", "message": "This is a payment issue during the flash sale. Duplicate charges are going out. Looking at payment-service now."},
        {"timestamp": "2025-07-20T11:08:00Z", "user": "Raj Kapoor", "role": "Backend Engineer", "message": "The idempotency check is application-level — it reads from the DB, checks if the order has been charged, then writes. Under high concurrency, two threads can both read 'not charged' before either writes."},
        {"timestamp": "2025-07-20T11:09:00Z", "user": "Sarah Chen", "role": "SRE On-Call", "message": "Classic TOCTOU race. How many customers affected so far?"},
        {"timestamp": "2025-07-20T11:10:30Z", "user": "Raj Kapoor", "role": "Backend Engineer", "message": "32 duplicate charges. Total overcharge ~$4,800. I can add a UNIQUE constraint on (order_id, charge_status) to the payments table as an immediate fix."},
        {"timestamp": "2025-07-20T11:12:00Z", "user": "Sarah Chen", "role": "SRE On-Call", "message": "Do it. We'll get ConflictErrors on the duplicates but that's better than double-charging."},
        {"timestamp": "2025-07-20T11:16:00Z", "user": "Raj Kapoor", "role": "Backend Engineer", "message": "UNIQUE constraint in place. No more duplicates. Starting automated refund for the 32 affected orders."},
        {"timestamp": "2025-07-20T11:30:00Z", "user": "Raj Kapoor", "role": "Backend Engineer", "message": "All 32 refunds processed. Customers notified via email."}
    ],
    "git_commits.json": [
        {"sha": "pay001", "timestamp": "2025-07-15T10:00:00Z", "author": "Raj Kapoor", "message": "feat: add application-level idempotency check for payments", "files_changed": ["src/services/payment_service.py"], "diff_summary": "Added idempotency check: read payment status from DB, skip if already charged. Uses SELECT then INSERT pattern without row-level locking."},
        {"sha": "pay002", "timestamp": "2025-07-20T11:14:00Z", "author": "Raj Kapoor", "message": "hotfix: add DB UNIQUE constraint for payment idempotency", "files_changed": ["migrations/add_payment_unique_constraint.sql", "src/services/payment_service.py"], "diff_summary": "Added UNIQUE constraint on (order_id, charge_status) to payments table. Updated payment service to handle ConflictError gracefully."}
    ],
    "alerts.json": [
        {"timestamp": "2025-07-20T11:06:00Z", "severity": "critical", "source": "Internal", "title": "Duplicate Payment Charges", "description": "Multiple orders charged twice. Financial impact detected."},
        {"timestamp": "2025-07-20T11:16:30Z", "severity": "info", "source": "Internal", "title": "Duplicate Charges Stopped", "description": "Database constraint preventing further duplicates. Refund process initiated."}
    ],
    "ground_truth.json": {
        "root_cause": "The payment idempotency check used a read-then-write pattern (SELECT then INSERT) without row-level locking. Under the high concurrency of the flash sale (~450 req/s vs normal 50 req/s), multiple threads could simultaneously read 'not charged' for the same order before any of them wrote the charge record, resulting in duplicate payments.",
        "root_cause_category": "code_bug",
        "contributing_factors": [
            "Application-level idempotency without database-level enforcement",
            "Flash sale caused 9x normal traffic, exposing the race condition",
            "No load testing of the payment path at flash-sale traffic levels",
            "Idempotency implementation was added recently without a concurrent-access test"
        ],
        "key_timeline_events": [
            {"timestamp": "2025-07-20T11:00:00Z", "description": "Flash sale started — traffic surges to 450 req/s"},
            {"timestamp": "2025-07-20T11:05:00Z", "description": "First duplicate charge detected"},
            {"timestamp": "2025-07-20T11:08:00Z", "description": "Race condition identified in idempotency check"},
            {"timestamp": "2025-07-20T11:15:00Z", "description": "Database UNIQUE constraint applied — duplicates stopped"},
            {"timestamp": "2025-07-20T11:30:00Z", "description": "All 32 refunds processed"}
        ],
        "severity": "SEV1",
        "impact_summary": "32 customers double-charged totaling ~$4,800. All refunds issued within 30 minutes. Reputational risk during high-visibility flash sale event.",
        "resolution": "Added database-level UNIQUE constraint on (order_id, charge_status) to enforce idempotency at the DB layer. Processed refunds for all affected orders.",
        "duration_minutes": 30
    }
}

INCIDENT_07 = {
    "metadata.json": {"incident_id": "INC-007", "title": "Disk Space Exhaustion From Disabled Log Rotation"},
    "logs.jsonl": [
        {"timestamp": "2025-08-05T02:00:00Z", "level": "INFO", "service": "data-pipeline", "message": "Config update applied: log_rotation_enabled=false (for debugging investigation)", "metadata": {}},
        {"timestamp": "2025-08-08T14:00:00Z", "level": "WARN", "service": "monitoring", "message": "Disk usage at 75% on data-pipeline-01", "metadata": {"disk_used_pct": 75}},
        {"timestamp": "2025-08-10T06:00:00Z", "level": "WARN", "service": "monitoring", "message": "Disk usage at 90% on data-pipeline-01", "metadata": {"disk_used_pct": 90}},
        {"timestamp": "2025-08-10T09:15:00Z", "level": "ERROR", "service": "data-pipeline", "message": "Write failed: No space left on device", "metadata": {"errno": "ENOSPC"}},
        {"timestamp": "2025-08-10T09:15:30Z", "level": "FATAL", "service": "data-pipeline", "message": "Pipeline halted — cannot write intermediate results to disk", "metadata": {}},
        {"timestamp": "2025-08-10T09:16:00Z", "level": "ERROR", "service": "data-pipeline", "message": "Downstream consumers stalled — no new data arriving", "metadata": {}},
        {"timestamp": "2025-08-10T09:45:00Z", "level": "INFO", "service": "data-pipeline", "message": "Old logs cleaned. Log rotation re-enabled. Disk usage at 35%.", "metadata": {"disk_used_pct": 35}},
        {"timestamp": "2025-08-10T09:50:00Z", "level": "INFO", "service": "data-pipeline", "message": "Pipeline resumed. Processing backlog.", "metadata": {}}
    ],
    "slack_thread.json": [
        {"timestamp": "2025-08-10T09:16:00Z", "user": "AlertBot", "role": "Bot", "message": "🚨 ALERT: data-pipeline-01 disk full. Pipeline halted."},
        {"timestamp": "2025-08-10T09:18:00Z", "user": "Maya Singh", "role": "Data Engineer", "message": "Checking. Disk is 100% full. /var/log/data-pipeline has 180GB of log files. That's a week of unrotated logs."},
        {"timestamp": "2025-08-10T09:20:00Z", "user": "Maya Singh", "role": "Data Engineer", "message": "Found it — log rotation was disabled on Aug 5 for a debugging investigation and never re-enabled. The config change was committed directly without a revert reminder."},
        {"timestamp": "2025-08-10T09:25:00Z", "user": "Maya Singh", "role": "Data Engineer", "message": "Cleaning old logs and re-enabling rotation. Should have the pipeline back in 20 minutes."},
        {"timestamp": "2025-08-10T09:50:00Z", "user": "Maya Singh", "role": "Data Engineer", "message": "Pipeline is back and processing the backlog. No data loss — just delayed processing."}
    ],
    "git_commits.json": [
        {"sha": "disk001", "timestamp": "2025-08-05T01:55:00Z", "author": "Maya Singh", "message": "debug: disable log rotation temporarily for investigation", "files_changed": ["config/data-pipeline.yaml"], "diff_summary": "Set log_rotation_enabled=false to preserve full logs during debug investigation of data corruption issue. TODO: re-enable after investigation."}
    ],
    "alerts.json": [
        {"timestamp": "2025-08-08T14:00:00Z", "severity": "warning", "source": "Datadog", "title": "Disk Usage > 75%", "description": "data-pipeline-01 disk at 75%."},
        {"timestamp": "2025-08-10T06:00:00Z", "severity": "warning", "source": "Datadog", "title": "Disk Usage > 90%", "description": "data-pipeline-01 disk at 90%."},
        {"timestamp": "2025-08-10T09:15:30Z", "severity": "critical", "source": "PagerDuty", "title": "data-pipeline Halted", "description": "No space left on device. Pipeline unable to write."},
        {"timestamp": "2025-08-10T09:50:00Z", "severity": "info", "source": "PagerDuty", "title": "data-pipeline Recovered", "description": "Pipeline resumed processing."}
    ],
    "ground_truth.json": {
        "root_cause": "Log rotation was disabled on the data pipeline server for a debugging investigation 5 days prior and never re-enabled. Logs accumulated to 180GB, filling the disk completely and halting the pipeline.",
        "root_cause_category": "configuration",
        "contributing_factors": [
            "Config change to disable log rotation was committed without a corresponding revert ticket or reminder",
            "Disk usage alerts at 75% and 90% were not acted upon — treated as non-urgent",
            "No automated policy to prevent log rotation from being disabled for more than 24 hours",
            "Debugging investigation concluded but the config revert was forgotten"
        ],
        "key_timeline_events": [
            {"timestamp": "2025-08-05T02:00:00Z", "description": "Log rotation disabled for debugging"},
            {"timestamp": "2025-08-08T14:00:00Z", "description": "75% disk warning — not acted on"},
            {"timestamp": "2025-08-10T06:00:00Z", "description": "90% disk warning — not acted on"},
            {"timestamp": "2025-08-10T09:15:00Z", "description": "Disk full — pipeline halts"},
            {"timestamp": "2025-08-10T09:45:00Z", "description": "Logs cleaned, rotation re-enabled"},
            {"timestamp": "2025-08-10T09:50:00Z", "description": "Pipeline resumed"}
        ],
        "severity": "SEV2",
        "impact_summary": "35 minutes of data pipeline downtime. No data loss, but downstream consumers experienced delayed data. Backlog processed within 2 hours.",
        "resolution": "Cleaned old log files and re-enabled log rotation. Added automated policy to prevent rotation from being disabled for >24 hours.",
        "duration_minutes": 35
    }
}

INCIDENT_08 = {
    "metadata.json": {"incident_id": "INC-008", "title": "Third-Party API Rate Limiting Cascade"},
    "logs.jsonl": [
        {"timestamp": "2025-08-20T10:00:00Z", "level": "INFO", "service": "marketing-service", "message": "Email campaign 'Summer Promo' launched — 50,000 recipients", "metadata": {"campaign_id": "camp-301"}},
        {"timestamp": "2025-08-20T10:05:00Z", "level": "WARN", "service": "email-service", "message": "SendGrid API rate limit warning: 80% of quota used", "metadata": {"quota_used_pct": 80}},
        {"timestamp": "2025-08-20T10:08:00Z", "level": "ERROR", "service": "email-service", "message": "SendGrid API 429 Too Many Requests", "metadata": {"retry_after_seconds": 60}},
        {"timestamp": "2025-08-20T10:08:30Z", "level": "ERROR", "service": "email-service", "message": "Email queue growing — 12,000 emails pending", "metadata": {"queue_size": 12000}},
        {"timestamp": "2025-08-20T10:10:00Z", "level": "ERROR", "service": "notification-service", "message": "Unable to send transactional emails (password resets, order confirmations) — email-service queue saturated", "metadata": {}},
        {"timestamp": "2025-08-20T10:12:00Z", "level": "WARN", "service": "email-service", "message": "Memory usage high due to queued messages: 1.8GB", "metadata": {"queue_size": 25000}},
        {"timestamp": "2025-08-20T10:30:00Z", "level": "INFO", "service": "email-service", "message": "Campaign emails deprioritized. Transactional emails given dedicated queue.", "metadata": {}},
        {"timestamp": "2025-08-20T10:35:00Z", "level": "INFO", "service": "email-service", "message": "Transactional emails flowing normally. Campaign emails throttled to 100/min.", "metadata": {}}
    ],
    "slack_thread.json": [
        {"timestamp": "2025-08-20T10:09:00Z", "user": "AlertBot", "role": "Bot", "message": "🚨 ALERT: email-service queue depth > 10,000. SendGrid rate limited."},
        {"timestamp": "2025-08-20T10:10:00Z", "user": "Kim Park", "role": "SRE On-Call", "message": "SendGrid is rate-limiting us. Marketing launched a 50K email campaign and it's eating our entire API quota. Transactional emails are blocked too."},
        {"timestamp": "2025-08-20T10:12:00Z", "user": "Amy Liu", "role": "Marketing Ops", "message": "We didn't know there was a shared quota. We've always used the same email endpoint for campaigns."},
        {"timestamp": "2025-08-20T10:15:00Z", "user": "Kim Park", "role": "SRE On-Call", "message": "The issue is we have one email queue for everything — campaigns and transactional. When campaign volume spikes, transactional gets crowded out. I'm splitting the queues now."},
        {"timestamp": "2025-08-20T10:35:00Z", "user": "Kim Park", "role": "SRE On-Call", "message": "Transactional queue is separate now with reserved capacity. Campaign emails throttled. Password resets and order confirmations flowing again."}
    ],
    "git_commits.json": [
        {"sha": "rate001", "timestamp": "2025-08-20T10:25:00Z", "author": "Kim Park", "message": "hotfix: split email queues — dedicated transactional queue", "files_changed": ["src/services/email_service.py", "config/email_queues.yaml"], "diff_summary": "Created separate queues for transactional and marketing emails. Transactional queue gets priority and reserved SendGrid quota. Marketing queue throttled to 100/min."}
    ],
    "alerts.json": [
        {"timestamp": "2025-08-20T10:05:00Z", "severity": "warning", "source": "Datadog", "title": "SendGrid Quota > 80%", "description": "Email sending quota at 80% utilization."},
        {"timestamp": "2025-08-20T10:08:00Z", "severity": "critical", "source": "PagerDuty", "title": "SendGrid Rate Limited", "description": "All email sending blocked. HTTP 429 responses."},
        {"timestamp": "2025-08-20T10:35:00Z", "severity": "info", "source": "PagerDuty", "title": "Email Service Recovered", "description": "Transactional emails flowing. Campaign emails throttled."}
    ],
    "ground_truth.json": {
        "root_cause": "A 50,000-recipient marketing email campaign consumed the entire shared SendGrid API quota, rate-limiting all email sending including critical transactional emails (password resets, order confirmations). There was no separation between campaign and transactional email queues.",
        "root_cause_category": "architecture",
        "contributing_factors": [
            "Single email queue shared between marketing campaigns and transactional emails",
            "No rate limiting or throttling on campaign email sending",
            "Marketing team unaware of shared API quota — no coordination process for large campaigns",
            "No priority system to protect transactional emails during high-volume sends"
        ],
        "key_timeline_events": [
            {"timestamp": "2025-08-20T10:00:00Z", "description": "50K email campaign launched"},
            {"timestamp": "2025-08-20T10:08:00Z", "description": "SendGrid rate limit hit — all emails blocked"},
            {"timestamp": "2025-08-20T10:10:00Z", "description": "Transactional emails (password resets, order confirmations) blocked"},
            {"timestamp": "2025-08-20T10:30:00Z", "description": "Queue split implemented — transactional emails prioritized"},
            {"timestamp": "2025-08-20T10:35:00Z", "description": "Transactional emails restored"}
        ],
        "severity": "SEV2",
        "impact_summary": "27 minutes where no emails could be sent. Critical transactional emails (password resets, order confirmations) delayed. Campaign emails throttled to 100/min.",
        "resolution": "Split email queues — dedicated transactional queue with reserved capacity. Campaign queue throttled.",
        "duration_minutes": 27
    }
}

INCIDENT_09 = {
    "metadata.json": {"incident_id": "INC-009", "title": "Kubernetes Pod Crash Loop From Bad Health Check"},
    "logs.jsonl": [
        {"timestamp": "2025-09-01T14:00:00Z", "level": "INFO", "service": "auth-service", "message": "Deploy v4.1.0 started — added new /healthz endpoint", "metadata": {"deploy_id": "dep-1201"}},
        {"timestamp": "2025-09-01T14:02:00Z", "level": "INFO", "service": "auth-service", "message": "v4.1.0 deployed. New liveness probe: /healthz (checks DB connectivity)", "metadata": {}},
        {"timestamp": "2025-09-01T14:02:30Z", "level": "INFO", "service": "auth-service", "message": "Service started. Warming up caches and DB connections...", "metadata": {}},
        {"timestamp": "2025-09-01T14:02:35Z", "level": "ERROR", "service": "kubernetes", "message": "Liveness probe failed: /healthz returned 503 (DB connection not ready)", "metadata": {"pod": "auth-service-5f8d2a", "probe_type": "liveness"}},
        {"timestamp": "2025-09-01T14:02:50Z", "level": "ERROR", "service": "kubernetes", "message": "Liveness probe failed 3 times — restarting pod", "metadata": {"pod": "auth-service-5f8d2a", "restart_count": 1}},
        {"timestamp": "2025-09-01T14:03:10Z", "level": "ERROR", "service": "kubernetes", "message": "Pod restarted. Liveness probe failing again during startup.", "metadata": {"restart_count": 2}},
        {"timestamp": "2025-09-01T14:04:00Z", "level": "ERROR", "service": "kubernetes", "message": "CrashLoopBackOff: auth-service-5f8d2a", "metadata": {"restart_count": 4, "back_off_seconds": 40}},
        {"timestamp": "2025-09-01T14:04:30Z", "level": "ERROR", "service": "api-gateway", "message": "No healthy auth-service pods available — authentication failing", "metadata": {}},
        {"timestamp": "2025-09-01T14:15:00Z", "level": "INFO", "service": "auth-service", "message": "Liveness probe updated: initialDelaySeconds=30, /healthz only checks process alive", "metadata": {}},
        {"timestamp": "2025-09-01T14:16:00Z", "level": "INFO", "service": "kubernetes", "message": "auth-service pods healthy and serving traffic", "metadata": {}}
    ],
    "slack_thread.json": [
        {"timestamp": "2025-09-01T14:04:00Z", "user": "AlertBot", "role": "Bot", "message": "🚨 ALERT: auth-service in CrashLoopBackOff. Authentication unavailable."},
        {"timestamp": "2025-09-01T14:05:00Z", "user": "Carlos Ruiz", "role": "SRE On-Call", "message": "Auth is down. Pods are crash-looping. Let me check what deployed."},
        {"timestamp": "2025-09-01T14:06:00Z", "user": "Carlos Ruiz", "role": "SRE On-Call", "message": "v4.1.0 added a new /healthz endpoint that checks DB connectivity. But the liveness probe has no initialDelaySeconds — it starts checking immediately on pod start, before the DB connection pool is ready."},
        {"timestamp": "2025-09-01T14:07:00Z", "user": "Emma Watson", "role": "Backend Engineer", "message": "That's my bad. I set up /healthz to check DB as a liveness probe. It should be a readiness probe. Liveness should only check if the process is alive."},
        {"timestamp": "2025-09-01T14:08:00Z", "user": "Carlos Ruiz", "role": "SRE On-Call", "message": "Fixing now. Changing liveness to simple process check, adding initialDelaySeconds=30, and moving DB check to readiness probe."},
        {"timestamp": "2025-09-01T14:16:00Z", "user": "Carlos Ruiz", "role": "SRE On-Call", "message": "Fixed. Auth pods are stable. All authentication working again. Total downtime: ~12 minutes."}
    ],
    "git_commits.json": [
        {"sha": "k8s001", "timestamp": "2025-09-01T13:30:00Z", "author": "Emma Watson", "message": "feat: add /healthz endpoint with DB connectivity check", "files_changed": ["src/api/health.py", "k8s/deployment.yaml"], "diff_summary": "Added /healthz endpoint that checks DB connection. Configured as liveness probe in Kubernetes deployment. No initialDelaySeconds. No separate readiness probe."},
        {"sha": "k8s002", "timestamp": "2025-09-01T14:12:00Z", "author": "Carlos Ruiz", "message": "hotfix: fix health check configuration", "files_changed": ["src/api/health.py", "k8s/deployment.yaml"], "diff_summary": "Liveness probe now checks only process alive status. Readiness probe checks DB connectivity. Added initialDelaySeconds=30 to liveness probe."}
    ],
    "alerts.json": [
        {"timestamp": "2025-09-01T14:03:00Z", "severity": "critical", "source": "Kubernetes", "title": "CrashLoopBackOff: auth-service", "description": "Pod restarting repeatedly. Liveness probe failing."},
        {"timestamp": "2025-09-01T14:04:30Z", "severity": "critical", "source": "PagerDuty", "title": "Authentication Unavailable", "description": "No healthy auth-service pods. All login and auth requests failing."},
        {"timestamp": "2025-09-01T14:16:30Z", "severity": "info", "source": "PagerDuty", "title": "auth-service Recovered", "description": "Pods healthy. Authentication working."}
    ],
    "ground_truth.json": {
        "root_cause": "The new /healthz endpoint performed a database connectivity check and was configured as the Kubernetes liveness probe without an initialDelaySeconds. The DB connection pool takes ~15 seconds to initialize, but the liveness probe started checking immediately on pod start, failed 3 times, and Kubernetes restarted the pod — creating a CrashLoopBackOff since the pod could never pass the liveness check during startup.",
        "root_cause_category": "configuration",
        "contributing_factors": [
            "DB connectivity check was used as liveness probe instead of readiness probe",
            "No initialDelaySeconds configured on the liveness probe",
            "No Kubernetes health check review process for new deployments",
            "Staging environment had faster DB startup so the issue didn't surface there"
        ],
        "key_timeline_events": [
            {"timestamp": "2025-09-01T14:00:00Z", "description": "Deploy v4.1.0 with new health check"},
            {"timestamp": "2025-09-01T14:02:35Z", "description": "Liveness probe fails — DB not ready during startup"},
            {"timestamp": "2025-09-01T14:04:00Z", "description": "CrashLoopBackOff — authentication unavailable"},
            {"timestamp": "2025-09-01T14:06:00Z", "description": "Root cause identified"},
            {"timestamp": "2025-09-01T14:15:00Z", "description": "Hotfix deployed — proper probe configuration"},
            {"timestamp": "2025-09-01T14:16:00Z", "description": "Auth service recovered"}
        ],
        "severity": "SEV1",
        "impact_summary": "12 minutes of complete authentication outage. No users could log in or authenticate API requests. All authenticated endpoints affected.",
        "resolution": "Changed liveness probe to simple process check, moved DB check to readiness probe, added initialDelaySeconds=30.",
        "duration_minutes": 12
    }
}

INCIDENT_10 = {
    "metadata.json": {"incident_id": "INC-010", "title": "Data Pipeline Corruption From Out-of-Order Schema Migration"},
    "logs.jsonl": [
        {"timestamp": "2025-09-15T03:00:00Z", "level": "INFO", "service": "migration-runner", "message": "Running pending migrations: migration_042_add_status_column, migration_043_backfill_status", "metadata": {}},
        {"timestamp": "2025-09-15T03:00:30Z", "level": "INFO", "service": "migration-runner", "message": "migration_042 completed: added 'status' column with DEFAULT NULL", "metadata": {}},
        {"timestamp": "2025-09-15T03:01:00Z", "level": "ERROR", "service": "migration-runner", "message": "migration_043 failed: cannot backfill — references migration_044 function that doesn't exist yet", "metadata": {"error": "function compute_status() does not exist"}},
        {"timestamp": "2025-09-15T03:01:05Z", "level": "WARN", "service": "migration-runner", "message": "migration_043 rolled back. migration_042 committed (status column exists but is empty).", "metadata": {}},
        {"timestamp": "2025-09-15T06:00:00Z", "level": "ERROR", "service": "data-pipeline", "message": "ETL job failed: NOT NULL constraint violation on 'status' column in analytics table", "metadata": {"table": "order_analytics"}},
        {"timestamp": "2025-09-15T06:01:00Z", "level": "ERROR", "service": "data-pipeline", "message": "Pipeline writing NULL status values. Downstream analytics dashboards showing blank data.", "metadata": {}},
        {"timestamp": "2025-09-15T06:30:00Z", "level": "ERROR", "service": "reporting-service", "message": "Daily report generation failed: division by zero — status counts are all NULL", "metadata": {}},
        {"timestamp": "2025-09-15T08:00:00Z", "level": "INFO", "service": "migration-runner", "message": "migration_044 (compute_status function) manually applied", "metadata": {}},
        {"timestamp": "2025-09-15T08:05:00Z", "level": "INFO", "service": "migration-runner", "message": "migration_043 (backfill) re-run successfully — all status values populated", "metadata": {}},
        {"timestamp": "2025-09-15T08:10:00Z", "level": "INFO", "service": "data-pipeline", "message": "Pipeline re-run. All data consistent.", "metadata": {}}
    ],
    "slack_thread.json": [
        {"timestamp": "2025-09-15T06:05:00Z", "user": "AlertBot", "role": "Bot", "message": "🚨 ALERT: data-pipeline ETL job failed. order_analytics table has NULL constraint violations."},
        {"timestamp": "2025-09-15T06:10:00Z", "user": "Maya Singh", "role": "Data Engineer", "message": "The 'status' column was added by last night's migration but it's all NULLs. The backfill migration failed. Checking why."},
        {"timestamp": "2025-09-15T06:15:00Z", "user": "Maya Singh", "role": "Data Engineer", "message": "migration_043 (backfill) depends on a function defined in migration_044, but migrations run in order. 043 ran first, couldn't find the function, and failed. 042 (add column) had already committed, so we have the column with no data."},
        {"timestamp": "2025-09-15T06:20:00Z", "user": "Jake Brown", "role": "Backend Engineer", "message": "That's my fault. I split the original migration into 3 parts but numbered them wrong. 044 should have been 043 and vice versa."},
        {"timestamp": "2025-09-15T06:25:00Z", "user": "Maya Singh", "role": "Data Engineer", "message": "OK. The fix is to manually run 044 first, then re-run 043. But we also need to re-run the ETL pipeline to fix the analytics data."},
        {"timestamp": "2025-09-15T08:10:00Z", "user": "Maya Singh", "role": "Data Engineer", "message": "All fixed. Migrations complete, pipeline re-run, analytics data is clean. Dashboards look normal now."}
    ],
    "git_commits.json": [
        {"sha": "mig001", "timestamp": "2025-09-14T15:00:00Z", "author": "Jake Brown", "message": "feat: add order status tracking — schema migrations", "files_changed": ["migrations/042_add_status_column.sql", "migrations/043_backfill_status.sql", "migrations/044_compute_status_function.sql"], "diff_summary": "Three migrations: 042 adds status column, 043 backfills existing rows using compute_status(), 044 creates the compute_status() function. BUG: 043 references function from 044 but runs before it."}
    ],
    "alerts.json": [
        {"timestamp": "2025-09-15T06:00:30Z", "severity": "critical", "source": "PagerDuty", "title": "ETL Pipeline Failed", "description": "order_analytics pipeline failing on NULL constraint violations."},
        {"timestamp": "2025-09-15T06:30:30Z", "severity": "warning", "source": "Datadog", "title": "Daily Reports Failed", "description": "Reporting service unable to generate daily reports."},
        {"timestamp": "2025-09-15T08:10:00Z", "severity": "info", "source": "PagerDuty", "title": "Pipeline Recovered", "description": "Data pipeline and reports running successfully."}
    ],
    "ground_truth.json": {
        "root_cause": "Schema migrations were numbered in the wrong order. Migration 043 (backfill status values) depended on a function defined in migration 044 (compute_status), but migrations run sequentially by number. Migration 043 failed because the function didn't exist yet, leaving the status column populated with NULL values and corrupting downstream analytics.",
        "root_cause_category": "code_bug",
        "contributing_factors": [
            "Migrations were split into 3 parts but numbered incorrectly — dependency ordering was wrong",
            "Migration 042 committed independently, so the column existed without data even after 043 failed",
            "No migration dependency validation in the migration runner",
            "No dry-run or staging test of the migration sequence before production"
        ],
        "key_timeline_events": [
            {"timestamp": "2025-09-15T03:00:00Z", "description": "Migrations run — 042 succeeds, 043 fails due to missing function"},
            {"timestamp": "2025-09-15T06:00:00Z", "description": "ETL pipeline fails on NULL status values"},
            {"timestamp": "2025-09-15T06:15:00Z", "description": "Root cause identified — migration ordering bug"},
            {"timestamp": "2025-09-15T08:00:00Z", "description": "Migrations manually reordered and re-run"},
            {"timestamp": "2025-09-15T08:10:00Z", "description": "Data pipeline and dashboards recovered"}
        ],
        "severity": "SEV2",
        "impact_summary": "~5 hours of corrupted analytics data. Daily reports failed. Analytics dashboards showed blank/incorrect data. Data pipeline was re-run to fix.",
        "resolution": "Manually ran migration 044 first, then re-ran 043. Re-ran ETL pipeline to fix analytics data.",
        "duration_minutes": 310
    }
}


ALL_INCIDENTS = {
    "incident_01_db_connection_pool": INCIDENT_01,
    "incident_02_memory_leak": INCIDENT_02,
    "incident_03_cascading_failure": INCIDENT_03,
    "incident_04_ssl_cert_expiry": INCIDENT_04,
    "incident_05_dns_failure": INCIDENT_05,
    "incident_06_race_condition": INCIDENT_06,
    "incident_07_disk_exhaustion": INCIDENT_07,
    "incident_08_rate_limiting": INCIDENT_08,
    "incident_09_crash_loop": INCIDENT_09,
    "incident_10_schema_migration": INCIDENT_10,
}


def generate_all() -> None:
    """Write all synthetic incidents to disk."""
    for name, data in ALL_INCIDENTS.items():
        _write_incident(name, data)
        print(f"  [OK] Generated {name}")


if __name__ == "__main__":
    print("Generating synthetic incident data...")
    generate_all()
    print(f"\nDone! {len(ALL_INCIDENTS)} incidents written to {INCIDENTS_DIR}")
