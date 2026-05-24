<div align="center">

# NexusQA

**AI-Powered Website Review & QA Automation Tool**

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-Automation-green?style=flat-square&logo=playwright)](https://playwright.dev)
[![Groq](https://img.shields.io/badge/AI-Groq%20Llama%203.3-orange?style=flat-square)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-Kayyonly%2FNexusQA-black?style=flat-square&logo=github)](https://github.com/Kayyonly/NexusQA)

Automated website testing powered by Playwright + Groq AI — crawling, performance, accessibility, responsive, interaction, auth testing, dan AI analysis dalam satu tools.

</div>

---

## Features

| Feature | Description |
|---------|-------------|
| Smart Crawler | Crawl otomatis hingga 50 halaman dengan route detection |
| Performance Test | Load time, FCP, DOM ready, transfer size |
| Bug & Error Detection | Console errors, network failures, HTTP 4xx/5xx |
| Responsive Testing | Desktop, tablet, mobile dengan screenshot per device |
| Accessibility Audit | Alt text, label, heading structure, ARIA |
| Interaction Testing | Form, button, modal, dropdown testing otomatis |
| Auth Testing | Login flow, session, protected route testing |
| Video Recording | Record sesi testing per halaman |
| AI Analysis | Laporan profesional oleh Groq Llama 3.3 70B |
| GUI Desktop | Tampilan modern dengan CustomTkinter, auto dark/light mode |

---

## Testing Modes

### Quick (~10-30 seconds)
- Homepage only
- Basic performance & error check
- Screenshot homepage
- Desktop only, 1-3 pages

### Standard (~30-90 seconds)
- Limited crawling
- Responsive + mobile test
- Accessibility & form testing
- AI analysis active
- Desktop + Mobile, 5-15 pages

### Deep (~2-10 minutes)
- Smart crawler + AI agent
- Auth testing & session management
- Visual & security testing
- Video recording + replay
- Deep AI analysis
- Desktop + Tablet + Mobile, 20-50 pages

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| GUI | CustomTkinter |
| Browser Automation | Playwright |
| AI Analysis | Groq (Llama 3.3 70B) |
| Crawling | Smart Crawler (custom) |
| Terminal Output | Rich |
| Config | python-dotenv |

---

## Installation

### 1. Clone repository

```bash
git clone https://github.com/Kayyonly/NexusQA.git
cd NexusQA
```

### 2. Install dependencies

```bash
pip install -r Requirements.txt
playwright install chromium
```

### 3. Setup API Key

Buat file `.env` di root folder:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
```

Dapatkan API key gratis di [console.groq.com](https://console.groq.com)

---

## Usage

### GUI (Recommended)

```bash
python gui.py
```

1. Masukkan URL website
2. Pilih mode (Quick / Standard / Deep)
3. Klik Run Analysis
4. Lihat hasil di tab Live Log dan AI Report

### CLI

```bash
# Mode interaktif
python main.py

# Langsung dengan argumen
python main.py --url https://example.com --mode standard
python main.py --url https://example.com --mode deep --max-pages 20

# Dengan auth testing
python main.py --url https://example.com --mode deep \
  --auth-enabled \
  --login-url https://example.com/login \
  --auth-username admin@example.com \
  --auth-password password123
```

---

## Project Structure

```
NexusQA/
├── gui.py                  # Desktop GUI (CustomTkinter)
├── main.py                 # CLI entry point
├── analyzer.py             # AI analysis (Groq)
├── checker.py              # Page checker (Playwright)
├── crawler.py              # Basic crawler
├── report.py               # Report generator
├── utils.py                # Helper functions
│
├── ai/                     # AI summary builder
├── ai_agent/               # Autonomous testing agent
├── auth/                   # Auth testing modules
├── config/                 # Mode configurations
├── interaction/            # Form & interaction testing
├── recording/              # Video recording & replay
├── responsive/             # Responsive testing
├── smart_crawler/          # Smart crawling engine
├── visual_testing/         # Visual regression testing
│
├── .env                    # API keys (tidak di-commit)
├── .gitignore
└── Requirements.txt
```

---

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | API key Groq (required) | - |
| `GROQ_MODEL` | Groq model yang digunakan | `llama-3.3-70b-versatile` |

---

## Contributing

Pull request dan issue sangat welcome.

1. Fork repository ini
2. Buat branch baru: `git checkout -b feature/nama-fitur`
3. Commit perubahan: `git commit -m "Add fitur baru"`
4. Push: `git push origin feature/nama-fitur`
5. Buat Pull Request

---

## License

MIT License - bebas digunakan dan dimodifikasi.

---

<div align="center">

Made with love by **Kayy**

[![GitHub](https://img.shields.io/badge/GitHub-Kayyonly-black?style=flat-square&logo=github)](https://github.com/Kayyonly)

</div>
