"""
Agent 2: Communications Analyzer
Analyses Slack incident-response threads to extract human decisions and actions.
"""

from __future__ import annotations

import json
from typing import Any

from agents.llm_client import call_llm_json, MODEL_MINI

SYSTEM_PROMPT = """\
You are an expert incident communication analyst. Your job is to analyze
Slack/chat threads from incident response and extract the human side of the story.

You will receive a Slack thread from an incident response channel.

Your task is to produce a JSON analysis with these fields:

{
  "participants": [
    {
      "name": "person name",
      "role": "their role",
      "key_actions": ["list of significant actions they took"]
    }
  ],
  "key_decisions": [
    {
      "timestamp": "when the decision was made",
      "decision": "what was decided",
      "made_by": "who made it",
      "rationale": "why, if stated"
    }
  ],
  "manual_actions": [
    {
      "timestamp": "when",
      "action": "what was done",
      "by": "who did it",
      "result": "what happened after"
    }
  ],
  "communication_timeline": [
    {
      "timestamp": "ISO timestamp",
      "description": "what was communicated or discovered"
    }
  ],
  "investigation_path": "How did the team arrive at the root cause? What clues did they follow?",
  "time_to_identify_minutes": "approximate minutes from first alert to root cause identification",
  "comms_summary": "2-3 sentence summary of the incident response from the human perspective"
}

Rules:
- Extract ONLY information explicitly stated in the messages.
- Pay attention to the sequence of discovery — what did people check first?
- Note when someone identifies the root cause and what evidence led them there.
- Capture any decisions about mitigation strategy (rollback vs. hotfix vs. other).
- Use blameless language — focus on what the team did, not who messed up.
"""


def run(slack_data: list[dict], trajectory: list[dict] | None = None) -> dict:
    """
    Run the Communications Analyzer agent on Slack thread data.

    Args:
        slack_data: Slack messages (list of dicts with timestamp, user, role, message)
        trajectory: Mutable list to append trajectory steps to

    Returns:
        Structured communication analysis (dict)
    """
    if trajectory is None:
        trajectory = []

    # Format Slack thread for the LLM
    formatted_thread = []
    for msg in sorted(slack_data, key=lambda m: m.get("timestamp", "")):
        formatted_thread.append(
            f"[{msg.get('timestamp', '?')}] {msg.get('user', '?')} ({msg.get('role', '?')}): {msg.get('message', '')}"
        )

    user_prompt = f"""Analyze this incident response Slack thread:

```
{chr(10).join(formatted_thread)}
```

There are {len(slack_data)} messages from {len({m.get('user') for m in slack_data})} participants.

Produce your structured JSON analysis."""

    trajectory.append({
        "agent": "comms_analyzer",
        "step": "llm_analysis",
        "input_messages": len(slack_data),
        "input_participants": len({m.get("user") for m in slack_data}),
    })

    result = call_llm_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=MODEL_MINI,
        max_tokens=2048,
    )

    trajectory.append({
        "agent": "comms_analyzer",
        "step": "llm_response",
        "model": result["model"],
        "usage": result["usage"],
        "latency_seconds": result["latency_seconds"],
    })

    findings = result["parsed"]
    findings["_trajectory"] = trajectory
    return findings
