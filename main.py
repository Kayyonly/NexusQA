"""
🤖 AI Website Review Bot
Powered by Playwright + Claude AI

Usage:
  python main.py --url https://example.com
  python main.py --file index.html
  python main.py  (interactive mode)
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime

# Load .env otomatis saat script dijalankan
from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.text import Text
from rich import box

from checker import WebsiteChecker
from analyzer import AIAnalyzer

console = Console()

ASCII_BANNER = """
[bold blue]╔══════════════════════════════════════════╗
║      🤖  AI WEBSITE REVIEW BOT           ║
║   Claude · GPT · Gemini · Groq           ║
╚══════════════════════════════════════════╝[/bold blue]
"""


def print_quick_stats(result):
    table = Table(
        title="📊 Hasil Pemeriksaan",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="cyan",
    )
    table.add_column("Metrik", style="bold white", min_width=25)
    table.add_column("Nilai", justify="right", min_width=15)
    table.add_column("Status", justify="center", min_width=10)

    # Load time
    lt = result.load_time
    lt_color = "green" if lt < 3000 else ("yellow" if lt < 5000 else "red")
    lt_status = "✅ Cepat" if lt < 3000 else ("⚠️  Lambat" if lt < 5000 else "❌ Sangat Lambat")
    table.add_row("⏱️  Load Time", f"[{lt_color}]{lt:.0f} ms[/{lt_color}]", lt_status)

    # DOM Ready
    dom = result.dom_ready
    dom_color = "green" if dom < 2000 else ("yellow" if dom < 4000 else "red")
    table.add_row("🏗️  DOM Ready", f"[{dom_color}]{dom:.0f} ms[/{dom_color}]", "")

    # FCP
    if result.fcp:
        fcp_color = "green" if result.fcp < 1800 else ("yellow" if result.fcp < 3000 else "red")
        fcp_status = "✅ Bagus" if result.fcp < 1800 else ("⚠️  Perlu Optimasi" if result.fcp < 3000 else "❌ Buruk")
        table.add_row("🎨 First Contentful Paint", f"[{fcp_color}]{result.fcp:.0f} ms[/{fcp_color}]", fcp_status)

    table.add_section()

    # Console errors
    err_count = len(result.console_errors)
    err_color = "green" if err_count == 0 else "red"
    err_status = "✅ Bersih" if err_count == 0 else f"❌ {err_count} error"
    table.add_row("🐛 Console Errors", f"[{err_color}]{err_count}[/{err_color}]", err_status)

    # Console warnings
    warn_count = len(result.console_warnings)
    warn_color = "green" if warn_count == 0 else "yellow"
    table.add_row("⚠️  Console Warnings", f"[{warn_color}]{warn_count}[/{warn_color}]",
                  "✅ Bersih" if warn_count == 0 else f"⚠️  {warn_count} peringatan")

    # Network errors
    net_count = len(result.network_errors)
    net_color = "green" if net_count == 0 else "red"
    table.add_row("🔌 Network Errors", f"[{net_color}]{net_count}[/{net_color}]",
                  "✅ Bersih" if net_count == 0 else f"❌ {net_count} gagal")

    # Failed HTTP responses
    fail_count = len(result.failed_responses)
    fail_color = "green" if fail_count == 0 else "red"
    table.add_row("🌐 HTTP Errors (4xx/5xx)", f"[{fail_color}]{fail_count}[/{fail_color}]",
                  "✅ Bersih" if fail_count == 0 else f"❌ {fail_count} error")

    table.add_section()

    # Forms
    form_count = len(result.forms)
    table.add_row("📝 Form Ditemukan", f"[cyan]{form_count}[/cyan]",
                  f"ℹ️  {form_count} form" if form_count > 0 else "—")

    # Links
    link_count = len(result.links)
    ext_count = len([l for l in result.links if l.get("is_external")])
    table.add_row("🔗 Link Ditemukan", f"[cyan]{link_count}[/cyan]",
                  f"ℹ️  {ext_count} eksternal")

    # Images
    img_count = len(result.images)
    broken_imgs = len([i for i in result.images if not i.get("is_loaded")])
    img_color = "green" if broken_imgs == 0 else "red"
    table.add_row("🖼️  Gambar", f"[cyan]{img_count}[/cyan] ({broken_imgs} rusak)",
                  "✅ Semua Oke" if broken_imgs == 0 else f"[{img_color}]❌ {broken_imgs} rusak[/{img_color}]")

    table.add_section()

    # Accessibility
    a11y_count = len(result.accessibility_issues)
    a11y_color = "green" if a11y_count == 0 else ("yellow" if a11y_count < 5 else "red")
    table.add_row("♿ Aksesibilitas", f"[{a11y_color}]{a11y_count} isu[/{a11y_color}]",
                  "✅ Bersih" if a11y_count == 0 else f"⚠️  {a11y_count} isu")

    console.print(table)


def print_errors_detail(result):
    """Print detailed error information."""
    if result.console_errors:
        console.print("\n[bold red]❌ Console Errors:[/bold red]")
        for i, err in enumerate(result.console_errors[:10], 1):
            console.print(f"  [red]{i}.[/red] {err['text'][:200]}")
        if len(result.console_errors) > 10:
            console.print(f"  [dim]... dan {len(result.console_errors) - 10} error lainnya[/dim]")

    if result.network_errors:
        console.print("\n[bold red]🔌 Network Errors:[/bold red]")
        for i, err in enumerate(result.network_errors[:5], 1):
            console.print(f"  [red]{i}.[/red] [{err.get('method', 'GET')}] {err['url'][:120]}")
            console.print(f"     [dim]{str(err.get('error', 'Unknown'))[:100]}[/dim]")

    if result.failed_responses:
        console.print("\n[bold yellow]⚠️  HTTP Errors:[/bold yellow]")
        for i, res in enumerate(result.failed_responses[:10], 1):
            status_color = "red" if res["status"] >= 500 else "yellow"
            console.print(
                f"  [{status_color}]{i}. {res['status']} {res.get('status_text', '')}[/{status_color}]"
                f" — {res['url'][:120]}"
            )

    if result.accessibility_issues:
        console.print("\n[bold yellow]♿ Aksesibilitas Issues:[/bold yellow]")
        issue_map = {
            "missing_alt": "Gambar tanpa alt text",
            "input_no_label": "Input tanpa label",
            "button_no_text": "Button tanpa teks",
            "no_headings": "Halaman tanpa heading",
            "multiple_h1": "Lebih dari satu H1",
        }
        for i, issue in enumerate(result.accessibility_issues[:10], 1):
            desc = issue_map.get(issue["type"], issue["type"])
            detail = issue.get("src", "") or issue.get("name", "") or str(issue.get("count", ""))
            console.print(f"  [yellow]{i}.[/yellow] {desc}" + (f" — [dim]{detail[:80]}[/dim]" if detail else ""))


def save_report(result, ai_analysis, output_path, provider="AI"):
    """Save full report to text file."""
    lines = [
        "=" * 60,
        "        AI WEBSITE REVIEW BOT - LAPORAN LENGKAP",
        "=" * 60,
        f"Tanggal   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Target    : {result.url}",
        f"Judul     : {result.page_title}",
        "",
        "-" * 60,
        "PERFORMA",
        "-" * 60,
        f"Load Time            : {result.load_time:.0f} ms",
        f"DOM Content Loaded   : {result.dom_ready:.0f} ms",
        f"First Contentful Paint: {result.fcp:.0f} ms" if result.fcp else "First Contentful Paint: N/A",
        "",
        "-" * 60,
        "RINGKASAN ERROR",
        "-" * 60,
        f"Console Errors   : {len(result.console_errors)}",
        f"Console Warnings : {len(result.console_warnings)}",
        f"Network Errors   : {len(result.network_errors)}",
        f"HTTP Errors      : {len(result.failed_responses)}",
        "",
        "-" * 60,
        "UI & NAVIGASI",
        "-" * 60,
        f"Form     : {len(result.forms)}",
        f"Link     : {len(result.links)} ({len([l for l in result.links if l.get('is_external')])} eksternal)",
        f"Gambar   : {len(result.images)} ({len([i for i in result.images if not i.get('is_loaded')])} rusak)",
        f"Aksesibilitas Issues: {len(result.accessibility_issues)}",
    ]

    if result.console_errors:
        lines += ["", "-" * 60, "DETAIL CONSOLE ERRORS", "-" * 60]
        for err in result.console_errors:
            lines.append(f"  • {err['text']}")

    if result.network_errors:
        lines += ["", "-" * 60, "DETAIL NETWORK ERRORS", "-" * 60]
        for err in result.network_errors:
            lines.append(f"  • [{err.get('method', 'GET')}] {err['url']}")
            lines.append(f"    Error: {err.get('error', 'Unknown')}")

    if result.failed_responses:
        lines += ["", "-" * 60, "DETAIL HTTP ERRORS", "-" * 60]
        for res in result.failed_responses:
            lines.append(f"  • {res['status']} {res.get('status_text', '')} - {res['url']}")

    if result.forms:
        lines += ["", "-" * 60, "DETAIL FORMS", "-" * 60]
        for i, form in enumerate(result.forms, 1):
            lines.append(f"  Form #{i}: method={form.get('method', 'get')}, inputs={len(form.get('inputs', []))}")

    if result.accessibility_issues:
        lines += ["", "-" * 60, "DETAIL AKSESIBILITAS", "-" * 60]
        for issue in result.accessibility_issues:
            lines.append(f"  • [{issue['type']}] {issue.get('element', '')} — {issue.get('src', '') or issue.get('name', '')}")

    if ai_analysis:
        provider_label = provider.upper()
        lines += ["", "=" * 60, f"ANALISIS AI ({provider_label})", "=" * 60, "", ai_analysis]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


async def main():
    console.print(ASCII_BANNER)

    parser = argparse.ArgumentParser(
        description="🤖 AI Website Review Bot — Testing otomatis + analisis AI"
    )
    parser.add_argument("--url", help="URL website (contoh: https://example.com)")
    parser.add_argument("--file", help="Path file HTML lokal")
    parser.add_argument(
        "--output",
        default=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        help="Nama file output laporan (default: report_TIMESTAMP.txt)",
    )
    parser.add_argument("--no-ai", action="store_true", help="Skip analisis AI")
    parser.add_argument("--no-screenshot", action="store_true", help="Skip screenshot")
    parser.add_argument(
        "--provider",
        choices=["claude", "openai", "gemini", "groq"],
        default=None,
        help="AI provider: claude | openai | gemini | groq",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="API key untuk provider yang dipilih",
    )
    args = parser.parse_args()

    # ── Interactive mode ─────────────────────────────────────────────────────
    if not args.url and not args.file:
        console.print("[yellow]Masukkan URL website atau path file HTML:[/yellow]")
        target = input(">>> ").strip()
        if not target:
            console.print("[red]Input tidak boleh kosong.[/red]")
            sys.exit(1)

        abs_path = os.path.abspath(target)
        if os.path.exists(abs_path):
            args.file = abs_path
            console.print(f"[dim]📄 Mode: file lokal[/dim]")
        else:
            args.url = target
            console.print(f"[dim]🌐 Mode: URL[/dim]")

    # ── Pilih provider jika belum ada (interactive) ──────────────────────────
    if not args.no_ai and not args.provider:
        from analyzer import PROVIDERS
        console.print("\n[bold yellow]🤖 Pilih AI Provider:[/bold yellow]")
        provider_list = list(PROVIDERS.items())
        for i, (key, desc) in enumerate(provider_list, 1):
            console.print(f"  [cyan]{i}.[/cyan] [bold]{key:8}[/bold] — {desc}")
        console.print()
        choice = input("Pilih nomor (1-4): ").strip()
        try:
            args.provider = provider_list[int(choice) - 1][0]
        except (ValueError, IndexError):
            console.print("[red]Pilihan tidak valid. Menggunakan Claude.[/red]")
            args.provider = "claude"

    # ── Ambil API key dari .env / environment variable ───────────────────────
    if not args.no_ai and not args.api_key:
        env_map = {
            "claude": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "groq":   "GROQ_API_KEY",
        }
        env_key = env_map.get(args.provider or "claude", "")
        args.api_key = os.environ.get(env_key, "")

        if args.api_key:
            console.print(f"[dim]🔑 API key dimuat dari .env ({env_key})[/dim]")
        else:
            # Fallback: tanya manual lewat terminal
            console.print(f"\n[yellow]⚠️  {env_key} tidak ditemukan di .env[/yellow]")
            console.print(f"[dim]Tambahkan ke file .env atau masukkan sekarang:[/dim]")
            import getpass
            args.api_key = getpass.getpass(f"{env_key} = ").strip()
            if not args.api_key:
                console.print("[red]API key kosong. Melewati analisis AI.[/red]")
                args.no_ai = True

    target = args.url or args.file
    is_file = bool(args.file)

    console.print(f"\n[bold]🎯 Target  :[/bold] {target}")
    console.print(f"[bold]🤖 Provider:[/bold] {args.provider or '(skip)'}")
    console.print(f"[bold]📄 Output  :[/bold] {args.output}")
    console.print()

    # ── STEP 1: Browser Testing ──────────────────────────────────────────────
    result = None
    steps = [
        "🌐 Membuka website di browser...",
        "⚡ Mengukur performa...",
        "🐛 Mencari console & network errors...",
        "📝 Menganalisis forms...",
        "🔗 Memeriksa links & gambar...",
        "♿ Cek aksesibilitas...",
        "📸 Mengambil screenshot...",
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(steps[0], total=None)

        checker = WebsiteChecker(take_screenshot=not args.no_screenshot)

        for i, step in enumerate(steps[1:], 1):
            await asyncio.sleep(0.2)
            progress.update(task, description=step)

        try:
            result = await checker.check(target, is_file=is_file)
            progress.update(task, description="[green]✅ Pemeriksaan selesai![/green]")
            await asyncio.sleep(0.3)
        except Exception as e:
            progress.update(task, description=f"[red]❌ Gagal: {str(e)[:60]}[/red]")
            console.print(f"\n[red]Error saat memeriksa website: {e}[/red]")
            sys.exit(1)

    # ── STEP 2: Print Stats ──────────────────────────────────────────────────
    console.print()
    print_quick_stats(result)
    print_errors_detail(result)

    # ── STEP 3: AI Analysis ──────────────────────────────────────────────────
    ai_analysis = None
    if not args.no_ai:
        console.print()
        provider_label = (args.provider or "claude").upper()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"🤖 {provider_label} sedang menganalisis...", total=None)
            try:
                analyzer = AIAnalyzer(
                    provider=args.provider or "claude",
                    api_key=args.api_key,
                )
                ai_analysis = analyzer.analyze(result)
                progress.update(task, description=f"[green]✅ Analisis {provider_label} selesai![/green]")
                await asyncio.sleep(0.3)
            except Exception as e:
                progress.update(task, description=f"[yellow]⚠️  AI gagal[/yellow]")
                console.print(f"\n[red]Error:[/red] {e}")

        if ai_analysis:
            console.print()
            console.print(
                Panel(
                    ai_analysis,
                    title=f"[bold green]🤖 Analisis oleh {provider_label}[/bold green]",
                    border_style="green",
                    padding=(1, 2),
                )
            )

    # ── STEP 4: Save Report ──────────────────────────────────────────────────
    save_report(result, ai_analysis, args.output, provider=args.provider or "AI")

    console.print()
    console.print(Panel.fit(
        f"[green]✅ Laporan disimpan ke: [bold]{args.output}[/bold][/green]\n"
        + (f"[green]📸 Screenshot: [bold]{result.screenshot_path}[/bold][/green]"
           if result.screenshot_path else ""),
        border_style="green",
        title="Selesai!"
    ))


if __name__ == "__main__":
    asyncio.run(main())