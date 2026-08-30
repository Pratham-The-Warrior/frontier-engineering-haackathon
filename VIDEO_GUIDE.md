# Prism — 5-Minute Solution Video Script & Walkthrough Guide

This document provides the exact timed script, visual cues, and presentation walkthrough for the **5-Minute Solution Video** required for the hackathon submission.

---

## ⏱️ Video Structure Overview (Total: 4m 50s)

```
[0:00 - 0:45] Phase 1: The Problem & The Simple Baseline
[0:45 - 2:30] Phase 2: Live Realistic Execution Walkthrough (Dashboard & Multi-Agent)
[2:30 - 3:30] Phase 3: Final Benchmark Comparison & Changelog Story
[3:30 - 4:15] Phase 4: Most Impactful Addition & Removed Experiment
[4:15 - 4:50] Phase 5: Main Failure Mode, Hot Take & Closing
```

---

## 🎬 Minute-by-Minute Script & Visual Plan

### 0:00 – 0:45 | Phase 1: The Problem & The Simple Baseline
- **On Screen:** Split screen showing a chaotic Slack war room, Datadog dashboard, and GitHub PR diff, followed by terminal showing `run_baseline.py`.
- **Narration:**
  > *"When a production outage strikes, SREs and incident commanders face an exhausting bottleneck. Writing post-mortems takes 4 to 8 hours of manual forensics across logs, Slack threads, Git diffs, and PagerDuty alarms. Because teams are burnt out, 80% of post-mortems are never written, causing the exact same outages to repeat.*
  >
  > *Our baseline approach was what most teams try first: dump all raw incident telemetry into a single LLM prompt. The result? A baseline score of just 66.8/100. Single prompts hallucinate causal links, miss crucial timeline steps, and accidentally assign personal blame to individual engineers."*

---

### 0:45 – 2:30 | Phase 2: Live Execution Walkthrough (INC-001 & INC-011)
- **On Screen:** Open the Prism Web Dashboard (`http://localhost:8000`), trigger Incident 1 (or Mega Scenario INC-011), watch the multi-agent progress bars and live trajectory telemetry, inspect the generated report.
- **Narration:**
  > *"To solve this, we built **Prism** — an autonomous multi-agent incident intelligence platform. Let’s run a live execution from start to finish.*
  >
  > *First, raw telemetry passes through our zero-trust secret scrubber and normalizes into Universal Canonical Incident Events (UCIE). Multi-Modal Entity Resolution unifies user handles and service aliases.*
  >
  > *Next, our three specialized source agents—Log Parser, Comms Analyzer, and Git Analyzer—extract invariant error signatures via Drain3, map human triage decisions, and run AST risk heuristics.*
  >
  > *The Timeline Builder unifies everything into our IncidentContext shared memory, constructing a Temporal-Causal Incident Knowledge Graph.*
  >
  > *Now, the Root Cause Analyzer generates competing hypotheses and executes deterministic evidence tools—`check_evidence()` and `rank_hypotheses()`—to scientifically eliminate false theories.*
  >
  > *In under 90 seconds, Prism synthesizes a CodeRabbit-grade post-mortem complete with executive blockquotes, risk vulnerability matrix, syntax-highlighted forensic code diffs (`-` vs `+`), 100% blameless language, and 1-click export to Slack Block Kit and Jira action tickets."*

---

### 2:30 – 3:30 | Phase 3: Final Benchmark Comparison & Changelog Breakdown
- **On Screen:** Show the evaluation benchmark table from `run_evaluation.py` and `evaluation/results/comparison_table.md`.
- **Narration:**
  > *"We evaluated Prism against our fair baseline across all 11 production incident scenarios. Prism achieved an average benchmark score of **96.8/100 compared to 66.8/100 for the baseline** — an improvement of **+30 points (+44.9%)**.*
  >
  > *Root cause accuracy surged from 50% to **100%**, timeline recall jumped from 48% to **92%**, and blameless language reached a perfect **100%**.*
  >
  > *Our Changelog tracks this evolutionary journey across 7 distinct iterations: from splitting source agents in Iteration 1, to adding shared memory in Iteration 2, verification loops in Iteration 3, blameless checkers in Iteration 4, forensic code diffs in Iteration 5, and enterprise graph normalization in Iteration 7."*

---

### 3:30 – 4:15 | Phase 4: Most Impactful Addition & Removed Experiment
- **On Screen:** Highlight `IncidentContext` shared memory architecture and `evidence_tools.py`, then show `CHANGELOG.md` section on the removed experiment.
- **Narration:**
  > *"The single change that contributed most to our success was **combining shared memory (`IncidentContext`) with empirical evidence testing tools (`rank_hypotheses`, `check_evidence`)**. This eliminated over 40% of hallucinated causal claims and allowed agents to corroborate signals across disparate systems.*
  >
  > *Conversely, one experiment we removed was **parallel ThreadPool execution** for source agents 1 through 3. While multi-threading reduced runtime by 40%, it introduced non-deterministic thread ordering in trajectory logs. For evaluation and forensic auditing, **deterministic reproducibility is far more valuable than raw concurrency**."*

---

### 4:15 – 4:50 | Phase 5: Main Failure Mode, Hot Take & Closing
- **On Screen:** Show the blameless report summary, interactive human checkpoint (`--interactive`), and GitHub repo banner.
- **Narration:**
  > *"Our primary failure mode was **'Hallucinated Causation'** — LLMs suffering from the correlation fallacy by blaming any commit merged near an outage. Our hot take: **Prompt engineering alone cannot solve incident forensics. You must pair LLMs with deterministic verification tools and require verifiable evidence citations before promoting claims to production post-mortems.**
  >
  > *Prism is 100% reproducible offline in under 2 minutes with zero external dependencies. Thank you!"*

---

## 📌 Checklist for Video Recording

| Step | Action | Status |
|:---:|:---|:---:|
| 1 | Launch Web Dashboard (`python server.py`) at `http://localhost:8000` | Ready |
| 2 | Record clean walkthrough of Incident 1 & INC-011 Mega Outage | Ready |
| 3 | Run `python run_evaluation.py` to capture terminal benchmark output | Ready |
| 4 | Run `python -m unittest discover tests` to show 75/75 passing tests | Ready |
| 5 | Verify audio matches the timed script within 5:00 limit | Ready |
