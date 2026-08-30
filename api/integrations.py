"""
Integrations API — configure and test external tool connections.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import storage
from collectors import github_collector, slack_collector, pagerduty_collector, jira_collector

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class GitHubConfig(BaseModel):
    repo_url: str
    token: str = ""


class SlackConfig(BaseModel):
    bot_token: str
    default_channel: str = ""


class PagerDutyConfig(BaseModel):
    api_key: str


class JiraConfig(BaseModel):
    base_url: str
    email: str
    api_token: str
    default_project: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def list_integrations():
    """List all configured integrations and their status."""
    integrations = storage.list_integrations()

    # Ensure all providers are listed even if not configured
    providers = {"github", "slack", "pagerduty", "jira"}
    configured = {i["provider"] for i in integrations}

    for provider in providers - configured:
        integrations.append({
            "provider": provider,
            "enabled": 0,
            "config": {},
            "last_tested": "",
            "test_result": {},
            "updated_at": "",
        })

    return {"integrations": sorted(integrations, key=lambda x: x["provider"])}


@router.post("/github")
async def configure_github(config: GitHubConfig):
    """Configure GitHub integration."""
    try:
        github_collector._parse_repo(config.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    storage.save_integration(
        provider="github",
        config={"repo_url": config.repo_url},
        credentials={"token": config.token},
    )

    test_result = github_collector.test_connection(config.repo_url, config.token)
    storage.update_integration_test("github", test_result)

    return {"status": "saved", "test_result": test_result}


@router.post("/slack")
async def configure_slack(config: SlackConfig):
    """Configure Slack integration."""
    storage.save_integration(
        provider="slack",
        config={"default_channel": config.default_channel},
        credentials={"bot_token": config.bot_token},
    )

    test_result = slack_collector.test_connection(config.bot_token)
    storage.update_integration_test("slack", test_result)

    return {"status": "saved", "test_result": test_result}


@router.post("/pagerduty")
async def configure_pagerduty(config: PagerDutyConfig):
    """Configure PagerDuty integration."""
    storage.save_integration(
        provider="pagerduty",
        config={},
        credentials={"api_key": config.api_key},
    )

    test_result = pagerduty_collector.test_connection(config.api_key)
    storage.update_integration_test("pagerduty", test_result)

    return {"status": "saved", "test_result": test_result}


@router.post("/jira")
async def configure_jira(config: JiraConfig):
    """Configure Jira integration."""
    storage.save_integration(
        provider="jira",
        config={"base_url": config.base_url, "default_project": config.default_project},
        credentials={"email": config.email, "api_token": config.api_token},
    )

    test_result = jira_collector.test_connection(config.base_url, config.email, config.api_token)
    storage.update_integration_test("jira", test_result)

    return {"status": "saved", "test_result": test_result}


@router.post("/test/{provider}")
async def test_integration(provider: str):
    """Test connectivity for a configured integration."""
    integration = storage.get_integration(provider)
    if not integration:
        raise HTTPException(status_code=404, detail=f"{provider} not configured")

    creds = integration.get("credentials", {})
    config = integration.get("config", {})

    if provider == "github":
        result = github_collector.test_connection(
            config.get("repo_url", ""),
            creds.get("token", ""),
        )
    elif provider == "slack":
        result = slack_collector.test_connection(creds.get("bot_token", ""))
    elif provider == "pagerduty":
        result = pagerduty_collector.test_connection(creds.get("api_key", ""))
    elif provider == "jira":
        result = jira_collector.test_connection(
            config.get("base_url", ""),
            creds.get("email", ""),
            creds.get("api_token", ""),
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    storage.update_integration_test(provider, result)
    return {"test_result": result}


@router.delete("/{provider}")
async def delete_integration(provider: str):
    """Remove an integration."""
    deleted = storage.delete_integration(provider)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"{provider} not configured")
    return {"message": f"{provider} integration removed"}
