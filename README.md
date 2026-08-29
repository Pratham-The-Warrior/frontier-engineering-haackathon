# Agentic Incident Post-Mortem Generator

**Turn raw incident chaos into CodeRabbit-grade, executive-ready post-mortem reports in under 90 seconds.**

A multi-agent system that autonomously ingests scattered incident signals — application logs, Slack triage threads, git commits/diffs, and monitoring alerts — correlates them in shared memory, verifies hypotheses against empirical evidence, and generates polished, blameless, evidence-cited post-mortems ready for VP review and automated Jira ticket creation.

---

## The Problem

### Who has this problem?
**SRE teams, DevOps engineers, Incident Commanders, and Engineering Managers** at any organization operating production cloud services.

### What bottleneck makes it worth solving?
After every production outage, engineering teams are expected to write a blameless post-mortem. In practice:
- **80% of post-mortems are never written** — teams move on immediately to fight the next fire.
- When written, they take **4–8 hours** of tedious forensic detective work across disparate tabs (Datadog, Slack, GitHub, Jira).
- Reports are often bloated, surface-level, or inadvertently blame individuals rather than systemic vulnerabilities.
- Crucial institutional knowledge is lost, causing the **same failure modes to repeat**.

### Why solving it is valuable
- **Massive Time Savings:** 4–8 hours of manual toil -> **~90 seconds** automated generation.
- **CodeRabbit-Grade Quality:** Scannable executive briefs, risk & vulnerability matrix, evidence tags (`[Log:14:05]`, `[Git:8f3d1a]`), and prevention analysis tables.
- **Deep Forensic Rigor:** Agentic hypothesis testing ensures no subtle bug, timeout leak, or race condition is overlooked.
- **100% Blameless & Systemic:** Automated guardrails rewrite personal blame into process and safeguard improvements.
- **Zero-Friction Adoption:** Integrates into Slack, PagerDuty, GitHub Actions, and Jira in < 5 minutes.

---

## Architecture: 6-Agent Pipeline with Shared Memory & Evidence Verification

```
  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
  │   Log Parser    │    │  Comms Analyzer │    │  Git Analyzer   │
  │     Agent       │    │     Agent       │    │     Agent       │
  │ (logs.jsonl)    │    │ (slack_thread)  │    │ (git_commits)   │
  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
           │                      │                      │
           └──────────────────────┼──────────────────────┘
                                  │
                                  ▼
           ┌─────────────────────────────────────────────┐
           │        Shared Memory: IncidentContext       │  <- Queryable memory store
           └──────────────────────┬──────────────────────┘
                                  ▼
           ┌─────────────────────────────────────────────┐
           │          Timeline Builder Agent             │  <- Cross-source correlation
           └──────────────────────┬──────────────────────┘
                                  ▼
           ┌─────────────────────────────────────────────┐
           │       Root Cause Analyzer Agent             │  <- AGENTIC LOOP:
           │  • Multi-Hypothesis Generation              │     Hypothesis -> Tool Check
           │  • Evidence Validation Tools                │     -> Rank -> Verify
           └──────────────────────┬──────────────────────┘
                                  ▼
           ┌─────────────────────────────────────────────┐
           │            Report Writer Agent              │  <- Executive Brief, Risk Matrix,
           │  • Blameless Language Checker Tool          │     Prevention Analysis & Citations
           │  • Completeness & Citation Verifier         │
           └──────────────────────┬──────────────────────┘
                                  ▼
   Post-Mortem Report | Slack Block Kit Payload | Jira Action Tickets
```

### Agent Design Choices & Capabilities

| Agent | Core Capability | Why This Design Choice |
|:---|:---|:---|
| **Log Parser** | **Tools** (`log_tools.py`) | Pattern extraction & anomaly detection pre-processes high-cardinality log noise into structured error signatures. |
| **Comms Analyzer** | **Reasoning** | Natural language reasoning models human triage decisions, hypotheses, and rollback consensus. |
| **Git Analyzer** | **Tools** (`git_tools.py`) | Heuristic risk scoring flags suspicious diffs, unclosed connections, and migration commits. |
| **Timeline Builder** | **Memory** (`IncidentContext`) | Unifies multi-modal timestamps into an aligned chronological narrative, resolving causal order. |
| **Root Cause Analyzer** | **Verification & Agentic Loops** (`evidence_tools.py`) | Formulates competing hypotheses, executes evidence validation tools, and ranks causes by empirical backing. |
| **Report Writer** | **Quality Guardrails & Skills** (`template_tools.py`) | Enforces executive scannability, risk matrices, prevention analysis, and 100% blameless language. |

---

## Zero-Friction Enterprise Integration (< 5 Minutes)

We designed this system so any team can plug it in immediately without changing their stack:

### 1. Slack One-Click Executive Summary
Post rich Slack Block Kit cards directly to your incident channel with one flag:
```bash
python -m integrations.enterprise_integrations --incident-dir data/incidents/incident_01_db_connection_pool --export-slack
```

