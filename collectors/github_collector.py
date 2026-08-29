"""
GitHub Collector — fetches real commits, diffs, and PRs from GitHub repos.

Supports:
  1. GitHub REST API (with PAT or fine-grained token)
  2. Local git repo fallback (runs `git log` subprocess)

Output matches the existing git_commits.json schema so agents work unchanged.
"""

from __future__ import annotations

import json
import subprocess
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests


# ---------------------------------------------------------------------------
# GitHub REST API collector
# ---------------------------------------------------------------------------

_GITHUB_API = "https://api.github.com"


def _headers(token: str) -> dict:
    h = {"Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _parse_repo(repo_url: str) -> str:
    """Extract 'owner/repo' from various URL formats."""
    repo_url = repo_url.rstrip("/")
    if repo_url.startswith("https://github.com/"):
        parts = repo_url.replace("https://github.com/", "").split("/")
        return f"{parts[0]}/{parts[1].replace('.git', '')}"
    if "/" in repo_url and not repo_url.startswith("http"):
        return repo_url  # already owner/repo
    raise ValueError(f"Cannot parse GitHub repo URL: {repo_url}")


def fetch_commits(
    repo_url: str,
    token: str = "",
    since: str | None = None,
    until: str | None = None,
    max_commits: int = 50,
) -> list[dict]:
    """
    Fetch commits from a GitHub repository.

    Args:
        repo_url: GitHub repo URL or 'owner/repo'
        token: GitHub Personal Access Token (optional for public repos)
        since: ISO timestamp — only commits after this date
        until: ISO timestamp — only commits before this date
        max_commits: Maximum number of commits to fetch

    Returns:
        List of commits in the standard schema:
        [{sha, timestamp, author, message, files_changed, diff_summary}]
    """
    owner_repo = _parse_repo(repo_url)
    url = f"{_GITHUB_API}/repos/{owner_repo}/commits"

    params: dict[str, Any] = {"per_page": min(max_commits, 100)}
    if since:
        params["since"] = since
    if until:
        params["until"] = until

    resp = requests.get(url, headers=_headers(token), params=params, timeout=30)
    resp.raise_for_status()
    raw_commits = resp.json()

    commits = []
    for rc in raw_commits[:max_commits]:
        sha = rc.get("sha", "")[:7]

        # Fetch per-commit detail (files changed)
        detail = _fetch_commit_detail(owner_repo, rc["sha"], token)

        commits.append({
            "sha": sha,
            "timestamp": rc.get("commit", {}).get("author", {}).get("date", ""),
            "author": rc.get("commit", {}).get("author", {}).get("name", "unknown"),
            "message": rc.get("commit", {}).get("message", "").split("\n")[0],
            "files_changed": [f["filename"] for f in detail.get("files", [])],
            "diff_summary": _build_diff_summary(detail.get("files", [])),
        })

    return commits


def _fetch_commit_detail(owner_repo: str, sha: str, token: str) -> dict:
    """Fetch detailed commit info including files changed."""
    url = f"{_GITHUB_API}/repos/{owner_repo}/commits/{sha}"
    try:
        resp = requests.get(url, headers=_headers(token), timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def _build_diff_summary(files: list[dict]) -> str:
    """Build a human-readable diff summary from the commit's file list."""
    if not files:
        return "No file changes available."

    parts = []
    total_add = 0
    total_del = 0
    for f in files:
        status = f.get("status", "modified")
        adds = f.get("additions", 0)
        dels = f.get("deletions", 0)
        total_add += adds
        total_del += dels
        parts.append(f"{f['filename']} ({status}: +{adds}/-{dels})")

    summary = f"Changed {len(files)} files (+{total_add}/-{total_del}): "
    summary += "; ".join(parts[:10])  # cap at 10 files
    if len(parts) > 10:
        summary += f" ... and {len(parts) - 10} more"
    return summary


def fetch_commit_diff(repo_url: str, sha: str, token: str = "") -> str:
    """Fetch the raw diff for a specific commit."""
    owner_repo = _parse_repo(repo_url)
    url = f"{_GITHUB_API}/repos/{owner_repo}/commits/{sha}"
    headers = _headers(token)
    headers["Accept"] = "application/vnd.github.diff"

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_pull_requests(
    repo_url: str,
    token: str = "",
    state: str = "closed",
    since: str | None = None,
    max_prs: int = 20,
) -> list[dict]:
    """Fetch recent pull requests."""
    owner_repo = _parse_repo(repo_url)
    url = f"{_GITHUB_API}/repos/{owner_repo}/pulls"

    params: dict[str, Any] = {
        "state": state,
        "sort": "updated",
        "direction": "desc",
        "per_page": min(max_prs, 100),
    }

    resp = requests.get(url, headers=_headers(token), params=params, timeout=30)
    resp.raise_for_status()
    raw_prs = resp.json()

    prs = []
    for pr in raw_prs:
        merged_at = pr.get("merged_at", "")
        if since and merged_at and merged_at < since:
            continue
        prs.append({
            "number": pr.get("number"),
            "title": pr.get("title", ""),
            "author": pr.get("user", {}).get("login", "unknown"),
            "merged_at": merged_at,
            "url": pr.get("html_url", ""),
        })

    return prs


def test_connection(repo_url: str, token: str = "") -> dict:
    """Test GitHub connectivity and return repo info."""
    owner_repo = _parse_repo(repo_url)
    url = f"{_GITHUB_API}/repos/{owner_repo}"

    try:
        resp = requests.get(url, headers=_headers(token), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            "status": "connected",
            "repo": data.get("full_name", ""),
            "private": data.get("private", False),
            "default_branch": data.get("default_branch", "main"),
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"status": "error", "message": "Repository not found or token lacks access"}
        if e.response.status_code == 401:
            return {"status": "error", "message": "Invalid or expired token"}
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Local git fallback
# ---------------------------------------------------------------------------

def fetch_commits_local(
    repo_path: str,
    since: str | None = None,
    until: str | None = None,
    max_commits: int = 50,
) -> list[dict]:
    """
    Fetch commits from a local git repository using `git log`.

    Args:
        repo_path: Absolute path to a local git repository
        since: ISO timestamp — commits after this date
        until: ISO timestamp — commits before this date
        max_commits: Maximum number of commits

    Returns:
        Same schema as fetch_commits()
    """
    cmd = [
        "git", "-C", repo_path, "log",
        f"-{max_commits}",
        "--pretty=format:%H|||%aI|||%an|||%s",
        "--name-only",
    ]
    if since:
        cmd.append(f"--since={since}")
    if until:
        cmd.append(f"--until={until}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"git log failed: {result.stderr}")
    except FileNotFoundError:
        raise RuntimeError("git is not installed or not on PATH")

    commits = []
    current_commit = None

    for line in result.stdout.split("\n"):
        if "|||" in line:
            if current_commit:
                commits.append(current_commit)
            parts = line.split("|||")
            current_commit = {
                "sha": parts[0][:7],
                "timestamp": parts[1],
                "author": parts[2],
                "message": parts[3],
                "files_changed": [],
                "diff_summary": "",
            }
        elif line.strip() and current_commit:
            current_commit["files_changed"].append(line.strip())

    if current_commit:
        commits.append(current_commit)

    # Build diff summaries
    for c in commits:
        c["diff_summary"] = f"Changed {len(c['files_changed'])} files: {', '.join(c['files_changed'][:5])}"

    return commits
