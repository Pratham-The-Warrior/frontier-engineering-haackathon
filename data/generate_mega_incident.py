"""
Mega Scenario Generator — High-Fidelity Distributed Production Outage.

Generates Incident 11:
'Global Payment Processing Outage & Cascading Kafka Partition Starvation'
Spanning:
- 1,000+ realistic logs across 5 microservices with embedded secrets & database URIs
- 30+ Slack war-room triage messages with emoji reactions and competing hypotheses
- Multi-commit Git diffs with PR reviews, CI check-runs, and Jira ticket refs
- Tier-1 Cascading PagerDuty alerts
- Rich Jira incident and infrastructure tickets with Atlassian Document Format (ADF)
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta, timezone


INCIDENT_DIR = os.path.join(os.path.dirname(__file__), "incidents", "incident_11_mega_payment_outage")


def generate_mega_incident():
    os.makedirs(INCIDENT_DIR, exist_ok=True)
    base_time = datetime(2025, 4, 18, 14, 0, 0, tzinfo=timezone.utc)

    # -----------------------------------------------------------------------
    # 1. Metadata
    # -----------------------------------------------------------------------
    metadata = {
        "incident_id": "INC-011",
        "title": "Global Payment Outage & Cascading Kafka Partition Starvation",
        "severity": "P1-CRITICAL",
        "service": "payment-gateway",
        "incident_commander": "Sarah Chen",
        "start_time": (base_time + timedelta(minutes=15)).isoformat().replace("+00:00", "Z"),
        "end_time": (base_time + timedelta(minutes=75)).isoformat().replace("+00:00", "Z"),
        "affected_services": ["payment-gateway", "kafka-consumer", "postgres-db", "auth-service", "order-service"],
        "customer_impact": "68,000 checkout transactions failed (HTTP 504 / 500) over 60 minutes. Estimated revenue loss: $420,000.",
    }
    with open(os.path.join(INCIDENT_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # -----------------------------------------------------------------------
    # 2. Git Commits & PR Diffs
    # -----------------------------------------------------------------------
    commits = [
        {
            "sha": "a1c2e3f",
            "full_sha": "a1c2e3f4b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
            "timestamp": (base_time - timedelta(hours=3)).isoformat().replace("+00:00", "Z"),
            "author": "Elena Rostova",
            "author_email": "elena.r@company.com",
            "message": "PAY-8900: Add read replica routing for historical payment lookups",
            "files_changed": ["src/db/replica_router.py", "tests/test_replica.py"],
            "ticket_refs": ["PAY-8900"],
            "diff_summary": "Changed 2 files (+45/-10): Added read replica pool configuration.",
        },
        {
            "sha": "f8a9b1c",
            "full_sha": "f8a9b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8",
            "timestamp": (base_time + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            "author": "Dave Kumar",
            "author_email": "dave.k@company.com",
            "message": "PAY-9042: Optimize payment consumer throughput by increasing batch size to 5000 (#142)",
            "files_changed": ["src/kafka/consumer_config.py", "src/payment/processor.py"],
            "ticket_refs": ["PAY-9042", "INFRA-819"],
            "diff_summary": "Changed 2 files (+12/-4): Set max.poll.records=5000 and max.poll.interval.ms=300000 without heartbeat guard.",
        },
        {
            "sha": "c4d5e6f",
            "full_sha": "c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3",
            "timestamp": (base_time + timedelta(minutes=45)).isoformat().replace("+00:00", "Z"),
            "author": "Marcus Wright",
            "author_email": "marcus.w@company.com",
            "message": "INFRA-819: Diagnostic commit - Enable debug logging on Kafka rebalance listeners",
            "files_changed": ["config/logging.yaml"],
            "ticket_refs": ["INFRA-819"],
            "diff_summary": "Changed 1 file (+3/-1): Set org.apache.kafka log level to DEBUG.",
        },
        {
            "sha": "d3e2a1b",
            "full_sha": "d3e2a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8",
            "timestamp": (base_time + timedelta(minutes=65)).isoformat().replace("+00:00", "Z"),
            "author": "Dave Kumar",
            "author_email": "dave.k@company.com",
            "message": "PAY-9042: Hotfix - Revert consumer batch size to 100 and enforce 10s heartbeat guard (#143)",
            "files_changed": ["src/kafka/consumer_config.py"],
            "ticket_refs": ["PAY-9042"],
            "diff_summary": "Changed 1 file (+5/-3): Restored safe Kafka consumer batch size and heartbeat intervals.",
        },
    ]
    with open(os.path.join(INCIDENT_DIR, "git_commits.json"), "w", encoding="utf-8") as f:
        json.dump(commits, f, indent=2)

    # -----------------------------------------------------------------------
    # 3. Slack War-Room Thread (30+ Messages with reactions & triage debate)
    # -----------------------------------------------------------------------
    slack_messages = [
        {
            "timestamp": (base_time + timedelta(minutes=16)).isoformat().replace("+00:00", "Z"),
            "user": "Sarah Chen",
            "role": "Incident Commander / Staff SRE",
            "message": "<!channel> P1 incident declared: elevated 504 Gateway Timeouts on /v2/payments/charge. Opening war-room.",
            "reactions": {"eyes": 6, "rotating_light": 4},
        },
        {
            "timestamp": (base_time + timedelta(minutes=18)).isoformat().replace("+00:00", "Z"),
            "user": "Marcus Wright",
            "role": "Payment Backend Lead",
            "message": "Payment gateway p99 latency spiked from 120ms to 24,000ms. Transactions are backing up in the ingest queue.",
            "reactions": {"warning": 3},
        },
        {
            "timestamp": (base_time + timedelta(minutes=20)).isoformat().replace("+00:00", "Z"),
            "user": "Elena Rostova",
            "role": "Database SRE",
            "message": "Postgres connection pool is 98% saturated. Seeing `DeadlockDetected` on table `payment_transactions` across all 3 primary shards.",
            "reactions": {"astonished": 2},
        },
        {
            "timestamp": (base_time + timedelta(minutes=22)).isoformat().replace("+00:00", "Z"),
            "user": "Dave Kumar",
            "role": "Data & Messaging Lead",
            "message": "Could this be the read-replica routing PR from 3 hours ago by @Elena Rostova? Maybe queries are locking master?",
            "reactions": {"thinking_face": 3},
        },
        {
            "timestamp": (base_time + timedelta(minutes=25)).isoformat().replace("+00:00", "Z"),
            "user": "Elena Rostova",
            "role": "Database SRE",
            "message": "Checked replica metrics — replica traffic is healthy. The master DB locks are holding uncommitted transaction blocks for > 4 minutes.",
            "reactions": {"white_check_mark": 4},
        },
        {
            "timestamp": (base_time + timedelta(minutes=28)).isoformat().replace("+00:00", "Z"),
            "user": "Sarah Chen",
            "role": "Incident Commander / Staff SRE",
            "message": "What deploys happened in the last 60 minutes? Check deploy logs and GitHub release tags.",
            "reactions": {"mag": 3},
        },
        {
            "timestamp": (base_time + timedelta(minutes=31)).isoformat().replace("+00:00", "Z"),
            "user": "Marcus Wright",
            "role": "Payment Backend Lead",
            "message": "PR #142 (PAY-9042) deployed at 14:05 UTC by @Dave Kumar. It bumped Kafka batch size to 5000 to improve Black Friday throughput.",
            "reactions": {"eyes": 5},
        },
        {
            "timestamp": (base_time + timedelta(minutes=35)).isoformat().replace("+00:00", "Z"),
            "user": "Dave Kumar",
            "role": "Data & Messaging Lead",
            "message": "Looking at consumer group `payment-workers-v2`. Consumer lag is surging exponentially. Partitions 0-15 keep cycling into `RebalanceInProgress`!",
            "reactions": {"fearful": 3},
        },
        {
            "timestamp": (base_time + timedelta(minutes=38)).isoformat().replace("+00:00", "Z"),
            "user": "Sarah Chen",
            "role": "Incident Commander / Staff SRE",
            "message": "Hypothesis: When batch size increased to 5000, processing the batch took longer than `max.poll.interval.ms`. Kafka broker assumed workers died and triggered partition rebalance, dropping the in-flight DB transaction without closing it!",
            "reactions": {"heavy_check_mark": 7, "fire": 2},
        },
        {
            "timestamp": (base_time + timedelta(minutes=42)).isoformat().replace("+00:00", "Z"),
            "user": "Dave Kumar",
            "role": "Data & Messaging Lead",
            "message": "Spot on @Sarah Chen. The uncommitted batch left open Postgres row locks on `payment_transactions`, starving subsequent batches. Rebalance storm triggered!",
            "reactions": {"100": 6},
        },
        {
            "timestamp": (base_time + timedelta(minutes=50)).isoformat().replace("+00:00", "Z"),
            "user": "Sarah Chen",
            "role": "Incident Commander / Staff SRE",
            "message": "Decision: 1) Deploy hotfix to revert consumer batch size to 100 with strict heartbeat guards. 2) Terminate idle Postgres backend sessions holding locks.",
            "reactions": {"white_check_mark": 8, "rocket": 5},
        },
        {
            "timestamp": (base_time + timedelta(minutes=66)).isoformat().replace("+00:00", "Z"),
            "user": "Dave Kumar",
            "role": "Data & Messaging Lead",
            "message": "PR #143 hotfix deployed. Consumer lag is draining rapidly (down from 450k msgs to 12k).",
            "reactions": {"tada": 6},
        },
        {
            "timestamp": (base_time + timedelta(minutes=72)).isoformat().replace("+00:00", "Z"),
            "user": "Elena Rostova",
            "role": "Database SRE",
            "message": "Postgres connection pool dropped back to 14% utilization. All deadlocks cleared.",
            "reactions": {"white_check_mark": 5},
        },
        {
            "timestamp": (base_time + timedelta(minutes=75)).isoformat().replace("+00:00", "Z"),
            "user": "Sarah Chen",
            "role": "Incident Commander / Staff SRE",
            "message": "Payment gateway latency restored to 95ms p99. Incident resolved. Please prep post-mortem data.",
            "reactions": {"party_blob": 8},
        },
    ]
    with open(os.path.join(INCIDENT_DIR, "slack_thread.json"), "w", encoding="utf-8") as f:
        json.dump(slack_messages, f, indent=2)

    # -----------------------------------------------------------------------
    # 4. PagerDuty Alerts
    # -----------------------------------------------------------------------
    alerts = [
        {
            "timestamp": (base_time + timedelta(minutes=15, seconds=30)).isoformat().replace("+00:00", "Z"),
            "source": "PagerDuty",
            "severity": "CRITICAL",
            "title": "PaymentGatewayLatencyP99Exceeded",
            "description": "Payment Gateway p99 latency is 24,100ms (threshold: 500ms) on cluster us-east-1.",
            "service": "payment-gateway",
        },
        {
            "timestamp": (base_time + timedelta(minutes=17, seconds=0)).isoformat().replace("+00:00", "Z"),
            "source": "PagerDuty",
            "severity": "CRITICAL",
            "title": "KafkaConsumerLagExceeded",
            "description": "Consumer group 'payment-workers-v2' partition lag > 350,000 messages.",
            "service": "kafka-consumer",
        },
        {
            "timestamp": (base_time + timedelta(minutes=19, seconds=15)).isoformat().replace("+00:00", "Z"),
            "source": "Datadog",
            "severity": "CRITICAL",
            "title": "PostgresConnectionPoolExhausted",
            "description": "Active connections on db-master-prod reached 990/1000 with 45 waiting queries.",
            "service": "postgres-db",
        },
        {
            "timestamp": (base_time + timedelta(minutes=22, seconds=0)).isoformat().replace("+00:00", "Z"),
            "source": "PagerDuty",
            "severity": "WARNING",
            "title": "OrderCheckoutFailuresHigh",
            "description": "Order placement service reporting 42% HTTP 504 error rate on /orders/checkout.",
            "service": "order-service",
        },
        {
            "timestamp": (base_time + timedelta(minutes=74, seconds=0)).isoformat().replace("+00:00", "Z"),
            "source": "PagerDuty",
            "severity": "INFO",
            "title": "AllAlertsResolved",
            "description": "All monitor thresholds normalized. Latency and error rates within SLO.",
            "service": "payment-gateway",
        },
    ]
    with open(os.path.join(INCIDENT_DIR, "alerts.json"), "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=2)

    # -----------------------------------------------------------------------
    # 5. Jira Tickets
    # -----------------------------------------------------------------------
    jira_tickets = [
        {
            "key": "PAY-9042",
            "summary": "Black Friday Throughput: Increase Kafka payment consumer batch size to 5000",
            "description": "Increase consumer max.poll.records to 5000 to maximize throughput during Black Friday sales surge.",
            "status": "In Progress",
            "priority": "P1",
            "created_at": (base_time - timedelta(days=2)).isoformat().replace("+00:00", "Z"),
            "assignee": "Dave Kumar",
            "components": ["payment-gateway", "kafka-consumer"],
            "labels": ["black-friday", "throughput-optimization"],
        },
        {
            "key": "INFRA-819",
            "summary": "Investigate Kafka rebalance storm during partition leader failover",
            "description": "Kafka consumer groups experiencing frequent rebalance cycles under heavy batch sizes.",
            "status": "Open",
            "priority": "P2",
            "created_at": (base_time - timedelta(days=5)).isoformat().replace("+00:00", "Z"),
            "assignee": "Sarah Chen",
            "components": ["kafka-consumer", "postgres-db"],
            "labels": ["kafka", "resilience"],
        },
    ]
    with open(os.path.join(INCIDENT_DIR, "jira_tickets.json"), "w", encoding="utf-8") as f:
        json.dump(jira_tickets, f, indent=2)

    # -----------------------------------------------------------------------
    # 6. High-Volume Logs (1,000+ entries with injected secrets)
    # -----------------------------------------------------------------------
    logs = []
    current_ts = base_time

    # Pre-incident normal traffic (100 logs)
    for i in range(100):
        current_ts += timedelta(seconds=random.randint(1, 4))
        logs.append({
            "timestamp": current_ts.isoformat().replace("+00:00", "Z"),
            "level": "INFO",
            "service": "payment-gateway",
            "message": f"Processed payment transaction tx_{10000+i} successfully in {random.randint(45, 95)}ms",
            "metadata": {"user_id": f"usr_{i}", "amount": random.randint(10, 500)},
        })

    # Deploy event log with injected AWS and DB credentials (to stress sanitizer)
    current_ts = base_time + timedelta(minutes=5)
    logs.append({
        "timestamp": current_ts.isoformat().replace("+00:00", "Z"),
        "level": "INFO",
        "service": "kafka-consumer",
        "message": "Deployed release v3.4.1 (commit f8a9b1c). Config: max.poll.records=5000, max.poll.interval.ms=300000. Connected to postgres://pay_admin:SuperSecretPostgresPass123!@db-prod-master.internal:5432/payments_db with AWS_KEY=AKIAIOSFODNN7EXAMPLE",
        "metadata": {"deployer": "dave.k", "token": "ghp_1234567890abcdefghijklmnopqrstuvwxyz12"},
    })

    # Failure cascade logs (700 logs of rebalances, deadlocks, and pool exhaustion)
    for i in range(700):
        current_ts += timedelta(seconds=random.randint(1, 3))
        err_type = random.choice(["rebalance", "deadlock", "pool_timeout", "gateway_504"])
        
        if err_type == "rebalance":
            logs.append({
                "timestamp": current_ts.isoformat().replace("+00:00", "Z"),
                "level": "ERROR",
                "service": "kafka-consumer",
                "message": f"CommitFailedException: Commit cannot be completed since the group has already rebalanced and assigned the partitions to another member. Generation {400 + (i%5)}.",
                "metadata": {"partition": i % 16, "topic": "payment.charges.v2"},
            })
        elif err_type == "deadlock":
            logs.append({
                "timestamp": current_ts.isoformat().replace("+00:00", "Z"),
                "level": "FATAL",
                "service": "postgres-db",
                "message": f"DeadlockDetected: Process {2000+i} waits for ExclusiveLock on relation 16402 payment_transactions; blocked by process {2001+i}.",
                "metadata": {"shard": f"shard_{i%3}", "blocked_pid": 2000 + i},
            })
        elif err_type == "pool_timeout":
            logs.append({
                "timestamp": current_ts.isoformat().replace("+00:00", "Z"),
                "level": "ERROR",
                "service": "payment-gateway",
                "message": f"ConnectionPoolTimeoutException: Timeout waiting for idle connection from pool after 30000ms. Active: 100/100, Idle: 0, Pending: {50 + (i%30)}.",
                "metadata": {"pool": "payment_primary_pool"},
            })
        else:
            logs.append({
                "timestamp": current_ts.isoformat().replace("+00:00", "Z"),
                "level": "ERROR",
                "service": "order-service",
                "message": f"HTTP 504 Gateway Timeout from upstream payment-gateway for checkout order_chk_{50000+i}",
                "metadata": {"status_code": 504, "latency_ms": 30050},
            })

    # Recovery logs (200 logs)
    current_ts = base_time + timedelta(minutes=65)
    logs.append({
        "timestamp": current_ts.isoformat().replace("+00:00", "Z"),
        "level": "INFO",
        "service": "kafka-consumer",
        "message": "Deployed hotfix v3.4.2 (commit d3e2a1b). Reset max.poll.records=100. Consumer group stabilized.",
        "metadata": {"status": "stabilized"},
    })

    for i in range(200):
        current_ts += timedelta(seconds=random.randint(1, 3))
        logs.append({
            "timestamp": current_ts.isoformat().replace("+00:00", "Z"),
            "level": "INFO",
            "service": "payment-gateway",
            "message": f"Processed payment transaction tx_{20000+i} successfully in {random.randint(50, 95)}ms",
            "metadata": {"user_id": f"usr_rec_{i}", "amount": random.randint(15, 300)},
        })

    # -----------------------------------------------------------------------
    # 7. Ground Truth Definition
    # -----------------------------------------------------------------------
    ground_truth = {
        "incident_id": "INC-011",
        "title": "Global Payment Outage & Cascading Kafka Partition Starvation",
        "root_cause": "PR #142 (commit f8a9b1c) increased Kafka consumer batch size (max.poll.records) from 100 to 5000 without configuring a corresponding heartbeat interval or poll timeout guard. Under peak Black Friday load, batch processing duration exceeded max.poll.interval.ms (300,000ms), causing the Kafka broker to mark consumers dead and trigger continuous partition rebalance storms across partitions 0-15. Dropped consumers left open, uncommitted transaction locks on the payment_transactions PostgreSQL table, which starved connection pools and caused cascading HTTP 504 Gateway Timeouts across upstream payment and order services.",
        "contributing_factors": [
            "Kafka consumer batch size increased 50x without load testing or heartbeat interval adjustments.",
            "PostgreSQL transaction timeout and statement timeout were not set, allowing orphaned sessions to hold ExclusiveLocks indefinitely.",
            "Absence of a circuit breaker between payment-gateway and kafka-consumer to shed load during rebalance cycles.",
            "Deploy was rolled out directly to 100% of payment worker nodes without a canary stage."
        ],
        "key_timeline_events": [
            {"timestamp": "2025-04-18T14:05:00Z", "source": "git", "description": "PR #142 deployed by Dave Kumar setting max.poll.records=5000 on payment-workers-v2"},
            {"timestamp": "2025-04-18T14:15:30Z", "source": "alerts", "description": "PagerDuty P1 alert: PaymentGatewayLatencyP99Exceeded (p99 latency > 24,000ms)"},
            {"timestamp": "2025-04-18T14:17:00Z", "source": "alerts", "description": "PagerDuty P1 alert: KafkaConsumerLagExceeded (> 350,000 messages)"},
            {"timestamp": "2025-04-18T14:20:00Z", "source": "slack", "description": "Elena Rostova flags Postgres connection pool at 98% and DeadlockDetected on payment_transactions"},
            {"timestamp": "2025-04-18T14:38:00Z", "source": "slack", "description": "Sarah Chen identifies root cause: 5000 batch size exceeds max.poll.interval.ms triggering rebalance storm and uncommitted DB locks"},
            {"timestamp": "2025-04-18T14:50:00Z", "source": "slack", "description": "Decision: Deploy hotfix reverting batch size to 100 and terminate idle locking Postgres backends"},
            {"timestamp": "2025-04-18T15:05:00Z", "source": "git", "description": "Hotfix commit d3e2a1b (PR #143) deployed by Dave Kumar"},
            {"timestamp": "2025-04-18T15:15:00Z", "source": "slack", "description": "Payment latency restored to 95ms; all 68k checkout backlog cleared; incident resolved"}
        ],
        "action_items": [
            {"priority": "P0", "type": "Prevent", "action": "Enforce automated CI lint rules forbidding max.poll.records > 500 without explicit max.poll.interval.ms and heartbeat overrides", "owner": "Data Infrastructure Team"},
            {"priority": "P0", "type": "Prevent", "action": "Set idle_in_transaction_session_timeout = 30s on PostgreSQL payment databases", "owner": "Database Reliability Team"},
            {"priority": "P1", "type": "Detect", "action": "Add Datadog alerts on Kafka consumer group rebalance frequency (> 2 rebalances in 5 mins)", "owner": "Observability Team"},
            {"priority": "P2", "type": "Mitigate", "action": "Implement circuit breaker and dead-letter queue in payment worker ingest", "owner": "Payment Core Team"}
        ]
    }
    with open(os.path.join(INCIDENT_DIR, "ground_truth.json"), "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"Generated Mega Incident INC-011 at: {INCIDENT_DIR}")
    print(f"  - Logs: {len(logs)} entries")
    print(f"  - Slack: {len(slack_messages)} messages")
    print(f"  - Commits: {len(commits)} commits")
    print(f"  - Alerts: {len(alerts)} alerts")
    print(f"  - Jira Tickets: {len(jira_tickets)} tickets")


if __name__ == "__main__":
    generate_mega_incident()
