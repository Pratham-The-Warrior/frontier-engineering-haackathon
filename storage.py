"""
Storage layer — SQLite database for incidents, reports, and integration configs.

Zero-config: database file is auto-created on first run.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from cryptography.fernet import Fernet

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "postmortem.db")
_KEY_PATH = os.path.join(os.path.dirname(__file__), "data", ".encryption_key")


def _get_fernet() -> Fernet:
    """Get or create encryption key for sensitive credentials."""
    os.makedirs(os.path.dirname(_KEY_PATH), exist_ok=True)
    if os.path.exists(_KEY_PATH):
        with open(_KEY_PATH, "rb") as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(_KEY_PATH, "wb") as f:
            f.write(key)
    return Fernet(key)


def _get_conn() -> sqlite3.Connection:
    """Get a database connection with row_factory."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables on first run."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS incidents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            severity TEXT DEFAULT 'unknown',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            incident_time TEXT DEFAULT '',
            config TEXT DEFAULT '{}',
            sources_used TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            incident_id TEXT NOT NULL,
            report_markdown TEXT NOT NULL,
            quality_scores TEXT DEFAULT '{}',
            root_cause_summary TEXT DEFAULT '',
            trajectory TEXT DEFAULT '[]',
            timing TEXT DEFAULT '{}',
            token_usage INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS integrations (
            provider TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            config TEXT DEFAULT '{}',
            credentials TEXT DEFAULT '',
            last_tested TEXT DEFAULT '',
            test_result TEXT DEFAULT '{}',
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id TEXT PRIMARY KEY,
            incident_id TEXT NOT NULL,
            status TEXT DEFAULT 'running',
            current_phase TEXT DEFAULT '',
            progress INTEGER DEFAULT 0,
            log TEXT DEFAULT '[]',
            started_at TEXT NOT NULL,
            completed_at TEXT DEFAULT '',
            error TEXT DEFAULT '',
            FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Incidents CRUD
# ---------------------------------------------------------------------------

def create_incident(title: str, config: dict = None, severity: str = "unknown", incident_time: str = "") -> dict:
    """Create a new incident record."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"

    conn.execute(
        "INSERT INTO incidents (id, title, status, severity, created_at, updated_at, incident_time, config) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (incident_id, title, "pending", severity, now, now, incident_time, json.dumps(config or {})),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    conn.close()
    return dict(row)


def get_incident(incident_id: str) -> dict | None:
    """Get a single incident."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_incidents() -> list[dict]:
    """List all incidents, newest first."""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM incidents ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_incident(incident_id: str, **kwargs) -> dict | None:
    """Update incident fields."""
    conn = _get_conn()
    kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [incident_id]
    conn.execute(f"UPDATE incidents SET {sets} WHERE id = ?", vals)
    conn.commit()
    row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_incident(incident_id: str) -> bool:
    """Delete an incident and its associated data."""
    conn = _get_conn()
    conn.execute("DELETE FROM incidents WHERE id = ?", (incident_id,))
    affected = conn.total_changes
    conn.commit()
    conn.close()
    return affected > 0


# ---------------------------------------------------------------------------
# Reports CRUD
# ---------------------------------------------------------------------------

def save_report(incident_id: str, result: dict) -> dict:
    """Save a pipeline result as a report."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"

    conn.execute(
        "INSERT INTO reports (id, incident_id, report_markdown, quality_scores, root_cause_summary, trajectory, timing, token_usage, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            report_id,
            incident_id,
            result.get("report_markdown", ""),
            json.dumps(result.get("quality_scores", {})),
            result.get("root_cause_summary", ""),
            json.dumps(result.get("trajectory", []), default=str),
            json.dumps(result.get("timing", {})),
            result.get("token_usage", 0),
            now,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    return dict(row)


def get_report(incident_id: str) -> dict | None:
    """Get the latest report for an incident."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM reports WHERE incident_id = ? ORDER BY created_at DESC LIMIT 1",
        (incident_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Integrations
# ---------------------------------------------------------------------------

def save_integration(provider: str, config: dict, credentials: dict) -> dict:
    """Save or update an integration configuration with encrypted credentials."""
    conn = _get_conn()
    fernet = _get_fernet()
    now = datetime.now(timezone.utc).isoformat()

    encrypted_creds = fernet.encrypt(json.dumps(credentials).encode()).decode()

    conn.execute(
        """INSERT OR REPLACE INTO integrations
           (provider, enabled, config, credentials, updated_at)
           VALUES (?, 1, ?, ?, ?)""",
        (provider, json.dumps(config), encrypted_creds, now),
    )
    conn.commit()
    conn.close()
    return {"provider": provider, "status": "saved"}


def get_integration(provider: str) -> dict | None:
    """Get an integration config with decrypted credentials."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM integrations WHERE provider = ?", (provider,)).fetchone()
    conn.close()

    if not row:
        return None

    result = dict(row)
    if result.get("credentials"):
        try:
            fernet = _get_fernet()
            result["credentials"] = json.loads(
                fernet.decrypt(result["credentials"].encode()).decode()
            )
        except Exception:
            result["credentials"] = {}

    result["config"] = json.loads(result.get("config", "{}"))
    return result


def list_integrations() -> list[dict]:
    """List all integrations (credentials masked)."""
    conn = _get_conn()
    rows = conn.execute("SELECT provider, enabled, config, last_tested, test_result, updated_at FROM integrations").fetchall()
    conn.close()

    results = []
    for r in rows:
        d = dict(r)
        d["config"] = json.loads(d.get("config", "{}"))
        d["test_result"] = json.loads(d.get("test_result", "{}"))
        results.append(d)
    return results


def delete_integration(provider: str) -> bool:
    """Delete an integration."""
    conn = _get_conn()
    conn.execute("DELETE FROM integrations WHERE provider = ?", (provider,))
    affected = conn.total_changes
    conn.commit()
    conn.close()
    return affected > 0


def update_integration_test(provider: str, test_result: dict):
    """Update the test result for an integration."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE integrations SET last_tested = ?, test_result = ? WHERE provider = ?",
        (now, json.dumps(test_result), provider),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Pipeline runs (for live status tracking)
# ---------------------------------------------------------------------------

def create_pipeline_run(incident_id: str) -> str:
    """Create a pipeline run record, return its ID."""
    conn = _get_conn()
    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO pipeline_runs (id, incident_id, status, started_at) VALUES (?, ?, 'running', ?)",
        (run_id, incident_id, now),
    )
    conn.commit()
    conn.close()
    return run_id


def update_pipeline_run(run_id: str, **kwargs):
    """Update a pipeline run's status/progress."""
    conn = _get_conn()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [run_id]
    conn.execute(f"UPDATE pipeline_runs SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def get_pipeline_run(incident_id: str) -> dict | None:
    """Get the latest pipeline run for an incident."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM pipeline_runs WHERE incident_id = ? ORDER BY started_at DESC LIMIT 1",
        (incident_id,),
    ).fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["log"] = json.loads(result.get("log", "[]"))
        return result
    return None


# Initialize on import
init_db()
