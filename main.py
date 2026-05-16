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
from auth.auth_crawler import AuthCrawler
from auth.auth_manager import AuthManager
from auth.auth_tester import AuthTester
from auth.session_manager import SessionManager
from checker import WebsiteChecker
from config.modes import get_mode_config
from interaction.interaction_tester import InteractionTester
from report import build_report, write_reports
from responsive.responsive_tester import ResponsiveTester
from smart_crawler.smart_crawler import SmartCrawlerConfig, SmartWebsiteCrawler
from utils import ensure_dirs, retry_async, setup_logger, slugify_url

BANNER = """
[bold cyan]╔══════════════════════════════════════════╗
║         🤖 TOOLS WEBSITE REVIEW          ║
╚══════════════════════════════════════════╝[/bold cyan]
"""

MODE_BANNER = """
[bold cyan]╔════════════════════════════╗
║      SELECT TEST MODE      ║
╚════════════════════════════╝[/bold cyan]
"""

EXIT_COMMANDS = {"exit", "quit", "q"}


async def run(url: str, mode_config: dict, auth_config: dict | None = None) -> tuple[str, str, dict]:
    ensure_dirs()
    logger = setup_logger()
    checker = WebsiteChecker()
    interaction_tester = InteractionTester()
    analyzer = AIAnalyzer()
    agent = AutonomousTestingAgent(max_actions=18)
    responsive_tester = ResponsiveTester()
    auth_manager = AuthManager(auth_config or {"enabled": False})
    session_manager = SessionManager()
    auth_crawler = AuthCrawler()
    auth_tester = AuthTester()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        session_options = session_manager.load() or {}
        context = await browser.new_context(ignore_https_errors=True, **session_options)

        auth_result: dict = {"status": "skipped", "reason": "disabled_by_mode"}
        if mode_config.get("auth"):
            auth_result = await auth_manager.login(context, url)
            if auth_result.get("status") == "success":
                await session_manager.save(context)

        crawler = SmartWebsiteCrawler(url, SmartCrawlerConfig(max_pages=mode_config["max_pages"], max_depth=3))
        crawl_result = await retry_async(crawler.crawl, context, retries=1, delay=1)
        pages_to_check = auth_crawler.prioritize(crawl_result.pages)[: mode_config["max_pages"]]
        logger.info("Crawled %s pages (mode=%s)", len(pages_to_check), mode_config["name"])

        page_results = []
        interaction_results = []
        for idx, page_url in enumerate(pages_to_check):
            shot_path = None
            if mode_config.get("screenshots"):
                shot_name = slugify_url(page_url) + ".png"
                shot_path = f"screenshots/{shot_name}"
            result = await retry_async(checker.check_page, context, page_url, shot_path, retries=1, delay=1)
            page_results.append(result.to_dict())

            if mode_config.get("interaction") and idx < mode_config.get("interaction_max_pages", 0):
                interaction_result = await retry_async(interaction_tester.test_page, context, page_url, retries=1, delay=1)
                interaction_results.append(interaction_result)
            logger.info("Checked page: %s", page_url)

        agent_result = {"status": "skipped", "reason": "disabled_by_mode"}
        if mode_config.get("ai_agent"):
            agent_result = await agent.run(context, url)

        responsive_result = {"devices": {"desktop": [], "tablet": [], "mobile": []}, "session_recording": {}, "video_paths": []}
        if mode_config.get("responsive"):
            responsive_result = await responsive_tester.test_pages(
                p,
                browser,
                pages_to_check,
                include_groups=mode_config.get("devices", ["desktop", "mobile"]),
                max_pages=mode_config.get("responsive_max_pages", 5),
                record_video=mode_config.get("video", False),
            )

        if mode_config.get("auth"):
            auth_test_result = await auth_tester.test_dashboard(context, pages_to_check) if auth_result.get("status") == "success" else {}
            auth_result["session"] = session_manager.inspect_state()
            auth_result["protected_routes"] = auth_crawler.summarize(pages_to_check)
            auth_result.update(auth_test_result)

        await browser.close()

    report_payload = build_report(
        page_results,
        interaction_results,
        crawl_result=crawl_result.__dict__,
        agent_session=agent_result,
        responsive_result=responsive_result,
    )
    report_payload["authenticated_testing"] = auth_result
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


