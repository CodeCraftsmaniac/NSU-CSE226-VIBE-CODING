#!/usr/bin/env python3
"""
main.py — NSU Degree Audit Engine (Premium Edition)
════════════════════════════════════════════════════
Beautiful terminal UI with interactive menus, animations,
and professional design using the Rich library.

Usage:
  python main.py                    # Interactive mode
  python main.py <transcript.csv>   # Direct audit mode

Author: NSU CSE226 Vibe Coding Project
Version: 2.0 Premium
"""

import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.spinner import Spinner
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.style import Style
from rich.box import DOUBLE_EDGE, ROUNDED, HEAVY
from rich import box

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Initialize console with force_terminal for proper color support
console = Console(force_terminal=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  THEME CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Theme:
    """Premium color theme."""
    PRIMARY = "cyan"
    SECONDARY = "magenta"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    MUTED = "dim white"
    ACCENT = "bright_cyan"
    GOLD = "yellow"

    # Gradient colors for headers
    GRADIENT = ["#00d4aa", "#00b4d8", "#0096c7", "#0077b6", "#023e8a"]


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def create_header():
    """Create the premium header banner."""
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
        subtitle="[dim cyan]North South University | Premium Terminal Edition v2.0[/dim cyan]",
        border_style="bright_cyan",
        box=box.DOUBLE,
        padding=(0, 1),
    )


def show_loading_animation(message: str = "Loading", duration: float = 1.5):
    """Show a premium loading animation."""
    with Progress(
        SpinnerColumn("dots12", style="cyan"),
        TextColumn("[cyan]{task.description}[/cyan]"),
        BarColumn(bar_width=30, style="cyan", complete_style="bright_cyan"),
        transient=True,
    ) as progress:
        task = progress.add_task(message, total=100)
        for i in range(100):
            time.sleep(duration / 100)
            progress.update(task, advance=1)


def create_menu():
    """Create the interactive main menu."""
    menu = Table(
        show_header=False,
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 2),
        expand=True,
    )

    menu.add_column("Option", style="bold white", justify="center")
    menu.add_column("Description", style="dim white")

    menu.add_row(
        "[bold cyan]1[/bold cyan]  [green]Credit Tally[/green]",
        "Level 1 - Count credits by category"
    )
    menu.add_row(
        "[bold cyan]2[/bold cyan]  [yellow]CGPA Analyzer[/yellow]",
        "Level 2 - Calculate CGPA and check waivers"
    )
    menu.add_row(
        "[bold cyan]3[/bold cyan]  [magenta]Degree Audit[/magenta]",
        "Level 3 - Full graduation eligibility check"
    )
    menu.add_row("", "")
    menu.add_row(
        "[bold cyan]4[/bold cyan]  [blue]OCR Extract[/blue]",
        "Extract transcript from PDF/Image"
    )
    menu.add_row("", "")
    menu.add_row(
        "[bold cyan]S[/bold cyan]  [dim]Settings[/dim]",
        "Configure program and department"
    )
    menu.add_row(
        "[bold cyan]Q[/bold cyan]  [red]Quit[/red]",
        "Exit the application"
    )

    return Panel(
        menu,
        title="[bold bright_cyan]  Main Menu  [/bold bright_cyan]",
        border_style="cyan",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )


def create_status_bar(program: str, transcript: str):
    """Create the bottom status bar."""
    status = Table.grid(expand=True)
    status.add_column(justify="left")
    status.add_column(justify="center")
    status.add_column(justify="right")

    status.add_row(
        f"[dim]Program:[/dim] [bold cyan]{program}[/bold cyan]",
        f"[dim]Transcript:[/dim] [bold green]{transcript or 'Not loaded'}[/bold green]",
        f"[dim]v2.0 Premium[/dim]"
    )

    return Panel(status, border_style="dim cyan", box=box.ROUNDED)


