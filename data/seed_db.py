"""
Seed SQLite database with all 11 incident reports for rich UI experience.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import storage
from agents.orchestrator import run_pipeline

DATA_DIR = os.path.join(os.path.dirname(__file__), "incidents")


def seed_database():
    storage.init_db()
    existing_incidents = {i["title"] for i in storage.list_incidents()}

    for name in sorted(os.listdir(DATA_DIR)):
        path = os.path.join(DATA_DIR, name)
        if not os.path.isdir(path) or not name.startswith("incident_"):
            continue

        meta_file = os.path.join(path, "metadata.json")
        if not os.path.exists(meta_file):
            continue

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        title = meta.get("title", name)
        severity = meta.get("severity", "P2")
        inc_time = meta.get("start_time", meta.get("incident_time", ""))

        # Check if already seeded
        if title in existing_incidents:
            print(f"Skipping already seeded: {title}")
            continue

        print(f"Seeding incident & generating report: {title}...")
        incident = storage.create_incident(
            title=title,
            severity=severity,
            incident_time=inc_time,
            config={"incident_dir": path},
        )

        result = run_pipeline(path, verbose=False)
        storage.save_report(incident["id"], result)
        storage.update_incident(
            incident["id"],
            status="completed",
            sources_used=json.dumps(["logs", "slack", "git", "alerts", "jira"]),
        )
        print(f"  -> Saved as {incident['id']}")

    print("\nDatabase seeding complete!")


if __name__ == "__main__":
    seed_database()