def _read_interactive_mode(console: Console) -> str:
    console.print(MODE_BANNER)
    console.print("1. ⚡ Quick Mode")
    console.print("2. 🛠️ Standard Mode")
    console.print("3. 🚀 Deep Mode")
    choice = input("Pilih mode: ").strip()
    return {"1": "quick", "2": "standard", "3": "deep"}.get(choice, "standard")


def _render_mode_config(console: Console, mode_config: dict) -> None:
    console.print(f"[bold cyan]⚡ Mode:[/bold cyan] {mode_config['name'].upper()}")
    console.print(f"[bold cyan]📄 Max Pages:[/bold cyan] {mode_config['max_pages']}")
    console.print(f"[bold cyan]📱 Devices:[/bold cyan] {', '.join(mode_config['devices'])}")
    console.print(f"[bold cyan]🎥 Video:[/bold cyan] {'ON' if mode_config.get('video') else 'OFF'}")
    console.print(f"[bold cyan]🤖 AI Agent:[/bold cyan] {'ON' if mode_config.get('ai_agent') else 'OFF'}")


async def _run_single_session(console: Console, target_url: str, mode_config: dict, auth_config: dict | None = None) -> None:
    _render_mode_config(console, mode_config)
    console.print("[cyan]🌐 Membuka website...[/cyan]")
    console.print("[cyan]⚡ Mengukur performa...[/cyan]")
    console.print("[cyan]🐛 Mendeteksi error...[/cyan]")
    console.print("[cyan]🧪 Testing interaction...[/cyan]")
    console.print("[cyan]🕷️ Crawling website...[/cyan]")
    txt_path, json_path, ai_result = await run(target_url, mode_config, auth_config)
    raw_payload = ai_result.get("raw_report", {})
    _render_tools_summary(console, raw_payload)
    _render_technical_explanation(console, raw_payload)
    ai_markdown = ai_result.get("markdown_report") or ai_result.get("analysis") or "Analisis tidak tersedia."

    console.print(Panel(Markdown(ai_markdown), title="HASIL ANALISIS WEB🤖", border_style="green", expand=True))
    console.print("[green]✅ Analisis selesai[/green]")
    console.print(f"[green]TXT report:[/green] {txt_path}")
    console.print(f"[green]JSON report:[/green] {json_path}")

# existing render helpers unchanged

def _render_tools_summary(console: Console, payload: dict) -> None:
    summary = payload.get("summary", {})
    crawler = payload.get("smart_crawler", {})
    interaction = payload.get("interaction_testing", {}).get("summary", {})
    pages = payload.get("pages", [])
    total_warnings = 0
    total_forms = sum(len(p.get("forms", [])) for p in pages)
    screenshot_count = len([p for p in pages if p.get("screenshot_path")])
    total_issues = (summary.get("total_console_errors", 0)+summary.get("total_failed_requests", 0)+summary.get("total_broken_images", 0)+summary.get("total_accessibility_issues", 0)+interaction.get("validation_issues", 0))
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
    perf = tree.add("⚡ Performa"); perf.add(f"Load Time rata-rata: {summary.get('avg_load_time_ms', 0)} ms"); perf.add(f"DOM Ready rata-rata: {avg_dom_ready} ms"); perf.add(f"FCP rata-rata: {avg_fcp} ms")
    inter = tree.add("🧪 Interaction Engine"); inter.add(f"Buttons diuji: {interaction.get('buttons_total', 0)} | clicked: {interaction.get('buttons_clicked', 0)} | failed: {interaction.get('buttons_failed', 0)}"); inter.add(f"Forms diuji: {interaction.get('forms_tested', 0)} | validation issue: {interaction.get('validation_issues', 0)}"); inter.add(f"Modal issue: {interaction.get('modal_issues', 0)} | Dropdown issue: {interaction.get('dropdown_issues', 0)}")
    crawl_node = tree.add("🕷️ Crawl Engine"); crawl_node.add(f"Halaman ditemukan: {len(crawler.get('pages', []))}"); crawl_node.add(f"Route unik: {structure.get('total_routes', 0)} | internal link: {structure.get('total_internal_links', 0)} | external link: {structure.get('total_external_links', 0)}"); crawl_node.add(f"Broken route: {len(issues.get('broken_routes', []))} | dead link: {len(issues.get('dead_links', []))} | duplicate pattern: {len(issues.get('duplicate_pages', []))}")
    network = tree.add("🌐 Network & API"); network.add(f"Failed requests: {summary.get('total_failed_requests', 0)}"); network.add(f"Total link terdeteksi: {total_links}")
    accessibility = tree.add("♿ Accessibility"); accessibility.add(f"Issue aksesibilitas: {summary.get('total_accessibility_issues', 0)}"); accessibility.add(f"Broken images: {summary.get('total_broken_images', 0)}")
    screenshots = tree.add("📸 Screenshot"); screenshots.add(f"Screenshot halaman utama: {len([p for p in pages if p.get('screenshot_path')])}"); screenshots.add("Screenshot interaction dan AI agent tersimpan di folder screenshots/")
    responsive = tree.add("📱 Responsive Test"); responsive_payload = payload.get("responsive_testing", {}); devices = responsive_payload.get("devices", {}); responsive.add(f"Desktop/Tablet/Mobile checks: {len(devices.get('desktop', []))}/{len(devices.get('tablet', []))}/{len(devices.get('mobile', []))}"); responsive.add(f"Responsive videos: {len([v for v in responsive_payload.get('video_paths', []) if v])}")
    auth_payload = payload.get("authenticated_testing", {}); auth_node = tree.add("🔐 Auth Test"); auth_node.add(f"Login status: {auth_payload.get('status', 'skipped')}"); auth_node.add(f"Cookie/session: {auth_payload.get('session', {}).get('cookies', 0)}"); auth_node.add(f"Dashboard loaded: {auth_payload.get('dashboard_loaded', False)}")
    console.print(Rule("⚙️ PENJELASAN TEKNIS", style="bright_blue")); console.print(tree)