def show_file_picker(title: str = "Select File", file_type: str = "csv"):
    """Show file selection prompt."""
    console.print()

    # Show current directory files
    cwd = Path(".")
    files = list(cwd.glob(f"**/*.{file_type}"))[:10]

    if files:
        table = Table(title=f"Available {file_type.upper()} Files", box=box.ROUNDED, border_style="cyan")
        table.add_column("#", style="bold cyan", width=3)
        table.add_column("File Path", style="white")

        for i, f in enumerate(files, 1):
            table.add_row(str(i), str(f))

        console.print(table)
        console.print()

    path = Prompt.ask(
        f"[cyan]Enter file path or number[/cyan]",
        default="data/cse/transcript.csv"
    )

    # Check if number was entered
    if path.isdigit() and files:
        idx = int(path) - 1
        if 0 <= idx < len(files):
            return str(files[idx])

    return path


def show_program_selector():
    """Show program selection menu."""
    console.print()

    table = Table(box=box.ROUNDED, border_style="cyan", title="Select Program")
    table.add_column("Option", style="bold cyan", justify="center", width=8)
    table.add_column("Program", style="white")
    table.add_column("Department", style="dim white")

    table.add_row("[1]", "Computer Science & Engineering (CSE)", "ECE, SEPS")
    table.add_row("[2]", "Bachelor of Laws (LLB)", "Law")

    console.print(table)
    console.print()

    choice = Prompt.ask("[cyan]Select program[/cyan]", choices=["1", "2"], default="1")
    return "CSE" if choice == "1" else "LLB"


def run_level1(transcript_path: str):
    """Run Level 1 - Credit Tally."""
    clear_screen()
    console.print(Panel("[bold cyan]Level 1: Credit Tally Engine[/bold cyan]", border_style="cyan"))
    show_loading_animation("Loading transcript", 1.0)

    # Import and run
    from src.credit_engine import main as credit_main
    sys.argv = ["credit_engine.py", transcript_path]

    try:
        credit_main()
    except SystemExit:
        pass

    console.print()
    Prompt.ask("[dim]Press Enter to continue[/dim]")


def run_level2(transcript_path: str):
    """Run Level 2 - CGPA Analyzer."""
    clear_screen()
    console.print(Panel("[bold yellow]Level 2: CGPA & Waiver Analyzer[/bold yellow]", border_style="yellow"))
    show_loading_animation("Analyzing transcript", 1.0)

    from src.cgpa_analyzer import main as cgpa_main
    sys.argv = ["cgpa_analyzer.py", transcript_path]

    try:
        cgpa_main()
    except SystemExit:
        pass

    console.print()
    Prompt.ask("[dim]Press Enter to continue[/dim]")


def run_level3(transcript_path: str, program: str):
    """Run Level 3 - Degree Audit."""
    clear_screen()
    console.print(Panel("[bold magenta]Level 3: Degree Audit Engine[/bold magenta]", border_style="magenta"))
    show_loading_animation("Running degree audit", 1.0)

    from src.degree_audit import main as audit_main

    # Find knowledge base
    kb_path = Path(__file__).parent / "knowledge_base.md"
    if not kb_path.exists():
        kb_path = Path("knowledge_base.md")

    sys.argv = ["degree_audit.py", transcript_path, program, str(kb_path)]

    try:
        audit_main()
    except SystemExit:
        pass

    console.print()
    Prompt.ask("[dim]Press Enter to continue[/dim]")


