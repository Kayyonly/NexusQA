import json
from checker import CheckResult

# ── Provider yang tersedia ────────────────────────────────────────────────────
PROVIDERS = {
    "claude": "Anthropic Claude  (claude-sonnet-4-20250514)",
    "openai": "OpenAI GPT        (gpt-4o)",
    "gemini": "Google Gemini     (gemini-1.5-flash)",
    "groq":   "Groq              (llama-3.3-70b-versatile) — Gratis!",
}


def build_prompt(result: CheckResult) -> str:
    """Buat prompt analisis dari hasil checker (dipakai semua provider)."""
    broken_images = [i for i in result.images if not i.get("is_loaded")]
    external_links = [l for l in result.links if l.get("is_external")]

    data = {
        "url": result.url,
        "judul": result.page_title,
        "meta_description": result.meta_description or "(tidak ada)",
        "performa": {
            "load_time_ms": result.load_time,
            "dom_content_loaded_ms": result.dom_ready,
            "first_contentful_paint_ms": result.fcp,
            "ukuran_transfer_kb": result.resource_sizes.get("transfer_size_kb", 0),
            "total_resource_kb": result.resource_sizes.get("total_resource_kb", 0),
            "jumlah_resource": result.resource_sizes.get("resource_count", 0),
        },
        "errors": {
            "console_errors": result.console_errors[:8],
            "console_warnings": result.console_warnings[:5],
            "network_errors": result.network_errors[:8],
            "http_errors": result.failed_responses[:8],
        },
        "forms": {
            "jumlah": len(result.forms),
            "detail": [
                {
                    "method": f.get("method"),
                    "jumlah_input": f.get("input_count"),
                    "ada_submit": f.get("has_submit"),
                    "inputs": f.get("inputs", [])[:4],
                }
                for f in result.forms
            ],
        },
        "links": {
            "total": len(result.links),
            "internal": len(result.links) - len(external_links),
            "eksternal": len(external_links),
        },
        "gambar": {
            "total": len(result.images),
            "rusak": len(broken_images),
            "tanpa_alt": len([i for i in result.images if not i.get("has_alt")]),
            "detail_rusak": [{"src": i["src"][:80]} for i in broken_images[:5]],
        },
        "aksesibilitas": result.accessibility_issues[:15],
    }

    return f"""Kamu adalah seorang Senior QA Engineer sekaligus Senior Web Developer dengan pengalaman industri bertahun-tahun dalam:
- Website Quality Assurance
- Automation Testing
- Frontend & Backend Debugging
- Performance Optimization
- Accessibility Audit
- Security Review
- Modern Web Framework Analysis (React, Next.js, Vue, Nuxt, Laravel, Express, dll)

Tugas kamu adalah menganalisa hasil testing otomatis website secara mendalam dan membuat laporan QA profesional dengan bahasa Indonesia yang natural, halus, mudah dipahami manusia, dan tidak terdengar seperti robot.

========================================
📥 DATA HASIL TESTING
========================================

{json.dumps(data, indent=2, ensure_ascii=False)}

========================================
🎯 TUJUAN ANALISA
========================================

Lakukan analisa menyeluruh terhadap:
- Performa website
- Bug & error
- UI/UX
- Form validation
- Accessibility
- API/network issue
- Security issue
- Asset/media issue
- Responsiveness
- Console error
- Failed request
- Rendering/hydration issue
- SEO basic issue
- Best practice modern web

Jika ada kemungkinan false positive dari automation testing, jelaskan juga.

Jangan membuat asumsi berlebihan tanpa bukti.
Jika informasi kurang jelas, tandai sebagai:
“⚠️ Perlu validasi manual lebih lanjut.”

Gunakan gaya bahasa:
- Profesional
- Natural
- Halus
- Mudah dipahami
- Tidak terlalu kaku
- Tidak menghakimi developer
- Fokus pada solusi konstruktif

========================================
📊 FORMAT OUTPUT
========================================

# 🏆 SKOR KESELURUHAN: [X/100]

Berikan penilaian umum kondisi website dalam 2–4 kalimat.
Jelaskan apakah website sudah cukup stabil atau masih memiliki banyak masalah penting.

Tambahkan penilaian:
| Kategori | Skor |
|---|---|
| Stability | X/100 |
| Performance | X/100 |
| Security | X/100 |
| Accessibility | X/100 |
| User Experience | X/100 |
| Maintainability | X/100 |

---

# ⚡ ANALISIS PERFORMA

Evaluasi:
- Load time
- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP)
- Time To Interactive (TTI)
- Total Blocking Time
- Ukuran halaman
- Asset loading
- API response
- Caching
- Render performance

Gunakan standar:
- Load < 3s = bagus
- FCP < 1.8s = bagus
- LCP < 2.5s = bagus

Jelaskan:
- Apa yang sudah baik
- Apa bottleneck utama
- Dampaknya ke UX & SEO
- Rekomendasi optimasi

Jika tidak ada masalah:
✅ Tidak ada masalah performa signifikan ditemukan.

---

# 🐛 BUG & ERROR

Untuk setiap issue gunakan format:

## [CRITICAL/HIGH/MEDIUM/LOW] Nama Masalah

### Ringkasan
Penjelasan singkat dan mudah dipahami.

### Detail Teknis
Jelaskan indikasi teknis atau penyebab kemungkinan.

### Dampak
Jelaskan dampaknya terhadap:
- User Experience
- Functionality
- Security
- Performance
- SEO
- Accessibility
(jika relevan)

### Kemungkinan Penyebab
Analisa akar masalah.

### Cara Fix / Rekomendasi
Berikan solusi realistis dan best practice.

### Prioritas
- Segera diperbaiki
- Bisa dijadwalkan
- Opsional

Jika tidak ada bug:
✅ Tidak ada bug/error signifikan ditemukan.

---

# 📋 UI & FORM

Evaluasi:
- Input field
- Validation
- Required field
- Error message
- Label form
- Placeholder
- Tombol submit
- Navigasi link
- Responsive layout
- Mobile usability
- Layout consistency

Jika ada screenshot:
- Analisa detail visual
- Kemungkinan penyebab CSS/JS/layout issue
- Indikasi hydration mismatch React/Next.js
- Layout shift
- Overflow
- Z-index issue

Jika tidak ada masalah:
✅ Tidak ada masalah UI/form signifikan ditemukan.

---

# ♿ AKSESIBILITAS

Evaluasi:
- Alt text
- Contrast
- ARIA label
- Semantic HTML
- Keyboard navigation
- Screen reader compatibility
- Heading structure

Kelompokkan berdasarkan prioritas:
- Critical
- High
- Medium
- Low

Jika tidak ada masalah:
✅ Tidak ada masalah aksesibilitas signifikan ditemukan.

---

# 🖼️ GAMBAR & MEDIA

Evaluasi:
- Broken image
- Missing alt text
- Lazy loading
- Ukuran gambar
- Format modern (WebP/AVIF)
- Video/media optimization

Jika tidak ada masalah:
✅ Tidak ada masalah gambar/media ditemukan.

---

# 🔐 ANALISIS SECURITY DASAR

Cek indikasi:
- Exposed secret
- Insecure header
- Open endpoint
- Auth issue
- XSS indication
- CSRF issue
- Dependency risk
- Sensitive data exposure

Jika tidak ada indikasi:
✅ Tidak ada indikasi masalah security kritis ditemukan.

---

# 🧠 ANALISA FRONTEND

Analisa:
- React/Next.js hydration
- Rendering issue
- State management issue
- Tailwind/CSS issue
- Component re-render
- Responsive issue
- Asset bundling
- Client-side error

Jika tidak ada masalah:
✅ Tidak ada masalah frontend signifikan ditemukan.

---

# ⚙️ ANALISA BACKEND/API

Analisa:
- Failed request
- Status code abnormal
- Slow API
- Validation issue
- Timeout
- Database indication
- API consistency

Jika tidak ada masalah:
✅ Tidak ada masalah backend/API signifikan ditemukan.

---

# 🎯 5 PRIORITAS UTAMA

Urutkan 5 hal PALING penting yang harus segera diperbaiki berdasarkan dampak bisnis dan user experience.

Gunakan format:
1. [Masalah] → alasan prioritas
2. ...
3. ...
4. ...
5. ...

---

# 📌 KESIMPULAN AKHIR

Berikan kesimpulan profesional layaknya laporan QA perusahaan software.

Jelaskan:
- Tingkat kesiapan website
- Risiko utama
- Area yang paling perlu improvement
- Apakah website layak production atau masih perlu banyak perbaikan

Gunakan bahasa natural dan profesional.
"""


