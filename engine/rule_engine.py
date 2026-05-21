from __future__ import annotations

from typing import Any

from engine.fallback_report import build_local_insight
from engine.grouping import deduplicate_issues, group_issues, normalize_issue
from engine.scoring import build_scores
from engine.severity import classify_severity


class LocalRuleEngine:
    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw = self._collect_raw_issues(payload)
        deduped, merged = deduplicate_issues(raw)
        grouped = group_issues(deduped)
        scores = build_scores(payload.get("summary", {}), grouped)
        responsive_summary = self._responsive_summary(payload)
        insight = build_local_insight(scores, grouped, responsive_summary)
        critical_count = sum(1 for i in deduped if i.get("severity") == "CRITICAL")
        high_priority = self._priority_issues(grouped)

        return {
            "issues_classified": deduped,
            "issues_grouped": grouped,
            "duplicates_merged": merged,
            "critical_issues": critical_count,
            "scores": scores,
            "responsive_summary": responsive_summary,
            "local_insight": insight,
            "priorities": high_priority,
            "terminal_summary": {
                "classified": len(deduped),
                "merged": merged,
                "critical": critical_count,
            },
        }

    def _collect_raw_issues(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for page in payload.get("pages", []):
            url = page.get("url", "")
            for e in page.get("console_errors", []):
                msg = str(e.get("text", ""))
                cat = "Frontend" if any(k in msg.lower() for k in ["react", "hydration", "render", "state"]) else "Performance"
                issues.append(self._item(cat, msg, url))
            for req in page.get("failed_requests", []):
                status = str(req.get("status", ""))
                url_req = req.get("url", "")
                text = f"failed request status {status} {url_req}"
                issues.append(self._item("Network/API", text, url))
            for a in page.get("accessibility_issues", []):
                text = str(a.get("type") or a.get("message") or "Accessibility issue")
                issues.append(self._item("Accessibility", text, url))

        responsive = payload.get("responsive_testing", {}).get("devices", {})
        for group in ["desktop", "tablet", "mobile"]:
            for item in responsive.get(group, []):
                issue_map = item.get("issue_map", {})
                for issue_name, val in issue_map.items():
                    if val:
                        issues.append(self._item("UI/Responsive", issue_name, item.get("url", ""), device=group))

        return issues

    def _item(self, category: str, text: str, page: str, device: str | None = None) -> dict[str, Any]:
        normalized = normalize_issue(text)
        severity = classify_severity(category, normalized, {"device": device})
        return {
            "category": category,
            "issue": text,
            "normalized_issue": normalized,
            "page": page,
            "device": device,
            "severity": severity,
        }

    def _responsive_summary(self, payload: dict[str, Any]) -> dict[str, Any]:
        devices = payload.get("responsive_testing", {}).get("devices", {})
        counts = {k: 0 for k in ["desktop", "tablet", "mobile"]}
        for k in counts:
            for item in devices.get(k, []):
                if any(item.get("issue_map", {}).values()):
                    counts[k] += 1
        worst_device = max(counts, key=counts.get) if counts else "unknown"
        return {"issues_per_device": counts, "worst_device": worst_device}

    def _priority_issues(self, grouped: list[dict[str, Any]]) -> list[dict[str, Any]]:
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        return sorted(grouped, key=lambda x: (order.get(x["severity"], 9), -x["count"]))[:5]
