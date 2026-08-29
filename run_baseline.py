"""
Baseline: Single-prompt approach to post-mortem generation.
Sends ALL incident data in one prompt with basic instructions.

This represents the "naive" approach that the multi-agent pipeline improves upon.

Usage:
    python run_baseline.py --incident 1
    python run_baseline.py --incident all
"""

import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import time

from agents.llm_client import call_llm, MODEL

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "incidents")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "baseline")

BASELINE_PROMPT = """\
You are an SRE. Write a post-mortem report based on the incident data below.

Include these sections:
- Executive Summary
- Impact
- Timeline
- Root Cause
- Contributing Factors
- Resolution
- Action Items
- Lessons Learned

Use blameless language. Focus on systems and processes, not individuals.
Write in Markdown format.
"""


def load_incident(incident_dir: str) -> dict:
    """Load all data files for a single incident."""
    data = {}
    for filename in os.listdir(incident_dir):
        filepath = os.path.join(incident_dir, filename)
        if filename.endswith(".json") or filename.endswith(".jsonl"):
            with open(filepath, "r", encoding="utf-8") as f:
                data[filename] = json.load(f)
    return data


def get_incident_dirs() -> list[tuple[int, str, str]]:
    """Return list of (number, name, path) for all incidents."""
    incidents = []
    for name in sorted(os.listdir(DATA_DIR)):
        path = os.path.join(DATA_DIR, name)
        if os.path.isdir(path) and name.startswith("incident_"):
            num = int(name.split("_")[1])
            incidents.append((num, name, path))
    return incidents


def run_baseline_single(incident_num: int, verbose: bool = True) -> dict:
    """Run the single-prompt baseline on one incident."""
    incidents = get_incident_dirs()
    match = [i for i in incidents if i[0] == incident_num]
    if not match:
        print(f"Error: Incident {incident_num} not found.")
        sys.exit(1)

    num, name, path = match[0]
    data = load_incident(path)
    metadata = data.get("metadata.json", {})

    if verbose:
        print(f"\n[Baseline] Processing: {metadata.get('title', name)}")

    # Build the single prompt with ALL data dumped in
    all_data_str = ""
    for filename, content in data.items():
        if filename == "ground_truth.json":
            continue  # Don't give the baseline the answers!
        all_data_str += f"\n## {filename}\n```json\n{json.dumps(content, indent=2)}\n```\n"

    user_prompt = f"""Incident: {metadata.get('title', 'Unknown')}

Here is ALL the data from the incident:
{all_data_str}

Write the complete post-mortem report."""

    start = time.time()
    result = call_llm(
        system_prompt=BASELINE_PROMPT,
        user_prompt=user_prompt,
        model=MODEL,
        max_tokens=4096,
        temperature=0.2,
    )
    elapsed = time.time() - start

    report_markdown = result["content"]

    # Save output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f"{name}_postmortem.md")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report_markdown)

    # Save trajectory
    trajectory = [{
        "agent": "baseline_single_prompt",
        "step": "single_llm_call",
        "model": result["model"],
        "usage": result["usage"],
        "latency_seconds": result["latency_seconds"],
        "input_length_chars": len(user_prompt),
        "output_length_chars": len(report_markdown),
    }]

    trajectory_file = os.path.join(OUTPUT_DIR, f"{name}_trajectory.json")
    with open(trajectory_file, "w", encoding="utf-8") as f:
        json.dump(trajectory, f, indent=2)

    if verbose:
        print(f"  Done ({elapsed:.1f}s) - Report: {output_file}")
        print(f"  Tokens: {result['usage'].get('total_tokens', 0):,}")

    return {
        "incident_id": metadata.get("incident_id", name),
        "incident_title": metadata.get("title", name),
        "report_markdown": report_markdown,
        "trajectory": trajectory,
        "timing": {"total_seconds": round(elapsed, 1)},
        "token_usage": result["usage"].get("total_tokens", 0),
    }


def run_baseline_all(verbose: bool = True) -> list[dict]:
    """Run baseline on all incidents."""
    incidents = get_incident_dirs()
    results = []

    for num, name, path in incidents:
        try:
            result = run_baseline_single(num, verbose=verbose)
            results.append(result)
        except Exception as e:
            print(f"\nError processing incident {num}: {e}")
            results.append({"incident_id": name, "error": str(e)})

    # Save summary
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    summary_file = os.path.join(OUTPUT_DIR, "summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump([
            {
                "incident_id": r.get("incident_id", "?"),
                "incident_title": r.get("incident_title", "?"),
                "total_seconds": r.get("timing", {}).get("total_seconds", 0),
                "tokens_used": r.get("token_usage", 0),
            }
            for r in results
        ], f, indent=2)

    if verbose:
        print(f"\nBaseline complete. Summary: {summary_file}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the single-prompt baseline")
    parser.add_argument("--incident", required=True, help="Incident number (1-10) or 'all'")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    if args.incident.lower() == "all":
        run_baseline_all(verbose=not args.quiet)
    else:
        try:
            num = int(args.incident)
        except ValueError:
            print(f"Error: --incident must be a number (1-10) or 'all'")
            sys.exit(1)
        run_baseline_single(num, verbose=not args.quiet)
