from __future__ import annotations

import json
from collections import Counter
from typing import Any


class SummaryBuilder:
    def __init__(self, max_payload_chars: int = 6000) -> None:
        self.max_payload_chars = max_payload_chars

    def build_summary(self, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        pages = payload.get("pages", [])[:20]
        summary = payload.get("summary", {})
        responsive = payload.get("responsive_testing", {}).get("devices", {})
        interactions = payload.get("interaction_testing", {}).get("details", [])[:20]

        console_errors = [e.get("text", "") for p in pages for e in p.get("console_errors", [])]
        failed_requests = [f.get("url", "") for p in pages for f in p.get("failed_requests", [])]
        a11y = [i.get("type", "unknown") for p in pages for i in p.get("accessibility_issues", [])]

        grouped_console = self._group_issues(console_errors)[:5]
        grouped_failed = self._group_issues(failed_requests)[:5]
        grouped_a11y = self._group_issues(a11y)[:10]
        responsive_issues = self._summarize_responsive(responsive)[:10]

        avg_fcp = round(sum((p.get("fcp_ms") or 0) for p in pages) / max(len(pages), 1), 2)
        slow_api = grouped_failed[0]["issue"] if grouped_failed else "none"
        top_perf_issue = "slow_loading" if summary.get("avg_load_time_ms", 0) > 3000 else "stable"

        compact = {
            "url": pages[0].get("url", "") if pages else "",
            "title": "AI Website Review Summary",
            "performance": {
                "load_time": summary.get("avg_load_time_ms", 0),
                "fcp": avg_fcp,
                "lcp": 0,
                "tti": 0,
                "bottleneck_summary": f"Top issue: {top_perf_issue}",
                "top_performance_issue": top_perf_issue,
                "api_latency_summary": slow_api,
                "render_issue_summary": grouped_console[0]["issue"] if grouped_console else "none",
            },
            "error_summary": {
                "console_errors": len(console_errors),
                "network_errors": summary.get("total_failed_requests", 0),
                "failed_requests": len(failed_requests),
            },
            "top_console_errors": grouped_console,
            "top_failed_requests": grouped_failed,
            "responsive_issues": responsive_issues,
            "accessibility_issues": grouped_a11y,
            "security_findings": [],
            "important_pages": self._important_pages(payload),
            "interaction_logs": interactions,
            "screenshots": self._collect_screenshots(payload),
        }

        trimmed, trim_info = self._enforce_payload_limit(compact)
        debug = {
            "payload_size": len(json.dumps(trimmed, ensure_ascii=False)),
            "console_errors_summarized": f"{len(trimmed.get('top_console_errors', []))}/{len(console_errors)}",
            "failed_requests_summarized": f"{len(trimmed.get('top_failed_requests', []))}/{len(failed_requests)}",
            **trim_info,
        }
        return trimmed, debug

    def _group_issues(self, values: list[str]) -> list[dict[str, Any]]:
        cleaned = [self._normalize(v) for v in values if self._is_relevant(v)]
        counts = Counter(cleaned)
        return [{"issue": key, "count": count} for key, count in counts.most_common()]

    def _is_relevant(self, text: str) -> bool:
        t = (text or "").lower()
        if not t.strip():
            return False
        noise_patterns = ["extension://", "favicon", "google-analytics", "gtm.js", "chrome-extension", "tracking"]
        return not any(p in t for p in noise_patterns)

    def _normalize(self, text: str) -> str:
        t = (text or "").strip()
        if "hydration" in t.lower():
            return "Hydration mismatch"
        return t[:140]

    def _summarize_responsive(self, devices: dict[str, Any]) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for group in ["desktop", "tablet", "mobile"]:
            for item in devices.get(group, []):
                issue_map = item.get("issue_map", {})
                first_issue = next((k for k, v in issue_map.items() if v), "")
                if first_issue:
                    issues.append({"device": item.get("device"), "issue": first_issue})
        unique = []
        seen = set()
        for i in issues:
            key = (i.get("device"), i.get("issue"))
            if key not in seen:
                seen.add(key)
                unique.append(i)
        return unique

    def _important_pages(self, payload: dict[str, Any]) -> list[str]:
        pages = payload.get("smart_crawler", {}).get("important_pages", {})
        if isinstance(pages, dict):
            return list(pages.keys())[:20]
        if isinstance(pages, list):
            return pages[:20]
        return []

    def _collect_screenshots(self, payload: dict[str, Any]) -> list[str]:
        shots = [p.get("screenshot_path", "") for p in payload.get("pages", []) if p.get("screenshot_path")]
        auth = payload.get("authenticated_testing", {})
        shots.extend(auth.get("screenshots", []))
        for extra in [auth.get("dashboard_screenshot"), auth.get("protected_route_screenshot")]:
            if extra:
                shots.append(extra)
        cleaned = [s for s in dict.fromkeys(shots) if s][:20]
        return cleaned

    def _enforce_payload_limit(self, summary: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        trimmed = dict(summary)
        dropped: list[str] = []
        while len(json.dumps(trimmed, ensure_ascii=False)) > self.max_payload_chars:
            if len(trimmed.get("interaction_logs", [])) > 5:
                trimmed["interaction_logs"] = trimmed["interaction_logs"][:-2]
                dropped.append("interaction_logs")
                continue
            if len(trimmed.get("responsive_issues", [])) > 3:
                trimmed["responsive_issues"] = trimmed["responsive_issues"][:-1]
                dropped.append("responsive_issues")
                continue
            if len(trimmed.get("screenshots", [])) > 5:
                trimmed["screenshots"] = trimmed["screenshots"][:-1]
                dropped.append("screenshots")
                continue
            break
        return trimmed, {"trimmed": bool(dropped), "trimmed_fields": list(dict.fromkeys(dropped))}
