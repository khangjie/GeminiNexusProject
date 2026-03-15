from __future__ import annotations

import re

from fastapi import HTTPException, status

from app.core.config import get_settings

INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"reveal\s+(the\s+)?(system|developer)\s+prompt",
    r"bypass\s+(safety|guardrails)",
    r"print\s+your\s+instructions",
    r"api\s*key",
    r"secret\s*key",
    r"access\s*token",
    r"password",
]


def _normalize_text(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[\x00-\x1f\x7f]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value


def _block_if_suspicious(value: str, field_name: str) -> None:
    lower = value.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Blocked unsafe {field_name} input by safety guardrail.",
            )


def guard_analytics_query(query: str) -> str:
    settings = get_settings()
    normalized = _normalize_text(query)

    if not settings.ENABLE_SAFETY_GUARDRAILS:
        return normalized

    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Analytics question cannot be empty")

    if len(normalized) > settings.MAX_ANALYTICS_QUERY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analytics question exceeds max length ({settings.MAX_ANALYTICS_QUERY_LENGTH})",
        )

    _block_if_suspicious(normalized, "analytics")
    return normalized


def guard_search_query(query: str) -> str:
    settings = get_settings()
    normalized = _normalize_text(query)

    if not settings.ENABLE_SAFETY_GUARDRAILS:
        return normalized

    if len(normalized) > settings.MAX_SEARCH_QUERY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Search query exceeds max length ({settings.MAX_SEARCH_QUERY_LENGTH})",
        )

    _block_if_suspicious(normalized, "search")
    return normalized
