"""
GitHub Collector — fetches real commits, diffs, PRs, CI check runs, and deployment events.

Supports:
  1. GitHub REST API (with PAT, fine-grained token, or GitHub App)
  2. Pull request review comments and CI status checks
  3. Jira ticket reference cross-extraction
  4. Local git repo fallback (runs `git log` subprocess)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from tools.sanitizer import sanitize_dict, sanitize_text


_GITHUB_API = "https://api.github.com"
TICKET_REGEX = re.compile(r"\b([A-Z]{2,10}-\d+)\b")


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
        return repo_url
    raise ValueError(f"Cannot parse GitHub repo URL: {repo_url}")


def extract_ticket_keys(text: str) -> list[str]:
    """Extract Jira ticket keys (e.g. PROD-1029) from commit message or PR title."""
    return list(set(TICKET_REGEX.findall(text)))


def fetch_commits(
    repo_url: str,
    token: str = "",
    since: str | None = None,
    until: str | None = None,
    max_commits: int = 50,
) -> list[dict]:
    """
    Fetch commits from a GitHub repository with diff summaries and linked ticket references.
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
        raw_msg = rc.get("commit", {}).get("message", "")
        summary_msg = raw_msg.split("\n")[0]

        # Fetch per-commit detail (files changed)
        detail = _fetch_commit_detail(owner_repo, rc["sha"], token)
        ticket_refs = extract_ticket_keys(raw_msg)

        commits.append(sanitize_dict({
            "sha": sha,
            "full_sha": rc.get("sha", ""),
            "timestamp": rc.get("commit", {}).get("author", {}).get("date", ""),
            "author": rc.get("commit", {}).get("author", {}).get("name", "unknown"),
            "author_email": rc.get("commit", {}).get("author", {}).get("email", ""),
            "message": summary_msg,
            "ticket_refs": ticket_refs,
            "files_changed": [f["filename"] for f in detail.get("files", [])],
            "diff_summary": _build_diff_summary(detail.get("files", [])),
            "html_url": rc.get("html_url", f"https://github.com/{owner_repo}/commit/{sha}"),
        }))

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
    summary += "; ".join(parts[:10])
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
    return sanitize_text(resp.text)


def fetch_pull_requests(
    repo_url: str,
    token: str = "",
    state: str = "closed",
    since: str | None = None,
    max_prs: int = 20,
) -> list[dict]:
    """Fetch recent pull requests with reviews and linked ticket references."""
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

        title = pr.get("title", "")
        ticket_refs = extract_ticket_keys(title)
        pr_num = pr.get("number")

        prs.append(sanitize_dict({
            "number": pr_num,
            "title": title,
            "author": pr.get("user", {}).get("login", "unknown"),
            "merged_at": merged_at,
            "merge_commit_sha": pr.get("merge_commit_sha", "")[:7] if pr.get("merge_commit_sha") else "",
            "ticket_refs": ticket_refs,
            "url": pr.get("html_url", ""),
            "draft": pr.get("draft", False),
        }))

    return prs


def fetch_check_runs(repo_url: str, ref: str, token: str = "") -> list[dict]:
    """Fetch CI check runs (GitHub Actions test passes/failures) for a commit ref."""
    owner_repo = _parse_repo(repo_url)
    url = f"{_GITHUB_API}/repos/{owner_repo}/commits/{ref}/check-runs"
    try:
        resp = requests.get(url, headers=_headers(token), timeout=15)
        if resp.status_code == 200:
            checks = []
            for cr in resp.json().get("check_runs", []):
                checks.append({
                    "name": cr.get("name"),
                    "status": cr.get("status"),
                    "conclusion": cr.get("conclusion"),  # success, failure, neutral, timed_out
                    "started_at": cr.get("started_at"),
                    "completed_at": cr.get("completed_at"),
                })
            return checks
    except Exception:
        pass
    return []


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
            "permissions": data.get("permissions", {}),
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"status": "error", "message": "Repository not found or token lacks access"}
        if e.response.status_code == 401:
            return {"status": "error", "message": "Invalid or expired token"}
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def fetch_commits_local(
    repo_path: str,
    since: str | None = None,
    until: str | None = None,
    max_commits: int = 50,
) -> list[dict]:
    """Fetch commits from a local git repository using git log."""
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
            parts = line.split("|||", 3)
            sha = parts[0] if len(parts) > 0 else ""
            ts = parts[1] if len(parts) > 1 else ""
            author = parts[2] if len(parts) > 2 else ""
            msg = parts[3] if len(parts) > 3 else ""
            current_commit = {
                "sha": sha[:7],
                "full_sha": sha,
                "timestamp": ts,
                "author": author,
                "message": msg,
                "ticket_refs": extract_ticket_keys(msg),
                "files_changed": [],
                "diff_summary": "",
            }
        elif line.strip() and current_commit:
            current_commit["files_changed"].append(line.strip())

    if current_commit:
        commits.append(current_commit)

    for c in commits:
        c["diff_summary"] = f"Changed {len(c['files_changed'])} files: {', '.join(c['files_changed'][:5])}"

    return sanitize_dict(commits)
