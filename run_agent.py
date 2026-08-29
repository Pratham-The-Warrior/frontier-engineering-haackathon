"""
Run the multi-agent post-mortem pipeline on one or all incidents.

Usage:
    python run_agent.py --incident 1          # Run on incident 1
    python run_agent.py --incident all        # Run on all incidents
    python run_agent.py --incident 1 --quiet  # Minimal output
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

from agents.orchestrator import run_pipeline

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "incidents")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "agent")


def get_incident_dirs() -> list[tuple[int, str, str]]:
    """Return list of (number, name, path) for all incidents."""
    incidents = []
    if not os.path.exists(DATA_DIR):
        print(f"Error: Data directory not found: {DATA_DIR}")
        print("Run: python data/generate_incidents.py")
        sys.exit(1)

    for name in sorted(os.listdir(DATA_DIR)):
        path = os.path.join(DATA_DIR, name)
        if os.path.isdir(path) and name.startswith("incident_"):
            num = int(name.split("_")[1])
            incidents.append((num, name, path))
    return incidents


def run_single(incident_num: int, verbose: bool = True, interactive: bool = False) -> dict:
    """Run pipeline on a single incident by number."""
    incidents = get_incident_dirs()
    match = [i for i in incidents if i[0] == incident_num]
    if not match:
        print(f"Error: Incident {incident_num} not found. Available: {[i[0] for i in incidents]}")
        sys.exit(1)

    num, name, path = match[0]
    result = run_pipeline(path, verbose=verbose, interactive=interactive)

    # Save outputs
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f"{name}_postmortem.md")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result["report_markdown"])

    trajectory_file = os.path.join(OUTPUT_DIR, f"{name}_trajectory.json")
    with open(trajectory_file, "w", encoding="utf-8") as f:
        json.dump(result["trajectory"], f, indent=2, default=str)

    if verbose:
        print(f"\nOutputs saved:")
        print(f"  Report:     {output_file}")
        print(f"  Trajectory: {trajectory_file}")
        print(f"  Tokens used: {result['token_usage']:,}")
        print(f"  Total time:  {result['timing']['total_seconds']}s")

    return result


def run_all(verbose: bool = True) -> list[dict]:
    """Run pipeline on all incidents."""
    incidents = get_incident_dirs()
    results = []

    for num, name, path in incidents:
        try:
            result = run_single(num, verbose=verbose)
            results.append(result)
        except Exception as e:
            print(f"\nError processing incident {num}: {e}")
            results.append({"incident_id": name, "error": str(e)})

    # Save summary
    summary_file = os.path.join(OUTPUT_DIR, "summary.json")
    summary = []
    for r in results:
        if "error" not in r:
            summary.append({
                "incident_id": r["incident_id"],
                "incident_title": r["incident_title"],
                "root_cause_summary": r["root_cause_summary"],
                "blameless_score": r["quality_scores"]["blameless_score"],
                "completeness_score": r["quality_scores"]["completeness_score"],
                "total_seconds": r["timing"]["total_seconds"],
                "tokens_used": r["token_usage"],
            })
        else:
            summary.append(r)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    if verbose:
        print(f"\n{'='*60}")
        print(f"  ALL INCIDENTS COMPLETE")
        print(f"{'='*60}")
        print(f"  Summary saved to: {summary_file}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the post-mortem agent pipeline")
    parser.add_argument("--incident", required=True, help="Incident number (1-10) or 'all'")
    parser.add_argument("--interactive", action="store_true", help="Enable human-in-the-loop approval checkpoint")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    if args.incident.lower() == "all":
        run_all(verbose=not args.quiet)
    else:
        try:
            num = int(args.incident)
        except ValueError:
            print(f"Error: --incident must be a number (1-10) or 'all'")
            sys.exit(1)
        run_single(num, verbose=not args.quiet, interactive=args.interactive)
