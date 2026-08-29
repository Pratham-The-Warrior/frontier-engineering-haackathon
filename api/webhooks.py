"""
Webhook receivers — auto-trigger pipeline from PagerDuty, Slack, etc.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Request, BackgroundTasks

import storage

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/pagerduty")
async def pagerduty_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive PagerDuty incident.resolve webhook events.
    Auto-triggers post-mortem generation.
    """
    payload = await request.json()
    event = payload.get("event", {})
    event_type = event.get("event_type", "")

    # Only trigger on incident resolution
    if event_type != "incident.resolved":
        return {"status": "ignored", "event_type": event_type}

    incident_data = event.get("data", {})
    pd_incident_id = incident_data.get("id", "")
    title = incident_data.get("title", "PagerDuty Incident")
    service = incident_data.get("service", {}).get("summary", "")

    # Create incident and trigger pipeline
    incident = storage.create_incident(
        title=f"{title} ({service})",
        severity="P1",
        config={
            "pagerduty_incident_id": pd_incident_id,
            "auto_triggered": True,
            "incident_time": incident_data.get("created_at", ""),
        },
    )

    # Import here to avoid circular imports
    from api.incidents import _run_pipeline_background

    background_tasks.add_task(
        _run_pipeline_background,
        incident["id"],
        json.loads(incident["config"]),
    )

    return {
        "status": "triggered",
        "incident_id": incident["id"],
        "pd_incident_id": pd_incident_id,
        "message": f"Post-mortem generation started for: {title}",
    }


@router.post("/slack")
async def slack_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive Slack slash command (/postmortem) or event.
    Slash command payload is form-encoded.
    """
    content_type = request.headers.get("content-type", "")

    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        data = dict(form)
    else:
        data = await request.json()

    # Handle Slack URL verification challenge
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge", "")}

    # Handle slash command
    command = data.get("command", "")
    text = data.get("text", "").strip()
    channel_id = data.get("channel_id", "")

    if command == "/postmortem" or "postmortem" in text.lower():
        title = text if text else f"Incident from #{data.get('channel_name', 'unknown')}"

        incident = storage.create_incident(
            title=title,
            config={
                "slack_channel": channel_id,
                "auto_triggered": True,
                "incident_time": datetime.now(timezone.utc).isoformat(),
            },
        )

        from api.incidents import _run_pipeline_background

        background_tasks.add_task(
            _run_pipeline_background,
            incident["id"],
            json.loads(incident["config"]),
        )

        return {
            "response_type": "in_channel",
            "text": f"🔍 Post-mortem generation started for: *{title}*\nIncident ID: `{incident['id']}`\nView progress at your dashboard.",
        }

    return {"response_type": "ephemeral", "text": "Usage: /postmortem [incident title]"}
