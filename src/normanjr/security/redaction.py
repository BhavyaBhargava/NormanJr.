"""Redaction utilities for sensitive data, secrets, and credentials."""

from __future__ import annotations

import re
from typing import Any

# Patterns for secrets
API_KEY_PATTERN = re.compile(r"(sk-[a-zA-Z0-9_-]{20,}|or-[a-zA-Z0-9_-]{20,})")
AUTH_HEADER_PATTERN = re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{15,}", re.IGNORECASE)
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
PASSWORD_FIELD_PATTERN = re.compile(r"(password|secret|token|api_key|passwd|auth)\s*[:=]\s*['\"]?([^'\",\s]+)", re.IGNORECASE)


def redact_string(text: str) -> str:
    """Redact sensitive substrings such as tokens, auth headers, and credit cards from a string."""
    if not text:
        return text
    redacted = AUTH_HEADER_PATTERN.sub(r"\1[REDACTED_AUTH_TOKEN]", text)
    redacted = API_KEY_PATTERN.sub("[REDACTED_API_KEY]", redacted)
    redacted = CREDIT_CARD_PATTERN.sub("[REDACTED_CARD_NUMBER]", redacted)
    redacted = PASSWORD_FIELD_PATTERN.sub(r"\1=[REDACTED]", redacted)
    return redacted


def redact_structure(data: Any) -> Any:
    """Recursively redact sensitive keys and values from dictionaries and lists."""
    if isinstance(data, dict):
        cleaned: dict[str, Any] = {}
        for k, v in data.items():
            lower_k = str(k).lower()
            if any(s in lower_k for s in ("password", "secret", "token", "auth", "api_key", "cookie")):
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_structure(v)
        return cleaned
    elif isinstance(data, list):
        return [redact_structure(item) for item in data]
    elif isinstance(data, str):
        return redact_string(data)
    return data
