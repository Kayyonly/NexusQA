import json
import os
import time
from typing import Any

from groq import Groq


ADVANCED_ANALYSIS_PROMPT_TEMPLATE = """Kamu adalah seorang Senior QA Engineer sekaligus Senior Web Developer dengan pengalaman industri bertahun-tahun dalam:

* Website Quality Assurance
* Automation Testing
* Frontend & Backend Debugging
* Performance Optimization
* Accessibility Audit
* Security Review
* Modern Web Framework Analysis (React, Next.js, Vue, Nuxt, Laravel, Express, dll)

Tugas kamu adalah menganalisa hasil testing otomatis website secara mendalam dan membuat laporan QA profesional dengan bahasa Indonesia yang natural, halus, mudah dipahami manusia, dan tidak terdengar seperti robot.

========================================
📥 DATA HASIL TESTING
=====================

{testing_data_json}

========================================
🎯 TUJUAN ANALISA
=================

Lakukan analisa menyeluruh terhadap:

* Performa website
* Bug & error
* UI/UX
* Form validation
* Accessibility
* API/network issue
* Security issue
* Asset/media issue
* Responsiveness
* Console error
* Failed request
* Rendering/hydration issue
* SEO basic issue
* Best practice modern web

Jika ada kemungkinan false positive dari automation testing, jelaskan juga.

Jangan membuat asumsi berlebihan tanpa bukti.
Jika informasi kurang jelas, tandai sebagai:
“⚠️ Perlu validasi manual lebih lanjut.”

Gunakan gaya bahasa:

* Profesional
* Natural
* Halus
* Mudah dipahami
* Tidak terlalu kaku
* Tidak menghakimi developer
* Fokus pada solusi konstruktif

========================================
📊 FORMAT OUTPUT
================

# 🏆 SKOR KESELURUHAN: [X/100]

Berikan penilaian umum kondisi website dalam 2–4 kalimat.

Tambahkan tabel penilaian:

| Kategori        | Skor  |
| --------------- | ----- |
| Stability       | X/100 |
| Performance     | X/100 |
| Security        | X/100 |
| Accessibility   | X/100 |
| User Experience | X/100 |
| Maintainability | X/100 |

---

# ⚡ ANALISIS PERFORMA

Analisa:

* Load time
* FCP
* LCP
* Render performance
* API latency
* Asset loading
* Bottleneck utama

Berikan:

* apa yang sudah baik
* apa yang perlu optimasi
* dampaknya ke UX & SEO
* rekomendasi realistis

Jika tidak ada masalah:
✅ Tidak ada masalah performa signifikan ditemukan.

---

# 🐛 BUG & ERROR

Gunakan severity:

* CRITICAL
* HIGH
* MEDIUM
* LOW

Untuk setiap issue gunakan format:

## [SEVERITY] Nama Masalah

### Ringkasan

...

### Detail Teknis

...

### Dampak

...

### Kemungkinan Penyebab

...

### Cara Fix / Rekomendasi

...

### Prioritas

...

Jika tidak ada bug:
✅ Tidak ada bug/error signifikan ditemukan.

---

# 📋 UI & FORM

Evaluasi:

* form
* validation
* responsive
* layout
* usability
* mobile issue
* overflow
* hydration mismatch
* layout shift

Jika tidak ada masalah:
✅ Tidak ada masalah UI/form signifikan ditemukan.

---

# ♿ AKSESIBILITAS

Evaluasi:

* alt text
* semantic HTML
* heading structure
* keyboard navigation
* ARIA
* screen reader compatibility

Kelompokkan berdasarkan severity.

---

# 🖼️ GAMBAR & MEDIA

Evaluasi:

* broken image
* missing alt
* ukuran gambar
* lazy loading
* modern image format

---

# 🔐 ANALISIS SECURITY DASAR

Cek indikasi:

* exposed secret
* insecure header
* auth issue
* XSS indication
* CSRF indication
* dependency issue

Jangan membuat klaim berlebihan tanpa bukti.

---

# 🧠 ANALISA FRONTEND

Analisa:

* React/Next.js hydration
* rendering issue
* component issue
* Tailwind/CSS issue
* state issue
* responsive issue

---

# ⚙️ ANALISA BACKEND/API

Analisa:

* failed request
* slow API
* abnormal status code
* validation issue
* timeout

---

# 🎯 5 PRIORITAS UTAMA

Urutkan 5 masalah paling penting berdasarkan dampak bisnis dan user experience.

---

# 📌 KESIMPULAN AKHIR

Berikan kesimpulan profesional layaknya laporan QA perusahaan software.

Jelaskan:

* tingkat kesiapan website
* risiko utama
* area yang paling perlu improvement
* apakah website layak production

---"""


