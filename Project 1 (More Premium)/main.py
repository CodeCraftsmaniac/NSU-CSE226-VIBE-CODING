"""
main.py  —  NSU Degree Audit Engine · Interactive Launcher  v2.0
═══════════════════════════════════════════════════════════════════
Premium single-file TUI launcher.  Select program, analysis level,
and data file through interactive menus with neo-dark styling.
Replaces all batch scripts with one elegant entry point.

Usage:  python main.py
"""

import os, sys, subprocess, glob
from datetime import datetime

# ─── Enable Virtual Terminal Processing (Windows) ──────────────────────────
os.system("")

# ─── Resolve paths ─────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from core import C, Box, _gradient_text, _gradient_line

# ═══════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

WIDTH = 78

PROGRAMS = {
    "1": {"key": "CSE",  "name": "Computer Science & Engineering", "credits": 130},
    "2": {"key": "ARCH", "name": "Architecture",                   "credits": 170},
}

LEVELS = {
    "1": {"script": "level1_credit_tally.py",  "name": "Credit Tally Engine",             "icon": "📊"},
    "2": {"script": "level2_cgpa_analyzer.py", "name": "CGPA & Waiver Handler",            "icon": "📈"},
    "3": {"script": "level3_degree_audit.py",  "name": "Degree Audit & Deficiency Reporter","icon": "🎓"},
}

FILE_LABELS = {
    "transcript.csv":          "Main student transcript",
}


# ═══════════════════════════════════════════════════════════════════════════
#  UI HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def clear():
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def _pad(text, visible_len, total):
    """Return text + spaces so the *visible* width reaches total."""
    return text + " " * max(0, total - visible_len)


# ── Splash ────────────────────────────────────────────────────────────────

def splash():
    """Render the premium hero splash screen (compact variant)."""
    inner = WIDTH - 4
    top = _gradient_line("━", WIDTH, 0, 220, 200, 100, 120, 255)
    bot = _gradient_line("━", WIDTH, 100, 120, 255, 0, 220, 200)
    deco = _gradient_line("─", inner - 6, 60, 60, 90, 40, 40, 65)
    mid = _gradient_line("─", WIDTH, 50, 50, 80, 35, 35, 55)

    lv = f"{C.AQUA}{Box.VH}{C.RST}"
    rv = f"{C.SAPPHIRE}{Box.VH}{C.RST}"
    bg = C.BG_CARD
    rs = C.RST

    blank = f"{lv}{bg}{' ' * inner}{rs}{rv}"

    # Title
    title = "NSU DEGREE AUDIT ENGINE"
    spaced = "  ".join(title)
    display_len = len(spaced)
    title_grad = _gradient_text(spaced, 80, 240, 255, 200, 140, 255)
    t_pad = (inner - display_len) // 2
    title_line = f"{lv}{bg}{' ' * t_pad}{C.BOLD}{title_grad}{rs}{bg}{' ' * (inner - t_pad - display_len)}{rs}{rv}"

    # Subtitle
    subtitle = "Interactive Launcher  ·  v2.0"
    s_pad = (inner - len(subtitle)) // 2
    sub_line = f"{lv}{bg}{' ' * s_pad}{C.SILVER}{C.ITAL}{subtitle}{rs}{bg}{' ' * (inner - s_pad - len(subtitle))}{rs}{rv}"

    # Decorators
    deco_full = f"{lv}{bg}   {C.GOLD}✦{rs}{bg}  {deco}  {C.GOLD}✦{rs}{bg}   {rs}{rv}"

    # Timestamp bar
    ts = datetime.now().strftime("%b %d, %Y  %H:%M")
    bar = f"◈ NSU Degree Audit Engine v2.0  ·  {ts}"
    b_pad = (inner - len(bar)) // 2
    bar_line = f"{lv}{C.BG_ACCENT}{' ' * b_pad}{C.SLATE}{bar}{rs}{C.BG_ACCENT}{' ' * (inner - b_pad - len(bar))}{rs}{rv}"

    print()
    print(f"  {top}")
    print(f"  {blank}")
    print(f"  {deco_full}")
    print(f"  {blank}")
    print(f"  {title_line}")
    print(f"  {sub_line}")
    print(f"  {blank}")
    print(f"  {deco_full}")
    print(f"  {blank}")
    print(f"  {mid}")
    print(f"  {bar_line}")
    print(f"  {bot}")
    print()


