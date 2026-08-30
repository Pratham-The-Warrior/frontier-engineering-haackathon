# Prism — Representative Agent Trajectories & Trace Analysis

This document provides representative execution trajectories for every agent in the Prism multi-agent pipeline, illustrating how prompts, domain-specific tools, shared memory, verification loops, and human checkpoints interact to generate CodeRabbit-grade incident post-mortems without hallucination.

---

## 🗺️ Pipeline Trajectory Architecture

Prism captures every agent action, tool invocation, token usage, latency, and feedback loop into deterministic JSON execution traces saved under `output/agent/<incident_id>_trajectory.json`.

```
                  ┌──────────────────────────────────────────────────────────┐
                  │                RAW TELEMETRY INGESTION                   │
                  │  (Logs, Slack Threads, Git Diffs, Alerts, Jira Tickets)   │
                  └────────────────────────────┬─────────────────────────────┘
                                               │ [Zero-Trust Secret Scrubbing]
                                               ▼
                  ┌──────────────────────────────────────────────────────────┐
                  │      UCIE Canonical Normalization & Entity Resolution    │
                  └────────────────────────────┬─────────────────────────────┘
                                               │
               ┌───────────────────────────────┼───────────────────────────────┐
               ▼                               ▼                               ▼
       ┌───────────────┐               ┌───────────────┐               ┌───────────────┐
       │ 1. Log Parser │               │2. Comms Anal. │               │3. Git Analyzer│
       │     Agent     │               │     Agent     │               │     Agent     │
       └───────┬───────┘               └───────┬───────┘               └───────┬───────┘
               │                               │                               │
               │ Drain3 Mining                 │ Triage Decisions              │ AST Diff Tools
               │ Anomalies & Errors            │ Rollback Consensus            │ Risk Pattern Scans
               │                               │                               │
               └───────────────────────────────┼───────────────────────────────┘
                                               │
                                               ▼
                              ┌──────────────────────────────────┐
                              │    4. Timeline Builder Agent     │
                              │     [IncidentContext Memory]     │
                              └────────────────┬─────────────────┘
                                               │
                                               ▼
                              ┌──────────────────────────────────┐
                              │  5. Root Cause Analyzer Agent    │
                              │   (Agentic Hypothesis Testing)   │
                              └────────────────┬─────────────────┘
                                               │
                                   Empirical Tool Feedback:
                                   - rank_hypotheses()
                                   - check_evidence()
                                   - find_corroborating_events()
                                   - assess_causal_chain()
                                               │
                                               ▼
                              ┌──────────────────────────────────┐
                              │ [Human-in-the-Loop Checkpoint]   │
                              │ (--interactive / Dashboard UI)   │
                              └────────────────┬─────────────────┘
                                               │ (Approved Hypothesis)
                                               ▼
                              ┌──────────────────────────────────┐
                              │     6. Report Writer Agent       │
                              │    (Blameless & Completeness)    │
                              └────────────────┬─────────────────┘
                                               │
                                   Quality Guardrail Tools:
                                   - check_blameless_language()
                                   - validate_completeness()
                                               │
                                               ▼
                              ┌──────────────────────────────────┐
                              │   Executive CodeRabbit Report    │
                              │   + Slack Card + Jira Tickets    │
                              └──────────────────────────────────┘
```

---

## 🔬 Representative Step-by-Step Trajectory Trace (INC-001)

Below is the comprehensive trace recorded during the execution of **Incident 1: Database Connection Pool Exhaustion**.

---

### Step 1: Log Parser Agent (`agents/log_parser.py`)

#### Agent Objective & Shaping Instructions
> *"You are an expert SRE log analyst. Analyze the provided log summary and error patterns to produce structured log findings. Focus on error signatures, frequency patterns, first/last error times, affected services, and service degradation transitions."*

#### 1.1 Tool Preprocessing Phase
- **Tools Invoked:**
  - `parse_logs(raw_logs)`
  - `filter_by_severity(min_severity='WARNING')`
  - `find_error_patterns()`
  - `detect_anomalies()`
  - `summarise_logs()`
