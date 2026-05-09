"""
checker.py — Browser automation dengan Playwright
Memeriksa: performa, errors, forms, links, gambar, aksesibilitas
"""

import asyncio
import time
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from playwright.async_api import async_playwright, Page, BrowserContext


@dataclass
class CheckResult:
    url: str
    page_title: str = ""
    meta_description: str = ""
    load_time: float = 0.0          # ms, total waktu hingga networkidle
    dom_ready: float = 0.0          # ms, domContentLoaded
    fcp: Optional[float] = None     # ms, First Contentful Paint
    resource_sizes: Dict = field(default_factory=dict)
    console_errors: List[Dict] = field(default_factory=list)
    console_warnings: List[Dict] = field(default_factory=list)
    network_errors: List[Dict] = field(default_factory=list)
    failed_responses: List[Dict] = field(default_factory=list)
    all_responses: List[Dict] = field(default_factory=list)
    forms: List[Dict] = field(default_factory=list)
    links: List[Dict] = field(default_factory=list)
    images: List[Dict] = field(default_factory=list)
    accessibility_issues: List[Dict] = field(default_factory=list)
    screenshot_path: str = ""
    html_snippet: str = ""           # Potongan HTML untuk AI


class WebsiteChecker:
    def __init__(self, headless: bool = True, take_screenshot: bool = True):
        self.headless = headless
        self.take_screenshot = take_screenshot

    async def check(self, target: str, is_file: bool = False) -> CheckResult:
        # Normalisasi URL
        if is_file:
            abs_path = os.path.abspath(target)
            url = f"file://{abs_path}"
        else:
            if not target.startswith(("http://", "https://")):
                target = "https://" + target
            url = target

        result = CheckResult(url=url)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                ignore_https_errors=True,
            )
            page = await context.new_page()

            # ── Event Listeners ──────────────────────────────────────────────
            page.on("console", lambda msg: self._handle_console(msg, result))
            page.on(
                "requestfailed",
                lambda req: result.network_errors.append({
                    "url": req.url,
                    "method": req.method,
                    "error": req.failure or "Unknown error",
                    "resource_type": req.resource_type,
                }),
            )
            page.on("response", lambda res: self._handle_response(res, result))

            # ── Navigate ─────────────────────────────────────────────────────
            try:
                start = time.time()
                await page.goto(url, wait_until="networkidle", timeout=30_000)
                result.load_time = round((time.time() - start) * 1000, 2)

                # ── Performance Metrics ──────────────────────────────────────
                perf = await page.evaluate("""() => {
                    const nav = performance.getEntriesByType('navigation')[0];
                    const fcp = performance.getEntriesByName('first-contentful-paint')[0];
                    const resources = performance.getEntriesByType('resource');
                    const totalTransfer = resources.reduce((s, r) => s + (r.transferSize || 0), 0);
                    return {
                        domContentLoaded: nav
                            ? Math.round(nav.domContentLoadedEventEnd - nav.startTime)
                            : null,
                        loadComplete: nav
                            ? Math.round(nav.loadEventEnd - nav.startTime)
                            : null,
                        fcp: fcp ? Math.round(fcp.startTime) : null,
                        transferSize: nav ? nav.transferSize : null,
                        totalResourceTransfer: Math.round(totalTransfer),
                        resourceCount: resources.length
                    };
                }""")

                result.dom_ready = perf.get("domContentLoaded") or 0
                result.fcp = perf.get("fcp")
                result.resource_sizes = {
                    "transfer_size_kb": round((perf.get("transferSize") or 0) / 1024, 1),
                    "total_resource_kb": round((perf.get("totalResourceTransfer") or 0) / 1024, 1),
                    "resource_count": perf.get("resourceCount", 0),
                }

                # ── Page Info ────────────────────────────────────────────────
                result.page_title = await page.title()
                result.meta_description = await page.evaluate("""() => {
                    const m = document.querySelector('meta[name="description"]');
                    return m ? m.getAttribute('content') : '';
                }""")

                # HTML snippet (untuk konteks AI, tidak terlalu besar)
                html = await page.content()
                result.html_snippet = html[:8000]

                # ── Checks ───────────────────────────────────────────────────
                result.forms = await self._check_forms(page)
                result.links = await self._check_links(page, url)
                result.images = await self._check_images(page)
                result.accessibility_issues = await self._check_accessibility(page)

                # ── Screenshot ───────────────────────────────────────────────
                if self.take_screenshot:
                    ss_path = "screenshot.png"
                    await page.screenshot(path=ss_path, full_page=False)
                    result.screenshot_path = ss_path

            except Exception as e:
                result.network_errors.append({
                    "url": url,
                    "method": "GET",
                    "error": str(e),
                    "resource_type": "document",
                })

            await browser.close()

        return result

    # ── Event Handlers ───────────────────────────────────────────────────────

    def _handle_console(self, msg, result: CheckResult):
        entry = {"text": msg.text, "type": msg.type}
        if msg.type == "error":
            result.console_errors.append(entry)
        elif msg.type == "warning":
            result.console_warnings.append(entry)

    def _handle_response(self, response, result: CheckResult):
        entry = {"url": response.url, "status": response.status}
        result.all_responses.append(entry)
        if response.status >= 400:
            result.failed_responses.append({
                "url": response.url,
                "status": response.status,
                "status_text": response.status_text,
            })

    # ── Checkers ─────────────────────────────────────────────────────────────

    async def _check_forms(self, page: Page) -> List[Dict]:
        """Temukan dan analisis semua form di halaman."""
        try:
            forms_data = await page.evaluate("""() => {
                return Array.from(document.forms).map((form, i) => {
                    const inputs = Array.from(
                        form.querySelectorAll('input, textarea, select')
                    ).map(inp => ({
                        type: inp.type || inp.tagName.toLowerCase(),
                        name: inp.name || inp.id || '',
                        required: inp.required,
                        placeholder: inp.placeholder || '',
                        has_label: !!document.querySelector(`label[for="${inp.id}"]`) ||
                                   !!inp.closest('label')
                    }));
                    return {
                        index: i,
                        id: form.id || '',
                        class_name: form.className.slice(0, 50) || '',
                        action: form.action || '',
                        method: (form.method || 'get').toUpperCase(),
                        input_count: inputs.length,
                        inputs: inputs,
                        has_submit: !!form.querySelector('[type="submit"], button[type="submit"], button:not([type])'),
                        is_visible: form.offsetParent !== null
                    };
                });
            }""")
            return forms_data
        except Exception:
            return []

    async def _check_links(self, page: Page, base_url: str) -> List[Dict]:
        """Ambil semua link dan kategorikan."""
        try:
            from urllib.parse import urlparse
            base_domain = urlparse(base_url).netloc

            links_data = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href]'))
                    .slice(0, 100)
                    .map(a => ({
                        href: a.href,
                        text: a.textContent.trim().slice(0, 80),
                        target: a.target || '',
                        rel: a.rel || '',
                        is_visible: a.offsetParent !== null
                    }));
            }""")

            for link in links_data:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(link.get("href", ""))
                    link["is_external"] = (
                        parsed.netloc != "" and parsed.netloc != base_domain
                    )
                    link["protocol"] = parsed.scheme
                    link["is_anchor"] = link["href"].startswith("#") or link["href"] == ""
                except Exception:
                    link["is_external"] = False

            return links_data
        except Exception:
            return []

    async def _check_images(self, page: Page) -> List[Dict]:
        """Periksa semua gambar: status loading, alt text, ukuran."""
        try:
            images_data = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('img')).map(img => ({
                    src: img.src.slice(0, 200),
                    alt: img.alt || '',
                    has_alt: img.hasAttribute('alt'),
                    alt_is_empty: img.hasAttribute('alt') && img.alt.trim() === '',
                    natural_width: img.naturalWidth,
                    natural_height: img.naturalHeight,
                    display_width: img.width,
                    display_height: img.height,
                    is_loaded: img.complete && img.naturalWidth > 0,
                    is_visible: img.offsetParent !== null,
                    loading: img.loading || ''
                }));
            }""")
            return images_data
        except Exception:
            return []

    async def _check_accessibility(self, page: Page) -> List[Dict]:
        """Cek isu aksesibilitas dasar."""
        try:
            issues = await page.evaluate("""() => {
                const issues = [];

                // Gambar tanpa alt
                document.querySelectorAll('img:not([alt])').forEach(img => {
                    issues.push({
                        type: 'missing_alt',
                        element: 'img',
                        src: img.src.slice(0, 100)
                    });
                });

                // Input tanpa label
                document.querySelectorAll(
                    'input:not([type="hidden"]):not([aria-label]):not([aria-labelledby])'
                ).forEach(inp => {
                    const id = inp.id;
                    const hasLabel = id && document.querySelector(`label[for="${id}"]`);
                    const inLabel = inp.closest('label');
                    if (!hasLabel && !inLabel) {
                        issues.push({
                            type: 'input_no_label',
                            element: 'input',
                            name: inp.name || inp.id || inp.type
                        });
                    }
                });

                // Button tanpa teks
                document.querySelectorAll('button').forEach(btn => {
                    const hasText = btn.textContent.trim().length > 0;
                    const hasAriaLabel = btn.getAttribute('aria-label');
                    const hasTitle = btn.getAttribute('title');
                    if (!hasText && !hasAriaLabel && !hasTitle) {
                        issues.push({ type: 'button_no_text', element: 'button' });
                    }
                });

                // Tidak ada heading
                const headings = document.querySelectorAll('h1,h2,h3,h4,h5,h6');
                if (headings.length === 0) {
                    issues.push({ type: 'no_headings', element: 'page' });
                }

                // Multiple H1
                const h1s = document.querySelectorAll('h1');
                if (h1s.length > 1) {
                    issues.push({
                        type: 'multiple_h1',
                        element: 'page',
                        count: h1s.length
                    });
                }

                // Link tanpa teks bermakna
                document.querySelectorAll('a[href]').forEach(a => {
                    const text = a.textContent.trim();
                    const ariaLabel = a.getAttribute('aria-label');
                    const generic = ['klik di sini', 'click here', 'here', 'baca selengkapnya',
                                     'read more', 'more', 'link'];
                    if (!ariaLabel && generic.includes(text.toLowerCase())) {
                        issues.push({
                            type: 'generic_link_text',
                            element: 'a',
                            text: text
                        });
                    }
                });

                // Contrast / color — hanya cek teks putih di latar putih (basic)
                // (deep contrast checks butuh library khusus)

                // Form tanpa legend/fieldset jika ada radio group
                document.querySelectorAll('input[type="radio"]').forEach(radio => {
                    if (!radio.closest('fieldset')) {
                        issues.push({
                            type: 'radio_no_fieldset',
                            element: 'input[radio]',
                            name: radio.name || ''
                        });
                    }
                });

                return issues;
            }""")
            return issues
        except Exception:
            return []