# ── Menu Components ───────────────────────────────────────────────────────

def menu_section(title, icon=""):
    """Print a gradient section header for a menu."""
    prefix = f"{icon}  " if icon else ""
    display = f"{prefix}{title}"
    top = _gradient_line("═", WIDTH, 0, 180, 160, 80, 100, 220)
    bot = _gradient_line("─", WIDTH, 50, 50, 80, 30, 30, 50)
    grad = _gradient_text(display, 100, 230, 255, 200, 150, 255)
    print(f"  {top}")
    print(f"  {C.BG_HEADER}  {C.BOLD}{grad}{C.RST}{C.BG_HEADER}{' ' * max(0, WIDTH - len(display) - 4)}  {C.RST}")
    print(f"  {bot}")


def menu_option(key, label, detail=""):
    """Print a single menu choice line."""
    key_pill = f"{C.BG_ACCENT}{C.NEON_CYAN}{C.BOLD} {key} {C.RST}"
    det_str  = f"  {C.SLATE}{C.ITAL}— {detail}{C.RST}" if detail else ""
    print(f"    {key_pill}  {C.FROST}{C.BOLD}{label}{C.RST}{det_str}")


def menu_back(label="Exit"):
    """Print the exit/back option in muted style."""
    print()
    key_pill = f"{C.BG_ACCENT}{C.SLATE}{C.BOLD} 0 {C.RST}"
    print(f"    {key_pill}  {C.SLATE}{label}{C.RST}")


def prompt():
    """Display the input prompt and return stripped input."""
    try:
        return input(f"\n  {C.NEON_CYAN}▸{C.RST} {C.SILVER}Enter choice:{C.RST} ").strip()
    except (EOFError, KeyboardInterrupt):
        return "0"


def farewell():
    """Print a styled goodbye message."""
    msg = _gradient_text("  Thank you for using NSU Degree Audit Engine  ", 80, 240, 255, 200, 140, 255)
    border = _gradient_line("━", WIDTH, 0, 220, 200, 100, 120, 255)
    print()
    print(f"  {border}")
    print(f"  {C.BG_CARD}  {msg}{C.RST}{C.BG_CARD}{'':>2}{C.RST}")
    print(f"  {border}")
    print()


def launch_banner(prog, level_info, data_path):
    """Print a compact launch confirmation card."""
    border = _gradient_line("═", WIDTH, 0, 180, 160, 80, 100, 220)
    bot    = _gradient_line("─", WIDTH, 50, 50, 80, 30, 30, 50)
    grad   = _gradient_text("🚀  Launching Analysis", 100, 255, 200, 200, 255, 100)

    print(f"  {border}")
    print(f"  {C.BG_HEADER}  {C.BOLD}{grad}{C.RST}{C.BG_HEADER}{' ' * max(0, WIDTH - 24)}  {C.RST}")
    print(f"  {bot}")

    dot = f"{C.SLATE}{'·' * 22}{C.RST}"
    print(f"  {C.SILVER}  Program    {dot} {C.FROST}{C.BOLD}{prog['key']}  — {prog['name']}{C.RST}")
    print(f"  {C.SILVER}  Level      {dot} {C.ELECTRIC}{C.BOLD}{level_info['icon']}  {level_info['name']}{C.RST}")
    print(f"  {C.SILVER}  Data File  {dot} {C.AQUA}{os.path.relpath(data_path, ROOT)}{C.RST}")
    print()
    sep = _gradient_line("─", WIDTH, 50, 50, 80, 30, 30, 50)
    print(f"  {sep}")
    print()


# ═══════════════════════════════════════════════════════════════════════════
#  DATA DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════

