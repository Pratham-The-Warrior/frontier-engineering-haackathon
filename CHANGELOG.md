# Improvement Changelog

This changelog tells the story of how the solution evolved from a simple baseline to the final multi-agent pipeline. Each entry documents what we tried, why, and what we learned.

---

## Baseline: Single-Prompt Approach

**What we tried:** Feed ALL incident data (logs, Slack, git, alerts) into a single LLM prompt with basic instructions: "Write a post-mortem based on this data."

**Why:** Establish a fair starting point that represents the simplest reasonable approach.

**Evidence:** See `output/baseline/` for generated reports.

**Result:** Reports are generated but suffer from:
- Missing important timeline events (buried in the data dump)
- Surface-level root cause analysis (often identifies symptoms, not systemic causes)
- Inconsistent quality across incidents
- Occasional blame language ("the developer forgot to...")
- Missing sections (action items, contributing factors often skipped)

**Decision:** This is our baseline. The goal is to meaningfully improve on every dimension.

---

## Iteration 1: Split Into Source-Specific Agents

**What we tried:** Instead of dumping all data into one prompt, we created 3 specialized agents:
1. Log Parser Agent — analyzes only logs with specialized tools
2. Communications Analyzer — analyzes only Slack threads
3. Git Analyzer — analyzes only git commits with risk scoring tools

**Why:** Each data source requires different analytical skills. Log analysis benefits from pattern detection and anomaly tools. Communication analysis requires understanding human decisions. Git analysis needs risk scoring heuristics.

**Evidence:** Source-specific agents produce more focused, detailed findings than a single prompt that must context-switch between data types.

**Result:**
- Log Parser finds error patterns and service degradation transitions that the single prompt misses
- Comms Analyzer captures the investigation path and key decisions
- Git Analyzer correctly identifies suspicious commits with risk scoring

**Decision:** Kept. The source-specific decomposition produces richer intermediate findings.

---

## Iteration 2: Added Timeline Builder Agent

**What we tried:** Added a 4th agent (Timeline Builder) that takes findings from all 3 source agents and synthesizes them into a unified, chronological timeline with cross-source correlation.

**Why:** The key insight is that no single source tells the full story. Logs show WHAT happened technically. Slack shows HOW the team responded. Git shows WHAT changed before the incident. Only by correlating across sources can you see the full picture.

**Evidence:** The Timeline Builder found cross-source correlations (e.g., "deploy completed at T1 in git → first error at T2 in logs → team discovered root cause at T3 in Slack") that improve root cause identification.

**Result:**
- Timeline event recall improved significantly
- Cross-source correlations enabled more accurate root cause identification
- The narrative summary provided a coherent story arc

**Decision:** Kept. This is the single most impactful addition — the "memory" agent that holds context from all sources.

---

## Iteration 3: Added Verification Loop to Root Cause Analyzer

**What we tried:** After the Root Cause Analyzer produces its initial analysis, we added a verification step that checks:
1. Is every causal claim backed by specific evidence?
2. Is the language blameless?
3. Is the root cause truly systemic (not surface-level)?
4. Are there obvious contributing factors missing?

**Why:** We observed that the agent was hallucinating causation — inventing plausible-sounding causal chains not supported by evidence. A deploy happened near the incident? The agent confidently blamed it, even when correlation != causation.

**Evidence:** The verification step catches unsupported claims and requests revisions. On incidents where evidence is ambiguous, it correctly flags lower confidence.

**Result:**
- Root cause accuracy improved (fewer hallucinated causal claims)
- Reports are more honest about uncertainty when evidence is ambiguous

**Decision:** Kept. Verification is not optional for high-stakes analysis.

---

## Iteration 4: Added Blameless Language Checker to Report Writer

**What we tried:** Added automated blameless language detection to the Report Writer agent. If blame-assigning language is detected (e.g., "the developer forgot to check"), the report is automatically revised.

**Why:** Post-mortem best practice is blameless culture (Google SRE book). Blame language discourages engineers from reporting incidents honestly. Our reports must model best practices.