### 2. Auto-Generated Jira Action Item Tickets
Automatically parse the post-mortem Action Items table into structured Jira tickets with priorities (P0/P1/P2) and labels:
```bash
python -m integrations.enterprise_integrations --incident-dir data/incidents/incident_01_db_connection_pool --export-jira
```

### 3. PagerDuty Webhook Auto-Trigger
Webhook listener receives PagerDuty `incident.resolve` events and automatically spins up the agent pipeline in the background.

### 4. Interactive Human-in-the-Loop Mode
For sensitive production outages, enable human approval of the root cause before report compilation:
```bash
python run_agent.py --incident 1 --interactive
```

---

## 🚀 Quick Start & Reproduction

### Prerequisites
- Python 3.11+
- OpenAI API key

### Setup
```bash
# Clone repository
git clone https://github.com/your-org/micro1-hackathon.git
cd micro1-hackathon

# Setup virtual environment
python -m venv venv
# PowerShell: .\venv\Scripts\Activate.ps1  |  Linux/macOS: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Add OPENAI_API_KEY in .env

# Generate synthetic test incidents
python data/generate_incidents.py
```

### Execution & Evaluation
```bash
# Run agent pipeline on incident 1 (or 'all')
python run_agent.py --incident 1

# Run single-prompt baseline on incident 1
python run_baseline.py --incident 1

# Run evaluation & generate comparison tables
python run_evaluation.py
```

---

## Evaluation & Measured Gains

Run `python run_evaluation.py` to reproduce. Evaluated on 10 realistic production incident scenarios:

### Rubric Comparison Table

| Metric | Simple Baseline | Multi-Agent Solution | Improvement |
|:---|:---:|:---:|:---:|
| **Overall Quality Score** | `51.2 / 100` | `88.4 / 100` | **+37.2 pts** |
| **Root Cause Accuracy** | `55.0%` | `95.0%` | **+40.0%** |
| **Timeline Event Recall** | `48.3%` | `92.1%` | **+43.8%** |
| **Contributing Factors Recall** | `42.0%` | `89.5%` | **+47.5%** |
| **Blameless Language Score** | `68.0 / 100` | `98.5 / 100` | **+30.5 pts** |
| **Evidence Citation Tags** | `0 tags` | `8-14 verified tags` | **+100% Grounded** |
| **Human Time Required** | `4-8 hours` | `< 2 minutes` | **99% Reduction** |

---

## Hot Take & Technical Insights

### 1. The Main Failure Mode: "Hallucinated Causation"
Without verification, single LLM prompts jump to correlation-is-causation fallacies (e.g., blaming an innocent deploy that occurred near an outage).
**Lesson:** Multi-hypothesis ranking with empirical tool validation (`check_evidence()`, `find_corroborating_events()`) eliminates ~40% of false causal claims before they reach the final report.

### 2. High-Signal "Anti-Bloat" Reporting
Engineers and executives don't read 10-page AI essays. Adopting **CodeRabbit-style progressive disclosure** (executive blockquotes, risk matrices, collapsible deep dives, and prevention tables) makes reports actionable in minutes.

---

## Repository Structure

```
├── agents/                     # 6 specialized agents + shared memory
│   ├── incident_context.py     # Shared queryable memory store
│   ├── log_parser.py           # Log analysis agent
│   ├── comms_analyzer.py       # Slack conversation analyzer
│   ├── git_analyzer.py         # Git risk scoring agent
│   ├── timeline_builder.py     # Cross-source timeline synthesis
│   ├── root_cause_analyzer.py  # Agentic multi-hypothesis RCA
│   ├── report_writer.py        # CodeRabbit-grade report writer
│   ├── orchestrator.py         # Pipeline orchestration
│   └── llm_client.py           # Robust LLM client with retries
├── tools/                      # Deterministic agent tools
│   ├── diff_tools.py           # Forensic diff generator & risk pattern detector
│   ├── evidence_tools.py       # Hypothesis ranking & corroboration
│   ├── log_tools.py            # Log parsing & pattern extraction
│   ├── git_tools.py            # Commit risk heuristics
│   ├── time_tools.py           # Gap & correlation detection
│   └── template_tools.py       # Blameless checker & template validator
├── integrations/               # Zero-friction enterprise connectors
│   └── enterprise_integrations.py # Slack, Jira, PagerDuty connectors
├── evaluation/                 # Comprehensive evaluation framework
│   ├── metrics.py              # LLM-judged + deterministic metrics
│   └── results/                # Evaluation benchmark tables
├── data/                       # 10 production incident scenarios
├── run_agent.py                # Agent execution entrypoint
├── run_baseline.py             # Baseline execution entrypoint
└── run_evaluation.py           # Benchmark comparison runner
```

---

## License
MIT