- **Tool Output Received:**
  ```json
  {
    "total_logs": 16,
    "warnings_and_errors": 11,
    "error_patterns_found": 6,
    "anomalies_detected": 3,
    "unique_signatures": [
      "ConnectionPoolExhausted: Pool size 20 reached, max waiting connections exceeded",
      "HTTP 500 Internal Server Error in /api/v1/users/profile",
      "Database connection acquisition timeout after 30000ms"
    ],
    "first_error_timestamp": "2024-01-15T14:05:33Z",
    "last_error_timestamp": "2024-01-15T14:28:10Z"
  }
  ```

#### 1.2 LLM Reasoning Phase
- **Model:** `gpt-4o-mini` (or offline mock fallback)
- **Extracted Insight:** `user-service` suffered connection starvation starting at 14:05:33Z. Cascaded to `api-gateway` returning 500 errors.

---

### Step 2: Communications Analyzer Agent (`agents/comms_analyzer.py`)

#### Agent Objective & Shaping Instructions
> *"You are an expert incident communications analyst. Analyze Slack war-room transcripts to extract key investigation steps, human triage decisions, candidate theories discussed, mitigation consensus, and emoji reactions."*

#### 2.1 Input Data Ingested
- 11 Slack messages across 4 participants (`@sarah.chen`, `@mike.torres`, `@priya.patel`, `@dev-oncall`).
- Key emoji reactions tracked (`:eyes:`, `:white_check_mark:`, `:fire:`).

#### 2.2 LLM Synthesis Phase
- **Model:** `gpt-4o-mini`
- **Output Generated:**
  ```json
  {
    "key_decisions": [
      {"time": "14:12:00Z", "actor": "Sarah Chen", "decision": "Declared P1 incident and initiated rollback of user-service v2.14.0"},
      {"time": "14:22:00Z", "actor": "Mike Torres", "decision": "Discovered pool_size was reduced from 50 to 20 in recent PR"}
    ],
    "competing_theories": [
      "Theory A: Postgres RDS CPU saturation",
      "Theory B: Misconfigured connection pool limits in v2.14.0"
    ],
    "resolution_consensus": "Rollback to v2.13.9 confirmed healthy at 14:28:00Z."
  }
  ```

---

### Step 3: Git Analyzer Agent (`agents/git_analyzer.py`)

#### Agent Objective & Shaping Instructions
> *"You are a senior software engineer and security/stability auditor. Analyze git commits and PR diffs leading up to the incident. Calculate commit risk scores, isolate the most suspicious culprit change, and extract syntax-highlighted forensic code diffs."*

#### 3.1 Tool Preprocessing Phase
- **Tools Invoked:**
  - `parse_commits(commits)`
  - `find_suspicious_changes()`
  - `detect_diff_risk_patterns(diffs)`
- **Tool Output Received:**
  ```json
  {
    "total_commits": 5,
    "suspicious_commits": 4,
    "detected_risk_patterns": 3,
    "culprit_commit": {
      "hash": "a1b2c3d4",
      "author": "Sarah Chen",
      "message": "perf: optimize db connection pool limits for cost savings",
      "risk_score": 85,
      "risk_factors": ["pool_size reduced by 60%", "removed acquire timeout guard"]
    }
  }
  ```

#### 3.2 Forensic Diff Extraction Phase
- **Model:** `gpt-4o`
- **Generated Forensic Diff:**
  ```diff
  - pool_size = 50  # [Git:a1b2c3d4]
  - pool_timeout = 30
  + pool_size = 20  # 🚨 [CAUSE: Pool shrunk without concurrency modeling]
  + pool_timeout = None  # 🚨 [CAUSE: Missing timeout causing thread hangs]
  ```

---

### Step 4: Timeline Builder Agent (`agents/timeline_builder.py`)

#### Agent Objective & Shaping Instructions
> *"You are a principal incident coordinator. Synthesize all findings from log, comms, and git agents into a unified, chronological timeline. Correlate cross-source events, detect time gaps, and structure into incident phases (Trigger, Detection, Escalation, Mitigation, Resolution)."*

#### 4.1 Tool Preprocessing & Correlation
- **Tools Invoked:**
  - `correlate_events(logs, git, comms, alerts)`
  - `detect_gaps()`
- **Output Generated:**
  - 36 canonical UCIE events linked in chronological sequence.
  - Multi-source correlation: `Deploy v2.14.0 (13:58:00) → First 500 error (14:05:33) → PagerDuty Alarm (14:08:12) → Rollback initiated (14:22:00) → Restored (14:28:00)`.

