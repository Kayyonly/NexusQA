from datetime import datetime
from pathlib import Path
from typing import Any

from utils import save_json


def build_report(pages: list[dict[str, Any]], interactions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    interactions = interactions or []
    total_console_errors = sum(len(p["console_errors"]) for p in pages)
    total_failed_requests = sum(len(p["failed_requests"]) for p in pages)
    total_broken_images = sum(len(p["broken_images"]) for p in pages)
    total_accessibility_issues = sum(len(p["accessibility_issues"]) for p in pages)
    avg_load_time_ms = round(sum(p["load_time_ms"] for p in pages) / max(len(pages), 1), 2)

    interaction_summary = {
        "pages_tested": len(interactions),
        "buttons_total": sum(i.get("buttons_total", 0) for i in interactions),
        "buttons_clicked": sum(i.get("buttons_clicked", 0) for i in interactions),
        "buttons_failed": sum(i.get("buttons_failed", 0) for i in interactions),
        "forms_tested": sum(i.get("forms_tested", 0) for i in interactions),
        "validation_issues": sum(i.get("validation_issues", 0) for i in interactions),
        "broken_forms": sum(i.get("broken_forms", 0) for i in interactions),
        "broken_links": sum(i.get("broken_links", 0) for i in interactions),
        "dead_routes": sum(i.get("dead_routes", 0) for i in interactions),
        "redirect_issues": sum(i.get("redirect_issues", 0) for i in interactions),
        "modal_issues": sum(i.get("modal_issues", 0) for i in interactions),
        "dropdown_issues": sum(i.get("dropdown_issues", 0) for i in interactions),
        "interaction_timeouts": sum(i.get("interaction_timeouts", 0) for i in interactions),
    }

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "pages_crawled": len(pages),
            "avg_load_time_ms": avg_load_time_ms,
            "total_console_errors": total_console_errors,
            "total_failed_requests": total_failed_requests,
            "total_broken_images": total_broken_images,
            "total_accessibility_issues": total_accessibility_issues,
        },
        "interaction_testing": {
            "summary": interaction_summary,
            "details": interactions,
        },
        "pages": pages,
    }


def write_reports(base_name: str, payload: dict[str, Any], ai_result: dict[str, Any]) -> tuple[str, str]:
    Path("reports").mkdir(exist_ok=True)
    json_path = f"reports/{base_name}.json"
    txt_path = f"reports/{base_name}.txt"

    payload["ai_analysis"] = ai_result
    save_json(json_path, payload)

    summary = payload["summary"]
    interaction = payload.get("interaction_testing", {}).get("summary", {})
    lines = [
        "AI WEBSITE REVIEW BOT REPORT",
        "=" * 40,
        f"Generated: {payload['generated_at']}",
        f"Pages Crawled: {summary['pages_crawled']}",
        f"Avg Load Time: {summary['avg_load_time_ms']} ms",
        f"Console Errors: {summary['total_console_errors']}",
        f"Failed Requests: {summary['total_failed_requests']}",
        f"Broken Images: {summary['total_broken_images']}",
        f"Accessibility Issues: {summary['total_accessibility_issues']}",
        "",
        "🧪 INTERACTION TESTING",
        "-" * 40,
        f"Buttons total/clicked/failed: {interaction.get('buttons_total',0)}/{interaction.get('buttons_clicked',0)}/{interaction.get('buttons_failed',0)}",
        f"Forms tested: {interaction.get('forms_tested',0)} | Validation issues: {interaction.get('validation_issues',0)} | Broken forms: {interaction.get('broken_forms',0)}",
        f"Broken links: {interaction.get('broken_links',0)} | Dead routes: {interaction.get('dead_routes',0)} | Redirect issues: {interaction.get('redirect_issues',0)}",
        f"Modal issues: {interaction.get('modal_issues',0)} | Dropdown issues: {interaction.get('dropdown_issues',0)} | Interaction timeout: {interaction.get('interaction_timeouts',0)}",
        "",
        "AI ANALYSIS",
        "-" * 40,
        f"Score: {ai_result.get('score')}",
        f"Analysis: {ai_result.get('analysis')}",
        "Recommendations:",
    ]
    for item in ai_result.get("recommendations", []):
        lines.append(f"- {item}")

    Path(txt_path).write_text("\n".join(lines), encoding="utf-8")
    return txt_path, json_path
