#!/usr/bin/env python3
"""
cli_app/main.py — NSU Degree Audit Engine (Premium CLI)
═══════════════════════════════════════════════════════════
OCR-based transcript analysis with premium terminal UI.
Uses Cloud Run backend API (single backend for CLI, Web, Flutter).

Flow: Upload PDF → Cloud API → OCR Extract → View 3-Level Analysis

Usage:
  python cli_app/main.py                    # Cloud mode (default)
  python cli_app/main.py <transcript.pdf>   # Direct scan mode
  python cli_app/main.py --local            # Use local OCR instead

Environment:
  USE_CLOUD_API=false                         # Force local OCR
  CLOUD_API_URL=https://ocrapi.nsunexus.app   # Cloud API endpoint
"""

import os
import sys
import re
import time
import json
from pathlib import Path

# Add project root and src to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich import box

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Initialize console
console = Console(force_terminal=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLOUD API CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Use custom domain for Cloud Run backend
CLOUD_API_URL = os.environ.get("CLOUD_API_URL", "https://ocrapi.nsunexus.app")

# Default to cloud API - single backend for all
USE_CLOUD_API = os.environ.get("USE_CLOUD_API", "true").lower() == "true" and "--local" not in sys.argv

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  IMPORTS FROM SHARED BACKEND — single source of truth (src/core.py)
#  detect_program() and run_full_analysis() live ONLY in src/core.py
#  CLI, Web, and Flutter all import from here — zero duplication
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / '.env')
except ImportError:
    pass

from core import run_full_analysis  # THE analysis engine — same for all 3 apps

# OCR engine: try web API first (same as website), fall back to local
try:
    from ocr_web import WebOCR as TranscriptOCR
except ImportError:
    from ocr_engine import TranscriptOCR

# Knowledge base path
KB_PATH = PROJECT_ROOT / 'knowledge_base.md'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UI HELPERS (CLI-specific — Rich terminal rendering only)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def create_header():
    ascii_art = r"""
    _   _  ____  _   _   ____  _____ ____ ____  _____ _____      _   _   _ ____ ___ _____
   | \ | |/ ___|| | | | |  _ \| ____/ ___|  _ \| ____| ____|    / \ | | | |  _ \_ _|_   _|
   |  \| |\___ \| | | | | | | |  _|| |  _| |_) |  _| |  _|     / _ \| | | | | | | |  | |
   | |\  | ___) | |_| | | |_| | |__| |_| |  _ <| |___| |___   / ___ \ |_| | |_| | |  | |
   |_| \_||____/ \___/  |____/|_____\____|_| \_\_____|_____| /_/   \_\___/|____/___| |_|
    """
    return Panel(
        Text(ascii_art, style="bold cyan", justify="center"),
        title="[bold bright_cyan] NSU DEGREE AUDIT ENGINE [/bold bright_cyan]",
        subtitle="[dim cyan]North South University | Premium CLI v3.0 | OCR Powered[/dim cyan]",
        border_style="bright_cyan",
        box=box.DOUBLE,
        padding=(0, 1),
    )


