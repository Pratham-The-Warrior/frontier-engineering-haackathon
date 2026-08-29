"""
Run evaluation on both baseline and agent outputs.

Compares outputs against ground truth for all incidents.

Usage:
    python run_evaluation.py
    python run_evaluation.py --incident 1
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

from evaluation.metrics import evaluate_report

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "incidents")
AGENT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "agent")
BASELINE_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "baseline")
EVAL_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "evaluation", "results")


def get_incident_dirs() -> list[tuple[int, str, str]]:
    incidents = []
    for name in sorted(os.listdir(DATA_DIR)):
        path = os.path.join(DATA_DIR, name)
        if os.path.isdir(path) and name.startswith("incident_"):
            num = int(name.split("_")[1])
            incidents.append((num, name, path))
    return incidents


def load_ground_truth(incident_dir: str) -> dict:
    gt_path = os.path.join(incident_dir, "ground_truth.json")
    with open(gt_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_report(output_dir: str, incident_name: str) -> str | None:
    report_path = os.path.join(output_dir, f"{incident_name}_postmortem.md")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def evaluate_single(incident_num: int, verbose: bool = True) -> dict:
    """Evaluate both baseline and agent for a single incident."""
    incidents = get_incident_dirs()
    match = [i for i in incidents if i[0] == incident_num]
    if not match:
        print(f"Error: Incident {incident_num} not found.")
        return {}

    num, name, path = match[0]
    gt = load_ground_truth(path)

    results = {"incident_id": num, "incident_name": name}

    # Evaluate agent output
    agent_report = load_report(AGENT_OUTPUT_DIR, name)
    if agent_report:
        if verbose:
            print(f"\n  Evaluating AGENT output for incident {num}...")
        results["agent"] = evaluate_report(agent_report, gt)
        if verbose:
            print(f"    Weighted score: {results['agent']['weighted_score']}")
    else:
        if verbose:
            print(f"  No agent output found for incident {num}")
        results["agent"] = None

    # Evaluate baseline output
    baseline_report = load_report(BASELINE_OUTPUT_DIR, name)
    if baseline_report:
        if verbose:
            print(f"  Evaluating BASELINE output for incident {num}...")
        results["baseline"] = evaluate_report(baseline_report, gt)
        if verbose:
            print(f"    Weighted score: {results['baseline']['weighted_score']}")
    else:
        if verbose:
            print(f"  No baseline output found for incident {num}")
        results["baseline"] = None

    return results


def evaluate_all(verbose: bool = True) -> list[dict]:
    """Evaluate all incidents and produce comparison table."""
    incidents = get_incident_dirs()
    all_results = []

    for num, name, path in incidents:
        if verbose:
            print(f"\n{'='*50}")
            print(f"  Incident {num}: {name}")
        try:
            result = evaluate_single(num, verbose=verbose)
            all_results.append(result)
        except Exception as e:
            print(f"  Error evaluating incident {num}: {e}")
            all_results.append({"incident_id": num, "error": str(e)})

    # Save results
    os.makedirs(EVAL_OUTPUT_DIR, exist_ok=True)
    results_file = os.path.join(EVAL_OUTPUT_DIR, "evaluation_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)

    # Print comparison table
    if verbose:
        _print_comparison_table(all_results)

    # Save comparison table as markdown
    table_file = os.path.join(EVAL_OUTPUT_DIR, "comparison_table.md")
    with open(table_file, "w", encoding="utf-8") as f:
        f.write(_generate_comparison_markdown(all_results))

    if verbose:
        print(f"\nResults saved to: {results_file}")
        print(f"Comparison table: {table_file}")

    return all_results


def _print_comparison_table(results: list[dict]) -> None:
    """Print a comparison table to console."""
    print(f"\n{'='*80}")
    print(f"  EVALUATION RESULTS: Baseline vs. Agent")
    print(f"{'='*80}")
    print(f"{'Incident':<12} {'Baseline':>10} {'Agent':>10} {'Improvement':>12}")
    print(f"{'-'*12} {'-'*10} {'-'*10} {'-'*12}")

    baseline_scores = []
    agent_scores = []

    for r in results:
        if "error" in r:
            continue
        inc = f"INC-{r['incident_id']:03d}"
        b_score = r.get("baseline", {}).get("weighted_score", 0) if r.get("baseline") else 0
        a_score = r.get("agent", {}).get("weighted_score", 0) if r.get("agent") else 0
        improvement = a_score - b_score

        baseline_scores.append(b_score)
        agent_scores.append(a_score)

        sign = "+" if improvement > 0 else ""
        print(f"{inc:<12} {b_score:>10.1f} {a_score:>10.1f} {sign}{improvement:>11.1f}")

    if baseline_scores and agent_scores:
        avg_b = sum(baseline_scores) / len(baseline_scores)
        avg_a = sum(agent_scores) / len(agent_scores)
        avg_imp = avg_a - avg_b
        print(f"{'-'*12} {'-'*10} {'-'*10} {'-'*12}")
        sign = "+" if avg_imp > 0 else ""
        print(f"{'AVERAGE':<12} {avg_b:>10.1f} {avg_a:>10.1f} {sign}{avg_imp:>11.1f}")


def _generate_comparison_markdown(results: list[dict]) -> str:
    """Generate comparison table as markdown."""
    lines = [
        "# Evaluation Results: Baseline vs. Multi-Agent Pipeline\n",
        "| Incident | Baseline Score | Agent Score | Improvement |",
        "|----------|---------------|-------------|-------------|",
    ]

    baseline_scores = []
    agent_scores = []

    for r in results:
        if "error" in r:
            continue
        inc = f"INC-{r['incident_id']:03d}"
        b = r.get("baseline", {}).get("weighted_score", 0) if r.get("baseline") else 0
        a = r.get("agent", {}).get("weighted_score", 0) if r.get("agent") else 0
        imp = a - b
        sign = "+" if imp > 0 else ""
        lines.append(f"| {inc} | {b:.1f} | {a:.1f} | {sign}{imp:.1f} |")
        baseline_scores.append(b)
        agent_scores.append(a)

    if baseline_scores and agent_scores:
        avg_b = sum(baseline_scores) / len(baseline_scores)
        avg_a = sum(agent_scores) / len(agent_scores)
        avg_imp = avg_a - avg_b
        sign = "+" if avg_imp > 0 else ""
        lines.append(f"| **AVERAGE** | **{avg_b:.1f}** | **{avg_a:.1f}** | **{sign}{avg_imp:.1f}** |")

    lines.append("\n## Detailed Metrics\n")

    for r in results:
        if "error" in r or not r.get("agent"):
            continue
        inc = f"INC-{r['incident_id']:03d}"
        agent = r["agent"]
        lines.append(f"### {inc}\n")
        lines.append(f"- Root Cause Accuracy: {agent.get('root_cause_accuracy', {}).get('accuracy', 'N/A')}")
        lines.append(f"- Timeline Recall: {agent.get('timeline_recall', {}).get('recall', 'N/A')}")
        lines.append(f"- Contributing Factors Recall: {agent.get('contributing_factors_recall', {}).get('recall', 'N/A')}")
        lines.append(f"- Blameless Score: {agent.get('blameless_score', {}).get('score', 'N/A')}/100")
        lines.append(f"- Completeness Score: {agent.get('completeness_score', {}).get('score', 'N/A')}/100")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run evaluation")
    parser.add_argument("--incident", default="all", help="Incident number or 'all'")
    args = parser.parse_args()

    if args.incident.lower() == "all":
        evaluate_all()
    else:
        try:
            num = int(args.incident)
        except ValueError:
            print("Error: --incident must be a number or 'all'")
            sys.exit(1)
        evaluate_single(num)
