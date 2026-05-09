import argparse
import asyncio
from datetime import datetime

from playwright.async_api import async_playwright
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from analyzer import AIAnalyzer
from checker import WebsiteChecker
from interaction.interaction_tester import InteractionTester
from crawler import CrawlConfig, WebsiteCrawler
from report import build_report, write_reports
from utils import ensure_dirs, retry_async, setup_logger, slugify_url

BANNER = """
[bold cyan]╔══════════════════════════════════════════╗
║      🤖 AI WEBSITE REVIEW BOT           ║
╚══════════════════════════════════════════╝[/bold cyan]
"""

EXIT_COMMANDS = {"exit", "quit", "q"}


async def run(url: str, max_pages: int) -> tuple[str, str, dict]:
    ensure_dirs()
    logger = setup_logger()
    checker = WebsiteChecker()
    interaction_tester = InteractionTester()
    analyzer = AIAnalyzer()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)

        crawler = WebsiteCrawler(url, CrawlConfig(max_pages=max_pages))
        pages_to_check = await retry_async(crawler.crawl, context, retries=1, delay=1)
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

        await browser.close()

    report_payload = build_report(page_results, interaction_results)
    ai_result = analyzer.analyze(report_payload)
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
    txt_path, json_path, ai_result = await run(target_url, max_pages)
    ai_markdown = ai_result.get("markdown_report") or ai_result.get("analysis") or "Analisis tidak tersedia."
    console.print(
        Panel(
            Markdown(ai_markdown),
            title="🤖 ANALISIS GROQ AI",
            border_style="green",
            expand=True,
        )
    )
    console.print("[green]✅ Analisis selesai[/green]")
    console.print(f"[green]TXT report:[/green] {txt_path}")
    console.print(f"[green]JSON report:[/green] {json_path}")


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
