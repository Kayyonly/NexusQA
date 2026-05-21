from __future__ import annotations

from typing import Any


def clamp(value: int) -> int:
    return max(0, min(100, value))


def build_scores(summary: dict[str, Any], grouped_issues: list[dict[str, Any]]) -> dict[str, int]:
    perf = 100
    a11y = 100
    sec = 100
    ux = 100

    avg_load = float(summary.get("avg_load_time_ms", 0) or 0)
    failed = int(summary.get("total_failed_requests", 0) or 0)
    console_err = int(summary.get("total_console_errors", 0) or 0)

    if avg_load > 2500:
        perf -= 10
    if avg_load > 5000:
        perf -= 12
    perf -= min(failed * 2, 20)
    perf -= min(console_err, 10)

    for issue in grouped_issues:
        cat = issue.get("category", "")
        sev = issue.get("severity", "LOW")
        count = int(issue.get("count", 1))
        mul = 3 if sev == "CRITICAL" else 2 if sev == "HIGH" else 1
        penalty = min(count * mul, 12)
        if cat == "Accessibility":
            a11y -= penalty
        elif cat == "Security":
            sec -= penalty
        elif cat in {"UI/Responsive", "Frontend"}:
            ux -= penalty
        elif cat in {"Performance", "Network/API"}:
            perf -= penalty

    performance_score = clamp(perf)
    accessibility_score = clamp(a11y)
    security_score = clamp(sec)
    ux_score = clamp(ux)
    overall_score = clamp(round((performance_score + accessibility_score + security_score + ux_score) / 4))
    return {
        "performance_score": performance_score,
        "accessibility_score": accessibility_score,
        "security_score": security_score,
        "ux_score": ux_score,
        "overall_score": overall_score,
    }
