"""
Sanitizer Tool — High-performance zero-trust Secret, Token, and PII Redaction Pipeline.

Protects against leaking sensitive tokens, database connection strings, passwords,
and personal identifiable information before data is sent to shared memory or LLMs.
"""

from __future__ import annotations

import re
from typing import Any


# Pre-compiled high-performance secret and credential regex patterns
_SECRET_PATTERNS = [
    # AWS Access Key ID
    (re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    # GitHub Tokens (PAT, OAuth, App)
    (re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}\b"), "[REDACTED_GITHUB_TOKEN]"),
    # Slack Tokens
    (re.compile(r"\bxox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*\b"), "[REDACTED_SLACK_TOKEN]"),
    # OpenAI / Anthropic Keys
    (re.compile(r"\bsk-(?:live-|proj-)?[A-Za-z0-9_-]{20,64}\b"), "[REDACTED_API_KEY]"),
    # Generic Bearer Tokens
    (re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.=:_+/]{20,500}"), "Bearer [REDACTED_BEARER_TOKEN]"),
    # JWT Tokens (header.payload.signature)
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "[REDACTED_JWT_TOKEN]"),
    # Private Key blocks
    (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----[^-]+-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", re.DOTALL), "[REDACTED_PRIVATE_KEY]"),
    # Database Connection Strings (Postgres, MySQL, Mongo, Redis, AMQP)
    (re.compile(r"(?i)\b(postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp(?:s)?):\/\/(?:([^:]+):)?([^@]+)@([^\s\/:]+)(?::(\d+))?(\/[^\s\?]+)?"), r"\1://\2:[REDACTED_PASSWORD]@\4:\5\6"),
    # Generic password / secret assignments in configs/logs
    (re.compile(r'(?i)(["\']?(?:password|passwd|pass|secret|api_key|apikey|access_token|auth_token|private_key|client_secret)["\']?\s*[:=]\s*["\'])([^"\'\s]{3,})([^"\']*)'), r'\1[REDACTED_CREDENTIAL]\3'),
]

# PII Patterns (Credit cards, SSNs)
_PII_PATTERNS = [
    # Credit Card numbers
    (re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"), "[REDACTED_CREDIT_CARD]"),
    # US SSN
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
]


def _is_sensitive_key(key: str) -> bool:
    """Check if dictionary key represents a sensitive credential."""
    k = str(key).lower().strip()
    if k in ("pass", "pwd", "secret", "token", "key", "auth", "credentials", "apikey", "api_key", "password", "passwd", "passphrase"):
        return True
    if any(k.endswith(p) for p in ("_pass", "-pass", "_pwd", "-pwd", "_passwd", "-passwd", "_secret", "-secret", "_token", "-token", "_key", "-key")):
        return True
    return any(sens in k for sens in (
        "password", "passwd", "passphrase", "client_secret", "app_secret", "api_key", "apikey",
        "access_token", "auth_token", "private_key", "credential",
        "authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key",
    ))


def sanitize_text(text: str, redact_pii: bool = True) -> str:
    """
    Sanitize raw text by redacting API tokens, database URIs, passwords, and sensitive PII.
    """
    if not isinstance(text, str) or not text:
        return text

    sanitized = text

    for pattern, replacement in _SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    if redact_pii:
        for pattern, replacement in _PII_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

    return sanitized


def sanitize_dict(data: Any, redact_pii: bool = True) -> Any:
    """
    Recursively sanitize a dictionary, list, or nested object.
    """
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            if _is_sensitive_key(key):
                cleaned[key] = "[REDACTED_CREDENTIAL]"
            else:
                cleaned[key] = sanitize_dict(value, redact_pii=redact_pii)
        return cleaned
    elif isinstance(data, list):
        return [sanitize_dict(item, redact_pii=redact_pii) for item in data]
    elif isinstance(data, str):
        return sanitize_text(data, redact_pii=redact_pii)
    return data


def sanitize_event_payload(payload: dict) -> dict:
    """Convenience helper to sanitize an entire event payload dictionary."""
    return sanitize_dict(payload)
