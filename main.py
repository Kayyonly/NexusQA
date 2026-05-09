"""
🤖 AI Website Review Bot
Powered by Playwright + Groq AI

Usage:
  python main.py --url https://example.com
  python main.py
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import box

from checker import WebsiteChecker
from analyzer import AIAnalyzer

console = Console()

ASCII_BANNER = """
[bold blue]╔══════════════════════════════════════════╗
║      🤖  AI WEBSITE REVIEW BOT           ║
║         Powered by Groq AI               ║
╚══════════════════════════════════════════╝[/bold blue]
"""


# ─────────────────────────────────────────────────────────────
# QUICK STATS
# ─────────────────────────────────────────────────────────────

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
    table.add_column("Status", justify="center", min_width=15)

    # Load time
    lt = result.load_time
    lt_color = "green" if lt < 3000 else ("yellow" if lt < 5000 else "red")

    table.add_row(
        "⏱️ Load Time",
        f"[{lt_color}]{lt:.0f} ms[/{lt_color}]",
        "✅ Cepat" if lt < 3000 else "⚠️ Lambat"
    )

    # FCP
    if result.fcp:
        fcp_color = "green" if result.fcp < 1800 else ("yellow" if result.fcp < 3000 else "red")

        table.add_row(
            "🎨 FCP",
            f"[{fcp_color}]{result.fcp:.0f} ms[/{fcp_color}]",
            "✅ Bagus" if result.fcp < 1800 else "⚠️ Optimasi"
        )

    table.add_section()

    # Errors
    table.add_row(
        "🐛 Console Errors",
        str(len(result.console_errors)),
        "✅ Bersih" if len(result.console_errors) == 0 else "❌ Ada Error"
    )

    table.add_row(
        "🌐 HTTP Errors",
        str(len(result.failed_responses)),
        "✅ Bersih" if len(result.failed_responses) == 0 else "❌ Error"
    )

    table.add_row(
        "♿ Accessibility",
        str(len(result.accessibility_issues)),
        "✅ Oke" if len(result.accessibility_issues) == 0 else "⚠️ Ada Issue"
    )

    console.print(table)


# ─────────────────────────────────────────────────────────────
# SAVE REPORT
# ─────────────────────────────────────────────────────────────

def save_report(result, ai_analysis, output_path):
    lines = [
        "=" * 60,
        "AI WEBSITE REVIEW BOT",
        "=" * 60,
        f"Tanggal : {datetime.now()}",
        f"Target  : {result.url}",
        "",
        "PERFORMA",
        "-" * 60,
        f"Load Time : {result.load_time:.0f} ms",
        f"DOM Ready : {result.dom_ready:.0f} ms",
        f"FCP       : {result.fcp}",
        "",
        "ERROR",
        "-" * 60,
        f"Console Errors : {len(result.console_errors)}",
        f"HTTP Errors    : {len(result.failed_responses)}",
        f"Accessibility  : {len(result.accessibility_issues)}",
    ]

    if ai_analysis:
        lines += [
            "",
            "=" * 60,
            "ANALISIS GROQ AI",
            "=" * 60,
            "",
            ai_analysis
        ]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

async def main():

    console.print(ASCII_BANNER)

    parser = argparse.ArgumentParser(
        description="🤖 AI Website Review Bot"
    )

    parser.add_argument(
        "--url",
        help="URL website"
    )

    parser.add_argument(
        "--output",
        default=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        help="Nama file output"
    )

    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip analisis AI"
    )

    parser.add_argument(
        "--no-screenshot",
        action="store_true",
        help="Skip screenshot"
    )

    args = parser.parse_args()

    # Default provider
    args.provider = "groq"

    # ─────────────────────────────────────────────────────────
    # INPUT URL
    # ─────────────────────────────────────────────────────────

    if not args.url:
        console.print("[yellow]Masukkan URL website:[/yellow]")
        args.url = input(">>> ").strip()

        if not args.url:
            console.print("[red]URL tidak boleh kosong[/red]")
            sys.exit(1)

    # ─────────────────────────────────────────────────────────
    # API KEY
    # ─────────────────────────────────────────────────────────

    api_key = os.getenv("GROQ_API_KEY", "")

    if not api_key and not args.no_ai:
        console.print("[red]GROQ_API_KEY tidak ditemukan di .env[/red]")
        sys.exit(1)

    target = args.url

    console.print(f"\n[bold]🎯 Target:[/bold] {target}")
    console.print(f"[bold]🤖 AI:[/bold] Groq")
    console.print(f"[bold]📄 Output:[/bold] {args.output}")

    # ─────────────────────────────────────────────────────────
    # WEBSITE CHECK
    # ─────────────────────────────────────────────────────────

    result = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        task = progress.add_task(
            "🌐 Memeriksa website...",
            total=None
        )

        checker = WebsiteChecker(
            take_screenshot=not args.no_screenshot
        )

        try:
            result = await checker.check(
                target,
                is_file=False
            )

            progress.update(
                task,
                description="[green]✅ Pemeriksaan selesai[/green]"
            )

            await asyncio.sleep(0.5)

        except Exception as e:
            progress.update(
                task,
                description=f"[red]❌ Error: {str(e)}[/red]"
            )

            console.print(f"\n[red]ERROR:[/red] {e}")
            sys.exit(1)

    # ─────────────────────────────────────────────────────────
    # PRINT STATS
    # ─────────────────────────────────────────────────────────

    console.print()
    print_quick_stats(result)

    # ─────────────────────────────────────────────────────────
    # AI ANALYSIS
    # ─────────────────────────────────────────────────────────

    ai_analysis = None

    if not args.no_ai:

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            task = progress.add_task(
                "🤖 Groq AI sedang menganalisis...",
                total=None
            )

            try:

                analyzer = AIAnalyzer(
                    provider="groq",
                    api_key=api_key
                )

                ai_analysis = analyzer.analyze(result)

                progress.update(
                    task,
                    description="[green]✅ Analisis selesai[/green]"
                )

                await asyncio.sleep(0.5)

            except Exception as e:

                progress.update(
                    task,
                    description="[red]❌ AI gagal[/red]"
                )

                console.print(f"\n[red]AI ERROR:[/red] {e}")

    # ─────────────────────────────────────────────────────────
    # SHOW AI RESULT
    # ─────────────────────────────────────────────────────────

    if ai_analysis:

        console.print()

        console.print(
            Panel(
                ai_analysis,
                title="[bold green]🤖 Analisis Groq AI[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
        )

    # ─────────────────────────────────────────────────────────
    # SAVE REPORT
    # ─────────────────────────────────────────────────────────

    save_report(
        result,
        ai_analysis,
        args.output
    )

    console.print()

    console.print(
        Panel.fit(
            f"[green]✅ Laporan disimpan:[/green]\n[bold]{args.output}[/bold]",
            border_style="green",
            title="Selesai"
        )
    )

if __name__ == "__main__":
    asyncio.run(main())
