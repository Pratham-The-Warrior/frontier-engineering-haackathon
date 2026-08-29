"""
Incidents API — create, list, view, and manage incident analyses.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel

import storage
from collectors import github_collector, slack_collector, pagerduty_collector, log_collector

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateIncidentRequest(BaseModel):
    title: str
    severity: str = "P2"
    incident_time: str = ""
    time_window_hours: int = 24
    github_repo: str = ""
    slack_channel: str = ""
    slack_thread_ts: str = ""
    pagerduty_incident_id: str = ""
    # Manual data fallbacks
    logs_text: str = ""
    slack_text: str = ""
    alerts_json: str = ""


# ---------------------------------------------------------------------------
# Background pipeline runner
# ---------------------------------------------------------------------------

def _run_pipeline_background(incident_id: str, config: dict):
    """Run the full pipeline in a background thread."""
    from agents.orchestrator import run_pipeline_from_sources

    run_id = storage.create_pipeline_run(incident_id)

    try:
        storage.update_pipeline_run(run_id, status="collecting", current_phase="Collecting data from sources", progress=10)
        storage.update_incident(incident_id, status="collecting")

        result = run_pipeline_from_sources(
            config=config,
            progress_callback=lambda phase, pct: storage.update_pipeline_run(
                run_id, current_phase=phase, progress=pct
            ),
        )

        # Save report
        storage.save_report(incident_id, result)
        storage.update_incident(
            incident_id,
            status="completed",
            sources_used=json.dumps(result.get("sources_used", [])),
        )
        storage.update_pipeline_run(
            run_id,
            status="completed",
            current_phase="Report generated",
            progress=100,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        storage.update_incident(incident_id, status="failed")
        storage.update_pipeline_run(
            run_id,
            status="failed",
            error=str(e),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("")
async def create_incident(req: CreateIncidentRequest, background_tasks: BackgroundTasks):
    """Create a new incident and trigger the analysis pipeline."""
    incident = storage.create_incident(
        title=req.title,
        severity=req.severity,
        incident_time=req.incident_time,
        config={
            "github_repo": req.github_repo,
            "slack_channel": req.slack_channel,
            "slack_thread_ts": req.slack_thread_ts,
            "pagerduty_incident_id": req.pagerduty_incident_id,
            "time_window_hours": req.time_window_hours,
            "incident_time": req.incident_time,
            "logs_text": req.logs_text,
            "slack_text": req.slack_text,
            "alerts_json": req.alerts_json,
        },
    )

    # Launch pipeline in background
    background_tasks.add_task(
        _run_pipeline_background,
        incident["id"],
        json.loads(incident["config"]),
    )

    return {"incident": incident, "message": "Pipeline started"}


@router.post("/upload")
async def create_incident_with_upload(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    severity: str = Form("P2"),
    incident_time: str = Form(""),
    time_window_hours: int = Form(24),
    github_repo: str = Form(""),
    log_file: UploadFile | None = File(None),
    slack_file: UploadFile | None = File(None),
    alerts_file: UploadFile | None = File(None),
):
    """Create an incident with file uploads for logs, slack messages, and alerts."""
    logs_text = ""
    slack_text = ""
    alerts_json = ""

    if log_file:
        content = await log_file.read()
        logs_text = content.decode("utf-8", errors="replace")

    if slack_file:
        content = await slack_file.read()
        slack_text = content.decode("utf-8", errors="replace")

    if alerts_file:
        content = await alerts_file.read()
        alerts_json = content.decode("utf-8", errors="replace")

    incident = storage.create_incident(
        title=title,
        severity=severity,
        incident_time=incident_time,
        config={
            "github_repo": github_repo,
            "time_window_hours": time_window_hours,
            "incident_time": incident_time,
            "logs_text": logs_text,
            "slack_text": slack_text,
            "alerts_json": alerts_json,
        },
    )

    background_tasks.add_task(
        _run_pipeline_background,
        incident["id"],
        json.loads(incident["config"]),
    )

    return {"incident": incident, "message": "Pipeline started with uploaded files"}


@router.get("")
async def list_incidents():
    """List all incidents."""
    incidents = storage.list_incidents()
    # Attach report status
    for inc in incidents:
        report = storage.get_report(inc["id"])
        inc["has_report"] = report is not None
        if report:
            scores = json.loads(report.get("quality_scores", "{}"))
            inc["quality_scores"] = scores
            inc["root_cause_summary"] = report.get("root_cause_summary", "")
        run = storage.get_pipeline_run(inc["id"])
        inc["pipeline"] = {
            "status": run["status"] if run else "none",
            "progress": run["progress"] if run else 0,
            "current_phase": run["current_phase"] if run else "",
        }
    return {"incidents": incidents}


@router.get("/{incident_id}")
async def get_incident(incident_id: str):
    """Get a specific incident with its report."""
    incident = storage.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    report = storage.get_report(incident_id)
    run = storage.get_pipeline_run(incident_id)

    return {
        "incident": incident,
        "report": report,
        "pipeline": run,
    }


@router.get("/{incident_id}/report")
async def get_report(incident_id: str):
    """Get just the markdown report for an incident."""
    report = storage.get_report(incident_id)
    if not report:
        raise HTTPException(status_code=404, detail="No report found for this incident")
    return {"report_markdown": report["report_markdown"]}


@router.get("/{incident_id}/status")
async def get_pipeline_status(incident_id: str):
    """Get the live pipeline status for an incident."""
    run = storage.get_pipeline_run(incident_id)
    if not run:
        return {"status": "none", "progress": 0}
    return run


@router.delete("/{incident_id}")
async def delete_incident(incident_id: str):
    """Delete an incident and all associated data."""
    deleted = storage.delete_incident(incident_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"message": "Incident deleted"}