def discover_files(program_key):
    """Return list of (display_name, full_path, description) for available CSVs."""
    data_dir = os.path.join(ROOT, "data", program_key.lower())
    if not os.path.isdir(data_dir):
        return []

    # Primary CSV files in data/{program}/
    csvs = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    result = []
    for fp in csvs:
        name = os.path.basename(fp)
        desc = FILE_LABELS.get(name, "")
        result.append((name, fp, desc))

    # Auto-generated test files in data/{program}/tests/
    tests_dir = os.path.join(data_dir, "tests")
    if os.path.isdir(tests_dir):
        gen_csvs = sorted(glob.glob(os.path.join(tests_dir, "*.csv")))
        if gen_csvs:
            for fp in gen_csvs:
                name = f"tests/{os.path.basename(fp)}"
                result.append((name, fp, "Auto-generated scenario"))

    return result


# ═══════════════════════════════════════════════════════════════════════════
#  COMMAND BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def build_command(level_key, data_file_path, program_key, credits):
    """Build the subprocess command list for the selected level."""
    script = os.path.join(SRC, LEVELS[level_key]["script"])
    if level_key == "1":
        return [sys.executable, script, data_file_path, str(credits)]
    elif level_key == "2":
        return [sys.executable, script, data_file_path]
    elif level_key == "3":
        kb = os.path.join(ROOT, "knowledge_base.md")
        return [sys.executable, script, data_file_path, program_key, kb]
    return []


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════

def main():
    while True:
        # ── Step 1: Program Selection ──────────────────────────────────
        clear()
        splash()
        menu_section("Select Program", "📌")
        print()
        for k, p in PROGRAMS.items():
            menu_option(k, f"{p['key']:5s}", f"{p['name']}  ({p['credits']} credits)")
        menu_back("Exit")

        prog_choice = prompt()
        if prog_choice == "0":
            farewell()
            break
        if prog_choice not in PROGRAMS:
            continue
        prog = PROGRAMS[prog_choice]

        # ── Step 2: Level Selection ────────────────────────────────────
        clear()
        splash()
        menu_section(f"Select Analysis Level  ·  {prog['key']}", "📊")
        print()
        for k, lv in LEVELS.items():
            menu_option(k, f"Level {k}", f"{lv['icon']}  {lv['name']}")
        menu_back("Back")

        lvl_choice = prompt()
        if lvl_choice == "0":
            continue
        if lvl_choice not in LEVELS:
            continue
        level_info = LEVELS[lvl_choice]

        # ── Step 3: Data File Selection ────────────────────────────────
        clear()
        splash()
        files = discover_files(prog["key"])
        if not files:
            menu_section(f"No Data Files Found  ·  data/{prog['key'].lower()}/", "⚠️")
            print(f"\n    {C.ROSE}No CSV files found in data/{prog['key'].lower()}/{C.RST}")
            print(f"    {C.SLATE}Run  python generate_tests.py  to create test data.{C.RST}")
            input(f"\n  {C.SLATE}Press Enter to go back...{C.RST}")
            continue

        menu_section(f"Select Data File  ·  {prog['key']}  ·  Level {lvl_choice}", "📂")
        print()
        for i, (name, _path, desc) in enumerate(files, 1):
            menu_option(str(i), name, desc)
        menu_back("Back")

        file_choice = prompt()
        if file_choice == "0":
            continue
        try:
            idx = int(file_choice) - 1
            if idx < 0 or idx >= len(files):
                continue
        except ValueError:
            continue

        _fname, data_path, _desc = files[idx]

        # ── Step 4: Launch ─────────────────────────────────────────────
        clear()
        launch_banner(prog, level_info, data_path)

        cmd = build_command(lvl_choice, data_path, prog["key"], prog["credits"])
        subprocess.run(cmd, cwd=ROOT)

        # ── After analysis: return to menu ─────────────────────────────
        print()
        sep = _gradient_line("━", WIDTH, 0, 220, 200, 100, 120, 255)
        print(f"  {sep}")
        print(f"  {C.BG_CARD}  {C.SILVER}Analysis complete.{C.RST}{C.BG_CARD}{' ' * (WIDTH - 22)}{C.RST}")
        print(f"  {sep}")
        input(f"\n  {C.SLATE}Press Enter to return to menu …{C.RST} ")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.SLATE}Interrupted. Goodbye.{C.RST}\n")