class AIAnalyzer:
    """
    Multi-provider AI analyzer.

    Parameters
    ----------
    provider : str
        Pilih: 'claude', 'openai', 'gemini', 'groq'
    api_key : str
        API key untuk provider yang dipilih
    """

    def __init__(self, provider: str = "claude", api_key: str = ""):
        provider = provider.lower().strip()
        if provider not in PROVIDERS:
            raise ValueError(
                f"Provider '{provider}' tidak dikenal.\n"
                f"Pilihan tersedia: {', '.join(PROVIDERS.keys())}"
            )
        if not api_key:
            raise ValueError(
                f"API key kosong untuk provider '{provider}'.\n"
                "Gunakan --api-key saat menjalankan script."
            )
        self.provider = provider
        self.api_key = api_key

    def analyze(self, result: CheckResult) -> str:
        prompt = build_prompt(result)
        dispatch = {
            "claude": self._analyze_claude,
            "openai": self._analyze_openai,
            "gemini": self._analyze_gemini,
            "groq":   self._analyze_groq,
        }
        return dispatch[self.provider](prompt)

    # ── Claude (Anthropic) ────────────────────────────────────────────────────
    def _analyze_claude(self, prompt: str) -> str:
        try:
            import anthropic
        except ImportError:
            raise ImportError("Install dulu: pip install anthropic")

        client = anthropic.Anthropic(api_key=self.api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    # ── OpenAI (GPT-4o) ───────────────────────────────────────────────────────
    def _analyze_openai(self, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Install dulu: pip install openai")

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    # ── Google Gemini ─────────────────────────────────────────────────────────
    def _analyze_gemini(self, prompt: str) -> str:
        # Coba pakai package baru dulu, fallback ke package lama
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            return response.text
        except ImportError:
            pass  # Package baru tidak ada, coba yang lama

        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "Install dulu salah satu:\n"
                "  pip install google-genai          (package baru)\n"
                "  pip install google-generativeai   (package lama)"
            )

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Sembunyikan FutureWarning
            genai.configure(api_key=self.api_key)
            # Coba model terbaru yang tersedia
            for model_name in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    return response.text
                except Exception:
                    continue
            raise RuntimeError("Tidak ada model Gemini yang tersedia. Cek API key kamu.")

    # ── Groq (Llama 3.3 — Gratis!) ───────────────────────────────────────────
    def _analyze_groq(self, prompt: str) -> str:
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Install dulu: pip install groq")

        client = Groq(api_key=self.api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content