def _score(avg_load_time: float, errors: int, a11y: int) -> int:
    score = 100
    if avg_load_time > 3000:
        score -= 15
    if avg_load_time > 5000:
        score -= 15
    score -= min(errors * 3, 30)
    score -= min(a11y * 2, 25)
    return max(score, 0)


class AIAnalyzer:
    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def _build_prompt(self, data: dict[str, Any]) -> str:
        formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
        return ADVANCED_ANALYSIS_PROMPT_TEMPLATE.format(testing_data_json=formatted_json)

    def _fallback_markdown(self, report_payload: dict[str, Any], score: int) -> str:
        summary = report_payload["summary"]
        return (
            f"# 🏆 SKOR KESELURUHAN: [{score}/100]\n\n"
            "⚠️ Perlu validasi manual lebih lanjut. (AI tidak tersedia, fallback lokal aktif)\n\n"
            "# ⚡ ANALISIS PERFORMA\n"
            f"- Rata-rata load time: {summary['avg_load_time_ms']} ms.\n"
            "- Potensi bottleneck: asset besar, request lambat, atau render blocking.\n\n"
            "# 🐛 BUG & ERROR\n"
            f"- Console errors: {summary['total_console_errors']}.\n"
            f"- Failed requests: {summary['total_failed_requests']}.\n\n"
            "# ♿ AKSESIBILITAS\n"
            f"- Total isu aksesibilitas dasar: {summary['total_accessibility_issues']}.\n\n"
            "# 🎯 5 PRIORITAS UTAMA\n"
            "1. Perbaiki failed request dan error console yang memblokir fitur utama.\n"
            "2. Optimasi resource statis (gambar, CSS, JS) serta aktifkan caching.\n"
            "3. Perbaiki aksesibilitas penting: alt text, label form, struktur heading.\n"
            "4. Validasi form input di frontend + backend untuk menurunkan error submission.\n"
            "5. Lakukan audit manual keamanan dasar (header security, auth flow, input sanitization).\n\n"
            "# 📌 KESIMPULAN AKHIR\n"
            "Website dapat diaudit otomatis dengan baik, namun masih memerlukan perbaikan prioritas sebelum dinilai siap production penuh."
        )

    def _request_with_retry(self, client: Groq, prompt: str, retries: int = 2) -> str:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Anda adalah QA engineer senior yang memberikan laporan profesional berbasis bukti."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=1800,
                )
                return (response.choices[0].message.content or "").strip()
            except Exception as exc:
                last_error = exc
                if attempt == retries:
                    break
                time.sleep(1.0)
        raise RuntimeError(f"Groq request failed after retry: {last_error}")

    def analyze(self, report_payload: dict[str, Any]) -> dict[str, Any]:
        perf = report_payload["summary"]["avg_load_time_ms"]
        err = report_payload["summary"]["total_console_errors"] + report_payload["summary"]["total_failed_requests"]
        a11y = report_payload["summary"]["total_accessibility_issues"]
        local_score = _score(perf, err, a11y)

        if not self.api_key:
            fallback = self._fallback_markdown(report_payload, local_score)
            return {
                "score": local_score,
                "analysis": "GROQ_API_KEY tidak tersedia. Menggunakan analisis lokal berbasis rule.",
                "recommendations": [
                    "Perbaiki console error dan failed request terlebih dahulu.",
                    "Optimalkan asset statis (gambar, CSS, JS).",
                    "Tambahkan label/alt text untuk aksesibilitas.",
                ],
                "markdown_report": fallback,
            }

        client = Groq(api_key=self.api_key)
        prompt = self._build_prompt(report_payload)

        try:
            raw = self._request_with_retry(client, prompt, retries=2)
            markdown_report = raw if raw else self._fallback_markdown(report_payload, local_score)
            return {
                "score": local_score,
                "analysis": "Analisis Groq berhasil dibuat.",
                "recommendations": [],
                "markdown_report": markdown_report,
            }
        except Exception as exc:
            fallback = self._fallback_markdown(report_payload, local_score)
            return {
                "score": local_score,
                "analysis": f"Groq gagal dipanggil, fallback lokal aktif: {exc}",
                "recommendations": ["Cek GROQ_API_KEY, model, dan koneksi jaringan."],
                "markdown_report": fallback,
            }