def run_ocr():
    """Run OCR extraction."""
    clear_screen()
    console.print(Panel("[bold blue]OCR Transcript Extractor[/bold blue]", border_style="blue"))
    console.print()

    # File picker for PDF/image
    console.print("[cyan]Supported formats:[/cyan] PDF, PNG, JPG, JPEG, BMP, TIFF")
    console.print()

    file_path = Prompt.ask(
        "[cyan]Enter path to transcript PDF or image[/cyan]",
        default="Transcript PDF.pdf"
    )

    if not Path(file_path).exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        Prompt.ask("[dim]Press Enter to continue[/dim]")
        return

    show_loading_animation("Running OCR extraction (this may take a minute)", 2.0)

    from src.ocr_engine import TranscriptOCR

    ocr = TranscriptOCR()

    with console.status("[cyan]Processing with PaddleOCR...[/cyan]", spinner="dots"):
        result = ocr.extract(file_path)

    if result.success:
        console.print()
        console.print(Panel(
            f"[green]Extraction successful![/green]\n\n"
            f"[dim]Courses found:[/dim] [bold]{result.course_count}[/bold]\n"
            f"[dim]Student:[/dim] [bold]{result.student_name or 'N/A'}[/bold]\n"
            f"[dim]ID:[/dim] [bold]{result.student_id or 'N/A'}[/bold]\n"
            f"[dim]CGPA:[/dim] [bold]{result.cgpa or 'N/A'}[/bold]",
            title="OCR Result",
            border_style="green"
        ))

        if result.courses:
            # Show courses table
            table = Table(title="Extracted Courses", box=box.ROUNDED, border_style="cyan")
            table.add_column("Course", style="bold")
            table.add_column("Credits", justify="center")
            table.add_column("Grade", justify="center")
            table.add_column("Semester", style="dim")

            for course in result.courses[:20]:  # Show first 20
                table.add_row(
                    course.course_code,
                    str(course.credits),
                    course.grade,
                    course.semester
                )

            if result.course_count > 20:
                table.add_row("...", "...", "...", f"({result.course_count - 20} more)")

            console.print(table)

        # Option to save
        if Confirm.ask("\n[cyan]Save to CSV file?[/cyan]", default=True):
            output_path = Prompt.ask(
                "[cyan]Output path[/cyan]",
                default="data/extracted_transcript.csv"
            )
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(result.csv_data)
            console.print(f"[green]Saved to {output_path}[/green]")
    else:
        console.print(f"[red]Extraction failed: {result.error}[/red]")

    console.print()
    Prompt.ask("[dim]Press Enter to continue[/dim]")


def show_settings(current_program: str, current_transcript: str):
    """Show settings menu."""
    clear_screen()
    console.print(Panel("[bold]Settings[/bold]", border_style="cyan"))

    table = Table(box=box.ROUNDED, border_style="dim cyan")
    table.add_column("Setting", style="cyan")
    table.add_column("Current Value", style="white")

    table.add_row("Program", current_program)
    table.add_row("Transcript", current_transcript or "Not loaded")

    console.print(table)
    console.print()

    new_program = current_program
    new_transcript = current_transcript

    if Confirm.ask("[cyan]Change program?[/cyan]", default=False):
        new_program = show_program_selector()

    if Confirm.ask("[cyan]Change transcript?[/cyan]", default=False):
        new_transcript = show_file_picker("Select Transcript", "csv")

    return new_program, new_transcript


def main():
    """Main application entry point."""
    # Default settings
    current_program = "CSE"
    current_transcript = "data/cse/transcript.csv"

    # Check for command line arguments
    if len(sys.argv) > 1:
        # Direct mode - run Level 3 with provided transcript
        transcript_path = sys.argv[1]
        program = sys.argv[2] if len(sys.argv) > 2 else "CSE"

        clear_screen()
        console.print(create_header())
        run_level3(transcript_path, program)
        return

    # Interactive mode
    while True:
        clear_screen()

        # Header
        console.print(create_header())
        console.print()

        # Menu
        console.print(create_menu())
        console.print()

        # Status bar
        console.print(create_status_bar(current_program, current_transcript))
        console.print()

        # Get user choice
        choice = Prompt.ask(
            "[bold cyan]Select option[/bold cyan]",
            choices=["1", "2", "3", "4", "s", "S", "q", "Q"],
            default="3"
        ).upper()

        if choice == "1":
            if not current_transcript:
                current_transcript = show_file_picker()
            run_level1(current_transcript)

        elif choice == "2":
            if not current_transcript:
                current_transcript = show_file_picker()
            run_level2(current_transcript)

        elif choice == "3":
            if not current_transcript:
                current_transcript = show_file_picker()
            run_level3(current_transcript, current_program)

        elif choice == "4":
            run_ocr()

        elif choice == "S":
            current_program, current_transcript = show_settings(
                current_program, current_transcript
            )

        elif choice == "Q":
            clear_screen()
            console.print(Panel(
                "[bold cyan]Thank you for using NSU Degree Audit Engine![/bold cyan]\n\n"
                "[dim]North South University - Premium Terminal Edition v2.0[/dim]",
                border_style="cyan",
                box=box.DOUBLE_EDGE
            ))
            console.print()
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