def grade_color(grade):
    if not grade:
        return "dim"
    if grade.startswith('A'):
        return "green"
    if grade.startswith('B'):
        return "cyan"
    if grade.startswith('C'):
        return "yellow"
    if grade.startswith('D'):
        return "bright_red"
    if grade == 'F':
        return "red"
    return "dim"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLOUD API FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def scan_transcript_cloud(file_path):
    """Upload transcript to cloud API and get analysis results.
    Uses the same backend as web app - just via HTTP instead of local."""
    import requests
    
    if not Path(file_path).exists():
        return None, f"File not found: {file_path}"
    
    file_name = Path(file_path).name
    file_size = Path(file_path).stat().st_size
    file_size_str = f"{file_size/1024:.0f} KB" if file_size < 1024*1024 else f"{file_size/1024/1024:.1f} MB"
    
    console.print()
    console.print(Panel(
        f"[bold white]{file_name}[/bold white]  [dim]({file_size_str})[/dim]\n"
        f"[dim cyan]Cloud API: {CLOUD_API_URL}[/dim cyan]",
        title="[bold bright_cyan]  ☁️  Cloud Scanning  [/bold bright_cyan]",
        border_style="cyan",
        box=box.DOUBLE_EDGE,
    ))
    console.print()
    
    _log("[CLOUD]", f"Connecting to {CLOUD_API_URL}...", "dim white", "bold blue")
    
    try:
        with Progress(
            SpinnerColumn("dots12", style="cyan"),
            TextColumn("[cyan]{task.description}[/cyan]"),
            BarColumn(bar_width=40, style="cyan", complete_style="bright_cyan"),
            transient=True,
        ) as progress:
            task = progress.add_task("Uploading to cloud...", total=None)
            
            with open(file_path, 'rb') as f:
                files = {'file': (file_name, f, 'application/pdf')}
                response = requests.post(
                    f"{CLOUD_API_URL}/upload",
                    files=files,
                    timeout=120
                )
        
        if response.status_code != 200:
            return None, f"Cloud API error: {response.status_code}"
        
        data = response.json()
        if not data.get('success'):
            return None, data.get('error', 'Unknown error from cloud API')
        
        result = data.get('data', {})
        
        _log("[OK]", f"Cloud processing complete ✓", "green", "bold green")
        console.print()
        
        return result, None
        
    except requests.exceptions.ConnectionError:
        return None, f"Cannot connect to cloud API at {CLOUD_API_URL}"
    except requests.exceptions.Timeout:
        return None, "Cloud API request timed out (120s)"
    except Exception as e:
        return None, f"Cloud API error: {str(e)}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  OCR SCANNING (mirrors website /upload flow exactly)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _log(tag, msg, style="cyan", tag_style="bold cyan"):
    """Print a terminal-style log line (same format as website STAGE_LOGS)."""
    console.print(f"  [{tag_style}]{tag:>8}[/{tag_style}]  [{style}]{msg}[/{style}]")
    time.sleep(0.08)