def _build_auth_config(args, mode_config: dict) -> dict:
    mode_auth = mode_config.get("auth", False)
    force_auth = bool(args and args.auth_enabled and mode_config.get("auth_override_allowed", False))
    enabled = mode_auth or force_auth
    return {
        "enabled": enabled,
        "login_url": getattr(args, "login_url", ""),
        "username": getattr(args, "auth_username", ""),
        "password": getattr(args, "auth_password", ""),
        "username_selector": getattr(args, "username_selector", "input[type=email],input[name*=email i],input[name*=user i]"),
        "password_selector": getattr(args, "password_selector", "input[type=password]"),
        "submit_selector": getattr(args, "submit_selector", "button[type=submit]"),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="AI Website Review Bot")
    parser.add_argument("--url", required=False, help="Target URL")
    parser.add_argument("--mode", choices=["quick", "standard", "deep"], default="standard", help="Execution mode")
    parser.add_argument("--max-pages", type=int, default=None, help="Override max pages to crawl")
    parser.add_argument("--auth-enabled", action="store_true", help="Enable authenticated testing")
    parser.add_argument("--login-url", default="", help="Login URL")
    parser.add_argument("--auth-username", default="", help="Login username/email")
    parser.add_argument("--auth-password", default="", help="Login password")
    parser.add_argument("--username-selector", default="input[type=email],input[name*=email i],input[name*=user i]")
    parser.add_argument("--password-selector", default="input[type=password]")
    parser.add_argument("--submit-selector", default="button[type=submit]")
    args = parser.parse_args()

    console = Console()
    console.print(BANNER)

    try:
        mode_name = args.mode if args.url else _read_interactive_mode(console)
        mode_config = get_mode_config(mode_name)
        if args.max_pages:
            mode_config["max_pages"] = args.max_pages

        if args.url:
            await _run_single_session(console, args.url, mode_config, _build_auth_config(args, mode_config))
            return

        while True:
            target_url = _read_interactive_url(console)
            if target_url is None:
                console.print("\n[cyan]👋 Terima kasih telah menggunakan AI Website Review Bot[/cyan]")
                break
            if target_url == "":
                continue
            await _run_single_session(console, target_url, mode_config, _build_auth_config(args, mode_config))
            console.print("\n" + "─" * 58 + "\n")

    except KeyboardInterrupt:
        console.print("\n[cyan]👋 Terima kasih telah menggunakan AI Website Review Bot[/cyan]")


if __name__ == "__main__":
    asyncio.run(main())