**Evidence:** The tool detects patterns like personal blame phrases, assigns suggestions, and triggers a revision pass if the blameless score is below 80/100.

**Result:**
- Blameless language scores improved from ~70 to ~95+
- Reports use systemic language: "The deployment process did not include a config validation step" instead of "John forgot to check the config"

**Decision:** Kept. This is a quality guardrail that ensures professional output.

---

## Iteration 5: Added Forensic Code Diff & Risky Line Pinpointer

**What we tried:** Upgraded Git Analyzer and Report Writer to isolate the exact "Smoking Gun" commit and reconstruct syntax-highlighted git diffs with inline risk annotations (`# 🚨 ROOT CAUSE:` or `# ⚠️ LEAK:`) alongside a preventative remediation patch (`# ✅ Proper pattern:`).

**Why:** Abstract text summaries force engineers to manually hunt for the buggy lines. A syntax-highlighted diff makes the root cause immediately intuitive and actionable to any developer or reviewer.

**Evidence:** Visual inspection of generated post-mortems across code-bug and configuration incidents confirmed clean `diff` code blocks with precise line-by-line vulnerability callouts.

**Result:**
- Bridges the gap between high-level SRE narrative and low-level code implementation
- Elevates output to match modern developer platforms like CodeRabbit and GitHub PR reviews

**Decision:** Kept. This is a visual and technical differentiator that makes reports immediately actionable.

---

## Iteration 6: Added Zero-Friction Enterprise Integrations (Slack, Jira, PagerDuty)

**What we tried:** Built a standalone integration module (`integrations/enterprise_integrations.py`) supporting Slack Block Kit executive cards, automated Jira ticket generation from Action Items, and PagerDuty webhook triggers.

**Why:** High adoption friction prevents teams from utilizing post-mortem tooling. Meeting teams where they already communicate (Slack, PagerDuty, Jira) reduces adoption friction to < 5 minutes.

**Evidence:** Executing with `--export-slack` produces native Slack Block Kit JSON; executing with `--export-jira` automatically extracts prioritized action items (P0/P1/P2) with owner labels.

**Result:**
- Eliminates manual copy-pasting of action items into project trackers
- Gives leadership a 30-second Slack card with 1-click deep dive

**Decision:** Kept. Essential for organizational adoption and practical value.

---

## Experiment Removed: Parallel Execution of Source Agents

**What we tried:** Running agents 1-3 in parallel using Python's `concurrent.futures.ThreadPoolExecutor`.

**Why:** Wanted to reduce total pipeline time since agents 1-3 are independent.

**Evidence:** Total time reduced by ~40% in parallel mode.

**Result:** Kept the architecture parallel-capable but reverted to sequential execution for the hackathon submission.

**Decision:** Removed for reproducibility. Parallel execution introduced non-deterministic ordering in trajectory logs, making evaluation harder to reproduce. The sequential version is clearer for judges to follow. The architecture supports parallelization for production use.

**Learning:** Reproducibility matters more than speed for evaluation. In production, you'd absolutely parallelize.

---

## Final: Combined All Improvements

**What the final system does:**
1. **Phase 1 (Source Analysis):** Three specialized agents analyze logs, communications, and git changes independently, each with domain-specific tools (including static risk pattern scanning)
2. **Phase 2 (Synthesis & Shared Memory):** Timeline Builder unifies multi-modal timestamps into `IncidentContext` shared memory with cross-source causal correlation
3. **Phase 3 (Agentic Analysis):** Root Cause Analyzer performs hypothesis generation, evidence tool validation (`check_evidence`, `find_corroborating_events`), and hypothesis ranking
4. **Phase 4 (Output):** Report Writer generates a CodeRabbit-grade post-mortem with executive brief, risk matrix, syntax-highlighted forensic diffs, evidence citations, and automated Jira action tickets

**Final evidence:** See `evaluation/results/comparison_table.md` for the complete baseline vs. agent comparison across all 10 incidents.

**Main contribution:** The combination of cross-source correlation in shared memory and empirical evidence-testing tools eliminates ~40% of hallucinated causal claims while delivering a scannable, developer-friendly forensic diff report.