def scan_transcript(file_path):
    """Scan PDF/image using OCR → run_full_analysis from src.core.
    Shows the same 5-phase scanning logs as the website."""
    if not Path(file_path).exists():
        return None, f"File not found: {file_path}"

    file_size = Path(file_path).stat().st_size
    file_size_str = f"{file_size/1024:.0f} KB" if file_size < 1024*1024 else f"{file_size/1024/1024:.1f} MB"
    file_name = Path(file_path).name

    # ── HEADER ──────────────────────────────────────────────────────────
    console.print()
    console.print(Panel(
        f"[bold white]{file_name}[/bold white]  [dim]({file_size_str})[/dim]",
        title="[bold bright_cyan]  Scanning Transcript  [/bold bright_cyan]",
        border_style="cyan",
        box=box.DOUBLE_EDGE,
    ))
    console.print()

    # ── PHASE 1: Initialize (same as website STAGE_LOGS.init) ──────────
    console.print("[bold cyan]  ── Phase 1/5: Initialize Engine ──[/bold cyan]")
    _log("[SYS]", "Loading OCR pipeline...", "dim white", "bold blue")
    _log("[SYS]", "Initializing OCR engine...", "dim white", "bold blue")
    _log("[CFG]", "Max file size: 16MB", "dim", "yellow")
    _log("[CFG]", "Supported formats: PDF, PNG, JPG", "dim", "yellow")
    _log("[OK]", "Pipeline initialized ✓", "green", "bold green")
    console.print()

    # ── PHASE 2: Preprocess (same as website STAGE_LOGS.preprocess) ────
    console.print("[bold cyan]  ── Phase 2/5: Image Processing ──[/bold cyan]")
    _log("[IMG]", "Reading file buffer...", "dim white", "bold blue")
    _log("[IMG]", "Detecting document format...", "dim white", "bold blue")
    _log("[PRE]", "Rendering document...", "dim", "yellow")
    _log("[PRE]", "Applying image enhancements...", "dim", "yellow")
    _log("[PRE]", "Optimizing for OCR...", "dim", "yellow")
    _log("[OK]", "Preprocessing complete ✓", "green", "bold green")
    console.print()

    # ── PHASE 3: Text Extraction (actual OCR happens here) ─────────────
    console.print("[bold cyan]  ── Phase 3/5: Text Extraction ──[/bold cyan]")
    _log("[OCR]", "Sending to OCR engine...", "dim white", "bold blue")

    with Progress(
        SpinnerColumn("dots12", style="cyan"),
        TextColumn("[cyan]{task.description}[/cyan]"),
        BarColumn(bar_width=40, style="cyan", complete_style="bright_cyan"),
        transient=True,
    ) as progress:
        task = progress.add_task("Processing document...", total=None)
        ocr = TranscriptOCR()
        ocr_result = ocr.extract(file_path)

    _log("[OCR]", "Processing document...", "dim white", "bold blue")
    _log("[OCR]", "Extracting text blocks...", "dim white", "bold blue")
    _log("[TXT]", "Parsing extracted content...", "dim white", "bold blue")

    if not ocr_result.success:
        _log("[ERR]", f"OCR failed: {ocr_result.error}", "red", "bold red")
        return None, ocr_result.error or "OCR extraction failed"

    if ocr_result.course_count == 0:
        _log("[ERR]", "No courses found in document", "red", "bold red")
        return None, "No courses found. Please upload a clear transcript PDF/image."

    _log("[OK]", f"Text extraction complete — {ocr_result.course_count} courses found ✓", "green", "bold green")
    console.print()

    # ── Show extracted courses table (same as website review table) ─────
    course_table = Table(
        title=f"[bold]Extracted Courses ({ocr_result.course_count})[/bold]",
        box=box.ROUNDED, border_style="cyan", show_lines=False,
    )
    course_table.add_column("Course", style="bold white", width=12)
    course_table.add_column("Credits", justify="center", width=8)
    course_table.add_column("Grade", justify="center", width=8)
    course_table.add_column("Semester", style="dim", width=16)

    for c in ocr_result.courses:
        g_style = grade_color(c.grade)
        course_table.add_row(
            c.course_code, str(c.credits),
            f"[{g_style}]{c.grade}[/{g_style}]",
            c.semester or "—",
        )
    console.print(course_table)
    console.print()

    # ── Approval gate (same as website "Approve & Continue") ───────────
    if not Confirm.ask("[bold cyan]Approve & Continue Analysis?[/bold cyan]", default=True):
        return None, "Cancelled by user"

    console.print()

    # Build courses list (same format as website)
    courses = [
        {'course_code': c.course_code, 'credits': c.credits,
         'grade': c.grade, 'semester': c.semester}
        for c in ocr_result.courses
    ]

    # ── PHASE 4: Data Parsing (same as website STAGE_LOGS.parse) ───────
    console.print("[bold cyan]  ── Phase 4/5: Data Parsing ──[/bold cyan]")
    _log("[PARSE]", "Analyzing extracted text...", "dim white", "bold blue")
    _log("[PARSE]", "Identifying course codes...", "dim white", "bold blue")
    _log("[PARSE]", "Extracting grades...", "dim white", "bold blue")
    _log("[PARSE]", "Extracting credit hours...", "dim white", "bold blue")
    _log("[PARSE]", "Resolving retakes...", "dim", "yellow")
    _log("[PARSE]", "Detecting semesters...", "dim white", "bold blue")
    _log("[OK]", "Data parsing complete ✓", "green", "bold green")
    console.print()

    # ── PHASE 5: Analysis (same as website STAGE_LOGS.analyze) ─────────
    console.print("[bold cyan]  ── Phase 5/5: Running Analysis ──[/bold cyan]")
    _log("[L1]", "Running credit tally...", "dim white", "bold blue")
    _log("[L1]", "Calculating earned credits...", "dim white", "bold blue")

    # ═══════════════════════════════════════════════════════════════════
    # Call the SHARED analysis engine from src/core.py
    # This is THE SAME function the website calls — zero duplication
    # ═══════════════════════════════════════════════════════════════════
    result = run_full_analysis(courses, kb_path=str(KB_PATH))

    _log("[L2]", "Computing CGPA...", "dim white", "bold blue")
    _log("[L2]", "Determining academic standing...", "dim white", "bold blue")
    _log("[L2]", "Checking waiver eligibility...", "dim", "yellow")
    _log("[L3]", "Running degree audit...", "dim white", "bold blue")
    _log("[L3]", "Checking graduation requirements...", "dim", "yellow")
    _log("[OK]", "Analysis complete ✓", "green", "bold green")
    console.print()

    # Build OCR info (same as website)
    ocr_info = {
        'engine': ocr_result.engine_used,
        'confidence': round(ocr_result.confidence_score * 100, 1),
        'raw_text_count': len(ocr_result.raw_text),
        'student_name': ocr_result.student_name or 'N/A',
        'student_id': ocr_result.student_id or 'N/A',
        'cgpa_from_pdf': ocr_result.cgpa,
        'total_credits_from_pdf': getattr(ocr_result, 'total_credits', 0),
    }

    # CGPA verification (same as website)
    if ocr_result.cgpa > 0 and result.get('level2'):
        calculated_cgpa = result['level2']['cgpa']
        if abs(calculated_cgpa - ocr_result.cgpa) > 0.05:
            result['cgpa_warning'] = {
                'message': 'CGPA mismatch detected',
                'pdf_value': ocr_result.cgpa,
                'calculated_value': calculated_cgpa,
                'difference': round(abs(calculated_cgpa - ocr_result.cgpa), 2)
            }

    result['ocr_info'] = ocr_info
    return result, None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DISPLAY FUNCTIONS (Rich UI — only rendering, no logic)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def show_ocr_summary(ocr_info, course_count):
    summary = Table.grid(expand=True, padding=(0, 2))
    summary.add_column(justify="left")
    summary.add_column(justify="left")
    summary.add_column(justify="left")
    summary.add_column(justify="right")
    summary.add_row(
        f"[dim]Student:[/dim] [bold white]{ocr_info['student_name']}[/bold white]",
        f"[dim]ID:[/dim] [bold white]{ocr_info['student_id']}[/bold white]",
        f"[dim]Courses:[/dim] [bold green]{course_count}[/bold green]",
        f"[dim]Confidence:[/dim] [bold cyan]{ocr_info['confidence']}%[/bold cyan]",
    )
    console.print(Panel(
        summary,
        title="[bold green]  ✓ Extraction Complete  [/bold green]",
        subtitle=f"[dim]OCR Engine: {ocr_info['engine']}[/dim]",
        border_style="green", box=box.DOUBLE_EDGE, padding=(1, 2),
    ))


