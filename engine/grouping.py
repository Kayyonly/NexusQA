from __future__ import annotations

from collections import Counter
from typing import Any


def normalize_issue(text: str) -> str:
    t = (text or "").strip()
    low = t.lower()
    if "hydration" in low:
        return "Hydration mismatch"
    if "404" in low and "image" in low:
        return "404 image"
    if "timeout" in low:
        return "Network timeout"
    if "missing alt" in low:
        return "Missing alt"
    if "missing label" in low:
        return "Missing label"
    if "overlap" in low:
        return "Overlapping element"
    if "overflow" in low:
        return "Overflow"
    if "5" in low and "status" in low:
        return "5xx API"
    return t[:140]


def deduplicate_issues(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    merged = 0
    for item in items:
        key = f"{item.get('category')}|{item.get('normalized_issue')}|{item.get('page')}|{item.get('device', '')}"
        if key in seen:
            merged += 1
            continue
        seen.add(key)
        out.append(item)
    return out, merged


def group_issues(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter = Counter((it["category"], it["normalized_issue"], it.get("severity", "LOW")) for it in items)
    grouped = [
        {"category": c, "issue": i, "severity": s, "count": n}
        for (c, i, s), n in counter.most_common()
    ]
    return grouped
