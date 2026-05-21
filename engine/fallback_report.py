from __future__ import annotations

from typing import Any


def build_local_insight(scores: dict[str, int], grouped: list[dict[str, Any]], responsive_summary: dict[str, Any]) -> str:
    perf_label = "baik" if scores["performance_score"] >= 80 else "cukup" if scores["performance_score"] >= 65 else "perlu perbaikan"
    net_issues = sum(i["count"] for i in grouped if i["category"] == "Network/API")
    resp_issues = sum(i["count"] for i in grouped if i["category"] == "UI/Responsive")
    device = responsive_summary.get("worst_device", "unknown")
    return (
        f"Website memiliki performa {perf_label}, ditemukan {net_issues} network/api issue dan "
        f"{resp_issues} responsive issue. Device paling bermasalah: {device}."
    )


def build_fallback_report(insight: str, scores: dict[str, int], grouped: list[dict[str, Any]]) -> str:
    top5 = grouped[:5]
    lines = [
        f"# 🏆 SKOR KESELURUHAN: {scores['overall_score']}/100",
        "",
        "⚠️ AI analyzer gagal. Laporan fallback lokal digunakan.",
        "",
        "## 📌 Insight Lokal",
        insight,
        "",
        "## 📊 Skor",
        f"- Performance: {scores['performance_score']}/100",
        f"- Accessibility: {scores['accessibility_score']}/100",
        f"- Security: {scores['security_score']}/100",
        f"- UX: {scores['ux_score']}/100",
        "",
        "## 🎯 Prioritas",
    ]
    for i, issue in enumerate(top5, 1):
        lines.append(f"{i}. [{issue['severity']}] {issue['category']} - {issue['issue']} (x{issue['count']})")
    lines.extend([
        "",
        "## Rekomendasi Lokal",
        "- Prioritaskan crash/auth failure/5xx API terlebih dahulu.",
        "- Perbaiki issue responsive pada viewport/device terburuk.",
        "- Optimasi asset besar dan endpoint lambat.",
        "- Tindak lanjuti potential security risk secara manual.",
    ])
    return "\n".join(lines)