---

### Step 5: Root Cause Analyzer Agent (`agents/root_cause_analyzer.py`)

#### Agent Objective & Shaping Instructions
> *"You are an elite principal SRE. Formulate competing hypotheses, test each hypothesis against empirical evidence validation tools, rank them by proof density, and perform an adversarial verification pass."*

#### 5.1 Hypothesis Generation
- **Candidate Hypotheses:**
  1. *Hypothesis 1:* "Deploy v2.14.0 reduced Postgres pool_size from 50 to 20 without timeout limits, causing connection starvation under normal peak traffic."
  2. *Hypothesis 2:* "PostgreSQL database server experienced memory/CPU exhaustion causing query timeouts."

#### 5.2 Empirical Evidence Tool Validation
- **Tools Invoked:**
  - `rank_hypotheses(hypotheses, timeline_events)`
  - `check_evidence(claim, evidence_sources)`
  - `find_corroborating_events(trigger_event)`
- **Tool Results:**
  ```json
  [
    {
      "rank": 1,
      "hypothesis": "Deploy v2.14.0 reduced Postgres pool_size from 50 to 20...",
      "score": 1.0,
      "evidence_strength": "STRONG",
      "supporting_count": 6,
      "contradicting_count": 0
    },
    {
      "rank": 2,
      "hypothesis": "PostgreSQL database server experienced hardware exhaustion...",
      "score": 0.2,
      "evidence_strength": "UNSUPPORTED",
      "supporting_count": 0,
      "contradicting_count": 2
    }
  ]
  ```

#### 5.3 Causal Chain Tool Assessment
- **Tool Invoked:** `assess_causal_chain(chain)`
- **Feedback:** Chain validated: Temporal order strictly verified (Cause at 13:58 precedes Effect at 14:05).

---

### Step 6: Human-in-the-Loop Checkpoint (`--interactive`)

When executed with `--interactive` (or triggered from the Dashboard UI), execution pauses at the root cause hypothesis phase:

```
[HUMAN CHECKPOINT] Root Cause Hypothesis Review:
--------------------------------------------------------------------------------
Rank 1 (Score: 1.0): Deploy v2.14.0 reduced pool_size from 50 to 20 without timeout guard.
Supporting Evidence: [Git:a1b2c3d4], [Log:14:05:33], [Slack:14:22:00]

Approve hypothesis to proceed to report synthesis? [Y/n]: Y
Hypothesis approved by human reviewer: Sarah Chen (Principal SRE).
```

---

### Step 7: Report Writer Agent (`agents/report_writer.py`)

#### Agent Objective & Shaping Instructions
> *"You are an expert technical writer. Produce a CodeRabbit-grade post-mortem incorporating Shields.io vector badges, Lucide icon headers, risk & vulnerability matrix, syntax-highlighted forensic code diffs, and evidence citations. Ensure 100% blameless language."*

#### 7.1 Report Quality & Blameless Verification Loop
- **Tools Invoked:**
  - `check_blameless_language(report_text)`
  - `validate_report_completeness(report_text)`
  - `diff_check(report_text)`
- **Quality Scorecard Result:**
  ```json
  {
    "blameless_score": 100,
    "completeness_score": 100,
    "blameless_violations": 0,
    "missing_sections": [],
    "evidence_citations_found": 24,
    "has_forensic_diff": true
  }
  ```

---

## 📊 Summary: Trajectory Comparison (Baseline vs. Multi-Agent)

| Trajectory Property | Single-Prompt Baseline | Prism Multi-Agent Pipeline |
|:---|:---|:---|
| **Execution Steps** | 1 monolithic prompt | 7 specialized deterministic phases |
| **Tool Invocations** | 0 tools | 15+ specialized verification tools |
| **Empirical Evidence Testing** | None (pure LLM hallucination risk) | Deterministic ranking via `check_evidence()` |
| **Self-Correction & Quality Guardrails** | None | Automated Blameless Checker & Causal Validator |
| **Human Checkpoint Support** | None | Interactive hypothesis gate (`--interactive`) |
| **Auditability & Traceability** | Black box output | Full JSON step trajectory with token/latency telemetry |