def show_level1(data):
    clear_screen()
    console.print(create_header())
    level1 = data['level1']

    console.print(Panel("[bold green]Level 1: Credit Tally[/bold green]", border_style="green", box=box.HEAVY))

    stats = Table(box=box.ROUNDED, border_style="cyan", expand=True, show_header=False)
    stats.add_column("Label", style="dim", justify="center")
    stats.add_column("Value", style="bold white", justify="center")
    stats.add_column("Label", style="dim", justify="center")
    stats.add_column("Value", style="bold white", justify="center")
    stats.add_column("Label", style="dim", justify="center")
    stats.add_column("Value", style="bold white", justify="center")
    stats.add_row(
        "Total Entries", str(level1['total_entries']),
        "Unique Courses", str(level1['unique_courses']),
        "Credits Earned", f"[bold green]{level1['earned_credits']}[/bold green]",
    )
    stats.add_row(
        "Credits Attempted", str(level1['total_credits_attempted']),
        "Failed Credits", f"[red]{level1['failed_credits']}[/red]" if level1['failed_credits'] > 0 else "0",
        "Progress (130)", f"[bold cyan]{level1['progress_130']}%[/bold cyan]",
    )
    console.print(stats)

    # Progress bar
    prog = level1['progress_130']
    bar_len = 40
    filled = int(bar_len * min(prog, 100) / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    bar_color = "green" if prog >= 100 else "cyan" if prog >= 75 else "yellow"
    console.print(f"\n  [{bar_color}]{bar}[/{bar_color}]  [bold]{prog}%[/bold] of 130 credits\n")

    # Retakes
    if level1['retakes']:
        retake_table = Table(title=f"Retakes ({level1['retakes_count']})", box=box.ROUNDED, border_style="yellow")
        retake_table.add_column("Course", style="bold")
        retake_table.add_column("Attempts", justify="center")
        retake_table.add_column("Grade History", justify="center")
        retake_table.add_column("Best", justify="center", style="bold green")
        for r in level1['retakes']:
            history = " → ".join([f"[{grade_color(g)}]{g}[/{grade_color(g)}]" for g in r['grades']])
            retake_table.add_row(r['code'], str(r['attempts']), history, r['best'])
        console.print(retake_table)

    # Course table by semester
    console.print()
    for sem in data['semesters']:
        sem_table = Table(title=f"[bold]{sem['name']}[/bold]", box=box.SIMPLE_HEAVY, border_style="dim cyan", show_lines=False)
        sem_table.add_column("Course", style="bold white", width=12)
        sem_table.add_column("Credits", justify="center", width=8)
        sem_table.add_column("Grade", justify="center", width=8)
        sem_table.add_column("QP", justify="center", width=8)
        sem_table.add_column("Status", justify="center", width=10)
        for c in sem['courses']:
            g_style = grade_color(c['grade'])
            status_style = "green" if c['status'] == 'earned' else "red" if c['status'] == 'failed' else "dim"
            sem_table.add_row(
                c['code'], str(c['credits']),
                f"[{g_style}]{c['grade']}[/{g_style}]",
                str(c['quality_points']),
                f"[{status_style}]{c['status']}[/{status_style}]",
            )
        console.print(sem_table)


def show_level2(data):
    clear_screen()
    console.print(create_header())
    level2 = data['level2']

    console.print(Panel("[bold yellow]Level 2: CGPA & Waiver Analysis[/bold yellow]", border_style="yellow", box=box.HEAVY))

    cgpa_val = level2['cgpa']
    cgpa_color = "green" if cgpa_val >= 3.5 else "cyan" if cgpa_val >= 3.0 else "yellow" if cgpa_val >= 2.5 else "red"
    console.print(Panel(
        f"[bold {cgpa_color}]{cgpa_val:.2f}[/bold {cgpa_color}]\n\n"
        f"[dim]Cumulative GPA[/dim]\n"
        f"[bold]{level2['standing']} {level2['stars']}[/bold]",
        border_style=cgpa_color, box=box.DOUBLE, expand=False, width=30, padding=(1, 4),
    ), justify="center")

    stats = Table(box=box.ROUNDED, border_style="cyan", expand=True, show_header=False)
    stats.add_column(justify="center")
    stats.add_column(justify="center")
    stats.add_column(justify="center")
    stats.add_row(
        f"[dim]GPA Credits:[/dim] [bold]{level2['gpa_credits']}[/bold]",
        f"[dim]Quality Points:[/dim] [bold]{level2['total_quality_points']}[/bold]",
        f"[dim]Credits Earned:[/dim] [bold]{data['level1']['earned_credits']}[/bold]",
    )
    console.print(stats)

    # Waiver
    if level2['waiver']:
        w = level2['waiver']
        waiver_color = "yellow" if w['color'] == 'gold' else "white" if w['color'] == 'silver' else "bright_red"
        console.print(Panel(
            f"[bold {waiver_color}]🎉 {w['name']}[/bold {waiver_color}]\n"
            f"[bold]{w['level']} Tuition Waiver Eligible[/bold]",
            border_style=waiver_color, box=box.DOUBLE_EDGE, expand=False, width=45, padding=(1, 3),
        ), justify="center")
    else:
        console.print(Panel(
            "[dim]No tuition waiver eligible at current CGPA.\nNeed ≥ 3.50 CGPA with ≥ 30 earned credits.[/dim]",
            border_style="dim", box=box.ROUNDED, expand=False, width=50,
        ), justify="center")

    # CGPA verification warning
    if data.get('cgpa_warning'):
        w = data['cgpa_warning']
        console.print(Panel(
            f"[bold red]⚠ {w['message']}[/bold red]\n"
            f"PDF CGPA: {w['pdf_value']}  |  Calculated: {w['calculated_value']}  |  Δ {w['difference']}",
            border_style="red", box=box.HEAVY,
        ))

    # Grade distribution
    console.print()
    grade_table = Table(title="Grade Distribution", box=box.ROUNDED, border_style="cyan")
    grade_table.add_column("Grade", style="bold", justify="center")
    grade_table.add_column("Count", justify="center")
    grade_table.add_column("Bar", justify="left")
    max_count = max(level2['grade_distribution'].values()) if level2['grade_distribution'] else 1
    for g, count in sorted(level2['grade_distribution'].items(), key=lambda x: -x[1]):
        bar_len = int(count / max_count * 25)
        g_color = grade_color(g)
        bar = f"[{g_color}]{'█' * bar_len}[/{g_color}]"
        grade_table.add_row(f"[{g_color}]{g}[/{g_color}]", str(count), bar)
    console.print(grade_table)


def show_level3(data):
    clear_screen()
    console.print(create_header())
    level3 = data['level3']

    console.print(Panel("[bold magenta]Level 3: Degree Audit[/bold magenta]", border_style="magenta", box=box.HEAVY))

    if not level3:
        console.print(Panel("[dim]Program not detected.[/dim]", border_style="dim"))
        return

    console.print(f"\n  [bold cyan]{level3['program_name']}[/bold cyan]\n")

    prog = level3['mandatory_progress']
    bar_len = 40
    filled = int(bar_len * min(prog, 100) / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    prog_color = "green" if prog >= 100 else "cyan" if prog >= 75 else "yellow"
    console.print(f"  [{prog_color}]{bar}[/{prog_color}]  [bold]{prog}%[/bold]")
    console.print(f"  [dim]{level3['mandatory_completed']} of {level3['mandatory_total']} mandatory courses completed[/dim]\n")

    grad_status = "[bold green]✓ READY[/bold green]" if level3['graduation_ready'] else "[bold red]✗ NOT READY[/bold red]"
    stats = Table(box=box.ROUNDED, border_style="cyan", expand=True, show_header=False)
    stats.add_column(justify="center")
    stats.add_column(justify="center")
    stats.add_column(justify="center")
    stats.add_row(
        f"[dim]Mandatory:[/dim] [bold]{level3['mandatory_completed']}/{level3['mandatory_total']}[/bold]",
        f"[dim]Progress:[/dim] [bold]{level3['mandatory_progress']}%[/bold]",
        f"[dim]Graduation:[/dim] {grad_status}",
    )
    console.print(stats)

    if level3['mandatory_missing']:
        console.print()
        missing_table = Table(title=f"Missing Mandatory ({len(level3['mandatory_missing'])})", box=box.ROUNDED, border_style="red")
        missing_table.add_column("#", style="dim", width=4)
        missing_table.add_column("Course Code", style="bold red")
        for i, code in enumerate(level3['mandatory_missing'], 1):
            missing_table.add_row(str(i), code)
        console.print(missing_table)
    else:
        console.print(Panel("[bold green]✓ All mandatory courses completed![/bold green]", border_style="green", box=box.ROUNDED))

    if level3.get('elective_status'):
        console.print()
        for group_name, group in level3['elective_status'].items():
            status = "[green]✓[/green]" if group['satisfied'] else "[red]✗[/red]"
            courses_str = ', '.join(group['courses']) if group['courses'] else 'none'
            console.print(f"  {status} [bold]{group_name}[/bold]: {group['completed']}/{group['required']} [dim]({courses_str})[/dim]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN APPLICATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def show_results_menu():
    menu = Table(show_header=False, box=box.ROUNDED, border_style="cyan", padding=(0, 2), expand=True)
    menu.add_column("Option", style="bold white", justify="center")
    menu.add_column("Description", style="dim white")
    menu.add_row("[bold cyan]1[/bold cyan]  [green]Credit Tally[/green]", "Level 1 — Credits, retakes, progress")
    menu.add_row("[bold cyan]2[/bold cyan]  [yellow]CGPA Analysis[/yellow]", "Level 2 — CGPA, standing, waiver")
    menu.add_row("[bold cyan]3[/bold cyan]  [magenta]Degree Audit[/magenta]", "Level 3 — Graduation eligibility")
    menu.add_row("", "")
    menu.add_row("[bold cyan]N[/bold cyan]  [blue]New Scan[/blue]", "Scan a different transcript")
    menu.add_row("[bold cyan]Q[/bold cyan]  [red]Quit[/red]", "Exit the application")
    return Panel(menu, title="[bold bright_cyan]  Analysis Results  [/bold bright_cyan]",
                 border_style="cyan", box=box.DOUBLE_EDGE, padding=(1, 2))


def get_file_path():
    console.print()
    console.print("[cyan]Supported formats:[/cyan] PDF, PNG, JPG, JPEG")
    console.print()

    default_pdf = PROJECT_ROOT / "Transcript PDF.pdf"
    pdfs = list(PROJECT_ROOT.glob("*.pdf")) + list(PROJECT_ROOT.glob("*.png")) + list(PROJECT_ROOT.glob("*.jpg"))

    if pdfs:
        file_table = Table(title="Available Files", box=box.ROUNDED, border_style="cyan")
        file_table.add_column("#", style="bold cyan", width=3)
        file_table.add_column("File", style="white")
        file_table.add_column("Size", style="dim", justify="right")
        for i, f in enumerate(pdfs[:10], 1):
            size_kb = f.stat().st_size / 1024
            size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            file_table.add_row(str(i), f.name, size_str)
        console.print(file_table)
        console.print()

    path = Prompt.ask("[cyan]Enter file path or number[/cyan]",
                      default="Transcript PDF.pdf" if default_pdf.exists() else "")

    if path.isdigit() and pdfs:
        idx = int(path) - 1
        if 0 <= idx < len(pdfs):
            return str(pdfs[idx])

    full_path = Path(path)
    if not full_path.is_absolute():
        full_path = PROJECT_ROOT / path
    return str(full_path)


def main():
    # Handle --cloud flag (remove it from argv for file path processing)
    args = [arg for arg in sys.argv[1:] if arg != '--cloud']
    
    # Direct mode: python cli_app/main.py <file.pdf>
    if len(args) > 0:
        file_path = args[0]
        if not Path(file_path).is_absolute():
            file_path = str(PROJECT_ROOT / file_path)
        clear_screen()
        console.print(create_header())
        
        # Use cloud API or local OCR based on configuration
        if USE_CLOUD_API:
            console.print(f"\n[dim cyan]Mode: Cloud API ({CLOUD_API_URL})[/dim cyan]")
            result, error = scan_transcript_cloud(file_path)
        else:
            console.print(f"\n[dim cyan]Mode: Local OCR[/dim cyan]")
            result, error = scan_transcript(file_path)
            
        if error:
            console.print(f"\n[red]Error: {error}[/red]")
            return
        show_ocr_summary(result['ocr_info'], len(result['courses']))
        console.print()
        Prompt.ask("[dim]Press Enter to view Level 1[/dim]")
        show_level1(result)
        console.print()
        Prompt.ask("[dim]Press Enter to view Level 2[/dim]")
        show_level2(result)
        console.print()
        Prompt.ask("[dim]Press Enter to view Level 3[/dim]")
        show_level3(result)
        console.print()
        Prompt.ask("[dim]Press Enter to exit[/dim]")
        return

    # Interactive mode
    while True:
        clear_screen()
        console.print(create_header())
        
        # Show mode indicator
        if USE_CLOUD_API:
            console.print(f"\n[bold cyan]☁️  Cloud Mode[/bold cyan] [dim]({CLOUD_API_URL})[/dim]")
        else:
            console.print(f"\n[bold cyan]💻 Local Mode[/bold cyan] [dim](Use --cloud for cloud API)[/dim]")
        
        console.print()
        file_path = get_file_path()

        if not Path(file_path).exists():
            console.print(f"\n[red]File not found: {file_path}[/red]")
            console.print()
            if Confirm.ask("[cyan]Try again?[/cyan]", default=True):
                continue
            break

        # Use cloud API or local OCR based on configuration
        if USE_CLOUD_API:
            result, error = scan_transcript_cloud(file_path)
        else:
            result, error = scan_transcript(file_path)
            
        if error:
            console.print(f"\n[red]Error: {error}[/red]")
            console.print()
            if Confirm.ask("[cyan]Try again with a different file?[/cyan]", default=True):
                continue
            break

        console.print()
        show_ocr_summary(result['ocr_info'], len(result['courses']))

        # Results navigation loop
        while True:
            console.print()
            console.print(show_results_menu())
            console.print()
            choice = Prompt.ask("[bold cyan]Select option[/bold cyan]",
                                choices=["1", "2", "3", "n", "N", "q", "Q"], default="1").upper()

            if choice == "1":
                show_level1(result)
                console.print()
                Prompt.ask("[dim]Press Enter to go back[/dim]")
            elif choice == "2":
                show_level2(result)
                console.print()
                Prompt.ask("[dim]Press Enter to go back[/dim]")
            elif choice == "3":
                show_level3(result)
                console.print()
                Prompt.ask("[dim]Press Enter to go back[/dim]")
            elif choice == "N":
                break
            elif choice == "Q":
                clear_screen()
                console.print(Panel(
                    "[bold cyan]Thank you for using NSU Degree Audit Engine![/bold cyan]\n\n"
                    "[dim]North South University | Premium CLI v3.0 | OCR Powered[/dim]",
                    border_style="cyan", box=box.DOUBLE_EDGE,
                ))
                console.print()
                return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
