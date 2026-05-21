from __future__ import annotations

from typing import Any

SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"


def classify_severity(category: str, issue: str, context: dict[str, Any] | None = None) -> str:
    text = f"{category} {issue}".lower()
    ctx = context or {}

    if any(k in text for k in ["crash", "fatal", "auth failure", "broken layout severe"]):
        return SEVERITY_CRITICAL

    if "5xx" in text or "status 5" in text or "internal server error" in text:
        return SEVERITY_HIGH
    if "timeout" in text and ctx.get("count", 0) >= 3:
        return SEVERITY_HIGH
    if "hydration" in text:
        return SEVERITY_MEDIUM
    if "overlap" in text or "overflow" in text or "hidden button" in text:
        return SEVERITY_HIGH if ctx.get("device") == "mobile" else SEVERITY_MEDIUM
    if "missing alt" in text or "missing label" in text:
        return SEVERITY_LOW
    if "aria" in text or "heading" in text:
        return SEVERITY_LOW
    if "4xx" in text or "failed request" in text:
        return SEVERITY_MEDIUM
    if "insecure header" in text or "exposed token" in text or "suspicious endpoint" in text:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW
