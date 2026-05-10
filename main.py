import argparse
import asyncio
from datetime import datetime

from playwright.async_api import async_playwright
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.tree import Tree

from ai_agent.agent import AutonomousTestingAgent
from analyzer import AIAnalyzer
from checker import WebsiteChecker
from interaction.interaction_tester import InteractionTester
from report import build_report, write_reports
from smart_crawler.smart_crawler import SmartCrawlerConfig, SmartWebsiteCrawler
from utils import ensure_dirs, retry_async, setup_logger, slugify_url

BANNER = """
[bold cyan]╔══════════════════════════════════════════╗
║         🤖 TOOLS WEBSITE REVIEW           ║
╚══════════════════════════════════════════╝[/bold cyan]
"""

EXIT_COMMANDS = {"exit", "quit", "q"}


async def run(url: str, max_pages: int) -> tuple[str, str, dict]:
    ensure_dirs()
    logger = setup_logger()
    checker = WebsiteChecker()
    interaction_tester = InteractionTester()
    analyzer = AIAnalyzer()
    agent = AutonomousTestingAgent(max_actions=18)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)

        crawler = SmartWebsiteCrawler(url, SmartCrawlerConfig(max_pages=max_pages, max_depth=3))
        crawl_result = await retry_async(crawler.crawl, context, retries=1, delay=1)
        pages_to_check = crawl_result.pages
        logger.info("Crawled %s pages", len(pages_to_check))

        page_results = []
        interaction_results = []
        for page_url in pages_to_check:
            shot_name = slugify_url(page_url) + ".png"
            shot_path = f"screenshots/{shot_name}"
            result = await retry_async(checker.check_page, context, page_url, shot_path, retries=1, delay=1)
            page_results.append(result.to_dict())
            interaction_result = await retry_async(interaction_tester.test_page, context, page_url, retries=1, delay=1)
            interaction_results.append(interaction_result)
            logger.info("Checked page: %s", page_url)

        agent_result = await agent.run(context, url)

        await browser.close()

    report_payload = build_report(page_results, interaction_results, crawl_result=crawl_result.__dict__, agent_session=agent_result)
    ai_result = analyzer.analyze(report_payload)
    ai_result["raw_report"] = report_payload
    base_name = "website_review_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    txt_path, json_path = write_reports(base_name, report_payload, ai_result)
    return txt_path, json_path, ai_result


def _read_interactive_url(console: Console) -> str | None:
    console.print("[bold yellow]Masukkan URL website (atau ketik exit/quit/q):[/bold yellow]")
    raw = input(">>> ").strip()
    if not raw:
        console.print("[red]URL tidak boleh kosong.[/red]\n")
        return ""
    if raw.lower() in EXIT_COMMANDS:
        return None
    return raw


async def _run_single_session(console: Console, target_url: str, max_pages: int) -> None:
    console.print("[cyan]🌐 Membuka website...[/cyan]")
    console.print("[cyan]⚡ Mengukur performa...[/cyan]")
    console.print("[cyan]🐛 Mendeteksi error...[/cyan]")
    console.print("[cyan]🧪 Testing interaction...[/cyan]")
    console.print("[cyan]🕷️ Crawling website...[/cyan]")
    txt_path, json_path, ai_result = await run(target_url, max_pages)
    raw_payload = ai_result.get("raw_report", {})
    _render_tools_summary(console, raw_payload)
    _render_technical_explanation(console, raw_payload)
    console.print(Rule("🤖HASIL ANALISIS WEB", style="green"))
    ai_markdown = ai_result.get("markdown_report") or ai_result.get("analysis") or "Analisis tidak tersedia."

    console.print(Panel(Markdown(ai_markdown), title="HASIL ANALISIS WEB🤖", border_style="green", expand=True))
    console.print("[green]✅ Analisis selesai[/green]")
    console.print(f"[green]TXT report:[/green] {txt_path}")
    console.print(f"[green]JSON report:[/green] {json_path}")


def _render_tools_summary(console: Console, payload: dict) -> None:
    summary = payload.get("summary", {})
    crawler = payload.get("smart_crawler", {})
    interaction = payload.get("interaction_testing", {}).get("summary", {})
    pages = payload.get("pages", [])

    total_warnings = 0
    total_forms = sum(len(p.get("forms", [])) for p in pages)
    screenshot_count = len([p for p in pages if p.get("screenshot_path")])
    total_issues = (
        summary.get("total_console_errors", 0)
        + summary.get("total_failed_requests", 0)
        + summary.get("total_broken_images", 0)
        + summary.get("total_accessibility_issues", 0)
        + interaction.get("validation_issues", 0)
    )

    table = Table(title="📊 HASIL TESTING TOOLS", show_lines=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Total page crawled", str(summary.get("pages_crawled", 0)))
    table.add_row("Total interaction tested", str(interaction.get("pages_tested", 0)))
    table.add_row("Total console error", str(summary.get("total_console_errors", 0)))
    table.add_row("Total warning", str(total_warnings))
    table.add_row("Total failed request", str(summary.get("total_failed_requests", 0)))
    table.add_row("Total form", str(total_forms))
    table.add_row("Total button", str(interaction.get("buttons_total", 0)))
    table.add_row("Total issue", str(total_issues))
    table.add_row("Screenshot count", str(screenshot_count))
    table.add_row("Smart crawler route", str(crawler.get("structure", {}).get("total_routes", 0)))

    console.print(Rule("📊 HASIL TESTING TOOLS", style="cyan"))
    console.print(table)


def _render_technical_explanation(console: Console, payload: dict) -> None:
    pages = payload.get("pages", [])
    summary = payload.get("summary", {})
    interaction = payload.get("interaction_testing", {}).get("summary", {})
    crawler = payload.get("smart_crawler", {})
    structure = crawler.get("structure", {})
    issues = crawler.get("issues", {})

    avg_dom_ready = round(sum(p.get("dom_ready_ms", 0) for p in pages) / max(len(pages), 1), 2)
    avg_fcp = round(sum((p.get("fcp_ms") or 0) for p in pages) / max(len(pages), 1), 2)
    total_links = sum(len(p.get("links", [])) for p in pages)

    tree = Tree("⚙️ PENJELASAN TEKNIS", guide_style="bold bright_blue")
    perf = tree.add("⚡ Performa")
    perf.add(f"Load Time rata-rata: {summary.get('avg_load_time_ms', 0)} ms")
    perf.add(f"DOM Ready rata-rata: {avg_dom_ready} ms")
    perf.add(f"FCP rata-rata: {avg_fcp} ms")

    inter = tree.add("🧪 Interaction Engine")
    inter.add(f"Buttons diuji: {interaction.get('buttons_total', 0)} | clicked: {interaction.get('buttons_clicked', 0)} | failed: {interaction.get('buttons_failed', 0)}")
    inter.add(f"Forms diuji: {interaction.get('forms_tested', 0)} | validation issue: {interaction.get('validation_issues', 0)}")
    inter.add(f"Modal issue: {interaction.get('modal_issues', 0)} | Dropdown issue: {interaction.get('dropdown_issues', 0)}")

    crawl_node = tree.add("🕷️ Crawl Engine")
    crawl_node.add(f"Halaman ditemukan: {len(crawler.get('pages', []))}")
    crawl_node.add(f"Route unik: {structure.get('total_routes', 0)} | internal link: {structure.get('total_internal_links', 0)} | external link: {structure.get('total_external_links', 0)}")
    crawl_node.add(f"Broken route: {len(issues.get('broken_routes', []))} | dead link: {len(issues.get('dead_links', []))} | duplicate pattern: {len(issues.get('duplicate_pages', []))}")

    network = tree.add("🌐 Network & API")
    network.add(f"Failed requests: {summary.get('total_failed_requests', 0)}")
    network.add(f"Total link terdeteksi: {total_links}")

    accessibility = tree.add("♿ Accessibility")
    accessibility.add(f"Issue aksesibilitas: {summary.get('total_accessibility_issues', 0)}")
    accessibility.add(f"Broken images: {summary.get('total_broken_images', 0)}")

    screenshots = tree.add("📸 Screenshot")
    screenshots.add(f"Screenshot halaman utama: {len([p for p in pages if p.get('screenshot_path')])}")
    screenshots.add("Screenshot interaction dan AI agent tersimpan di folder screenshots/")

    responsive = tree.add("📱 Responsive Test")
    responsive.add("Belum ada viewport matrix test otomatis; saat ini pengujian dilakukan pada context default browser.")

    console.print(Rule("⚙️ PENJELASAN TEKNIS", style="bright_blue"))
    console.print(tree)


async def main() -> None:
    parser = argparse.ArgumentParser(description="AI Website Review Bot")
    parser.add_argument("--url", required=False, help="Target URL")
    parser.add_argument("--max-pages", type=int, default=5, help="Max pages to crawl")
    args = parser.parse_args()

    console = Console()
    console.print(BANNER)

    try:
        if args.url:
            await _run_single_session(console, args.url, args.max_pages)
            return

        # Persistent interactive mode
        while True:
            target_url = _read_interactive_url(console)
            if target_url is None:
                console.print("\n[cyan]👋 Terima kasih telah menggunakan AI Website Review Bot[/cyan]")
                break
            if target_url == "":
                continue
            await _run_single_session(console, target_url, args.max_pages)
            console.print("\n" + "─" * 58 + "\n")

    except KeyboardInterrupt:
        console.print("\n[cyan]👋 Terima kasih telah menggunakan AI Website Review Bot[/cyan]")


if __name__ == "__main__":
    asyncio.run(main())