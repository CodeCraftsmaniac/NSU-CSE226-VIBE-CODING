"""
core.py  —  NSU Degree Audit Engine · Shared Core Module
═════════════════════════════════════════════════════════
Premium terminal UI system with gradient rendering, card layouts,
data tables, grade mapping, transcript parsing, and knowledge-base
parsing.  Imported by all three level scripts.

Author:  CSE226 Project 1
"""

import csv, os, re, sys
from collections import OrderedDict
from datetime import datetime

# ─── Force UTF-8 encoding (Windows fix) ────────────────────────────────────────
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ─── Enable Virtual Terminal Processing (Windows) ─────────────────────────────
os.system("")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ANSI  ·  256-Color & True-Color Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _fg(r, g, b):
    """True-color (24-bit) foreground."""
    return f"\033[38;2;{r};{g};{b}m"

def _bg(r, g, b):
    """True-color (24-bit) background."""
    return f"\033[48;2;{r};{g};{b}m"

class C:
    """ANSI escape codes — basic + 256-color palette."""
    RST   = "\033[0m"
    BOLD  = "\033[1m"
    DIM   = "\033[2m"
    ITAL  = "\033[3m"
    ULINE = "\033[4m"
    BLINK = "\033[5m"
    STRIKE = "\033[9m"

    # ── Core palette ──────────────────────────────────────
    BLACK   = "\033[30m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"

    # ── Premium accent colours (true-color) ───────────────
    TEAL      = _fg(0, 200, 180)
    CORAL     = _fg(255, 127, 80)
    LAVENDER  = _fg(180, 160, 255)
    MINT      = _fg(100, 255, 180)
    GOLD      = _fg(255, 215, 0)
    ROSE      = _fg(255, 100, 130)
    SKY       = _fg(135, 206, 250)
    PEACH     = _fg(255, 180, 130)
    LIME      = _fg(180, 255, 100)
    VIOLET    = _fg(160, 100, 255)

    # ── Background accents ────────────────────────────────
    BG_DARK     = _bg(20, 20, 30)
    BG_CARD     = _bg(30, 30, 45)
    BG_ACCENT   = _bg(40, 40, 60)
    BG_SUCCESS  = _bg(20, 60, 30)
    BG_DANGER   = _bg(70, 20, 20)
    BG_WARN     = _bg(70, 55, 10)
    BG_INFO     = _bg(15, 40, 65)

    BG_RED    = "\033[101m"
    BG_GREEN  = "\033[102m"
    BG_YELLOW = "\033[103m"
    BG_BLUE   = "\033[104m"
    BG_CYAN   = "\033[106m"
    BG_WHITE  = "\033[107m"
    BG_GRAY   = "\033[100m"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BOX-DRAWING  ·  Unicode Characters
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Box:
    # Double line
    TL = "╔"; TR = "╗"; BL = "╚"; BR = "╝"; H = "═"; V = "║"
    # Single line
    TL2 = "┌"; TR2 = "┐"; BL2 = "└"; BR2 = "┘"; H2 = "─"; V2 = "│"
    # Connectors
    CROSS = "┼"; T_DOWN = "┬"; T_UP = "┴"; T_LEFT = "┤"; T_RIGHT = "├"
    # Heavy
    HH = "━"; VH = "┃"
    TLH = "┏"; TRH = "┓"; BLH = "┗"; BRH = "┛"
    # Rounded
    TLR = "╭"; TRR = "╮"; BLR = "╰"; BRR = "╯"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GRADE-POINT MAPPING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GRADE_POINTS = {
    "A": 4.00, "A-": 3.70,
    "B+": 3.30, "B": 3.00, "B-": 2.70,
    "C+": 2.30, "C": 2.00, "C-": 1.70,
    "D+": 1.30, "D": 1.00,
    "F": 0.00,
}

PASSING_GRADES = {"A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "P", "TR"}
NON_GPA_GRADES = {"W", "I", "P", "TR"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PREMIUM UI  ·  Gradient & Visual Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _gradient_text(text, r1, g1, b1, r2, g2, b2):
    """Render text with a smooth left-to-right colour gradient."""
    n = max(len(text) - 1, 1)
    out = []
    for i, ch in enumerate(text):
        r = int(r1 + (r2 - r1) * i / n)
        g = int(g1 + (g2 - g1) * i / n)
        b = int(b1 + (b2 - b1) * i / n)
        out.append(f"\033[38;2;{r};{g};{b}m{ch}")
    out.append(C.RST)
    return "".join(out)

def _gradient_line(char, width, r1, g1, b1, r2, g2, b2):
    """Render a line of repeated chars with gradient colour."""
    return _gradient_text(char * width, r1, g1, b1, r2, g2, b2)


# ── Hero Banner ───────────────────────────────────────────────────────────────

def banner(title, subtitle="", width=76):
    """Print a premium gradient hero banner with optional subtitle."""
    # Gradient border: teal → cyan → blue
    top_border = _gradient_line("━", width, 0, 200, 180, 80, 140, 255)
    bot_border = _gradient_line("━", width, 80, 140, 255, 0, 200, 180)

    # Sides
    lv = f"{C.TEAL}{Box.VH}{C.RST}"
    rv = f"{C.VIOLET}{Box.VH}{C.RST}"

    # Title with gradient
    title_grad = _gradient_text(title, 100, 220, 255, 200, 160, 255)
    title_pad = (width - 2 - len(title)) // 2
    title_line = f"{lv}{' ' * title_pad}{C.BOLD}{title_grad}{C.RST}{' ' * (width - 2 - title_pad - len(title))}{rv}"

    # Subtitle
    if subtitle:
        sub_pad = (width - 2 - len(subtitle)) // 2
        sub_line = f"{lv}{' ' * sub_pad}{C.GRAY}{C.ITAL}{subtitle}{C.RST}{' ' * (width - 2 - sub_pad - len(subtitle))}{rv}"
    else:
        sub_line = None

    # Blank
    blank = f"{lv}{' ' * (width - 2)}{rv}"

    print()
    print(f"  {top_border}")
    print(f"  {blank}")
    print(f"  {title_line}")
    if sub_line:
        print(f"  {sub_line}")
    print(f"  {blank}")
    print(f"  {bot_border}")


# ── Section Header (Card-style) ──────────────────────────────────────────────

def section(title, icon="", width=76):
    """Print a card-style section header with icon."""
    prefix = f"{icon}  " if icon else ""
    display = f"{prefix}{title}"
    line = _gradient_line("─", width, 60, 60, 80, 40, 40, 60)
    title_grad = _gradient_text(display, 130, 200, 255, 180, 140, 255)
    print(f"\n  {line}")
    print(f"  {C.BOLD}{title_grad}{C.RST}")
    print(f"  {line}")


# ── Info Rows ─────────────────────────────────────────────────────────────────

def info_line(label, value, label_w=30):
    """Print a styled key-value pair with dim label and bright value."""
    dot_fill = "·" * max(1, label_w - len(label))
    print(f"  {C.GRAY}  {label} {dot_fill}{C.RST} {C.WHITE}{C.BOLD}{value}{C.RST}")


def stat_card(label, value, color=None, icon=""):
    """Print a single stat with optional icon."""
    clr = color or C.CYAN
    ico = f"{icon} " if icon else ""
    print(f"  {C.GRAY}  {ico}{C.RST}{C.GRAY}{label:<24}{C.RST} {clr}{C.BOLD}{value}{C.RST}")


# ── Separators ────────────────────────────────────────────────────────────────

def separator(width=76, style="light"):
    """Print a horizontal separator."""
    if style == "heavy":
        line = _gradient_line("━", width, 50, 50, 70, 35, 35, 50)
    elif style == "dots":
        line = f"{C.GRAY}{'·' * width}{C.RST}"
    else:
        line = f"{C.GRAY}{Box.H2 * width}{C.RST}"
    print(f"  {line}")

def spacer(lines=1):
    """Print blank lines."""
    for _ in range(lines):
        print()


# ── Badges & Pills ───────────────────────────────────────────────────────────

def pill(text, bg_color, fg_color=C.WHITE):
    """Return a pill/badge string with background colour."""
    return f"{bg_color}{fg_color}{C.BOLD} {text} {C.RST}"

def status_pill(passed):
    """Return PASS or FAIL pill."""
    if passed:
        return pill("✓ PASS", C.BG_SUCCESS, C.GREEN)
    return pill("✗ FAIL", C.BG_DANGER, C.RED)


# ── Grade Colour ──────────────────────────────────────────────────────────────

def grade_color(grade):
    """Return premium ANSI colour for a letter grade."""
    if grade in ("A", "A-"):
        return C.MINT
    elif grade in ("B+", "B", "B-"):
        return C.SKY
    elif grade in ("C+", "C", "C-"):
        return C.GOLD
    elif grade in ("D+", "D"):
        return C.CORAL
    elif grade == "F":
        return C.ROSE
    elif grade in ("W", "I"):
        return f"{C.RED}{C.DIM}"
    elif grade in ("P", "TR"):
        return C.LAVENDER
    return C.WHITE

def grade_pill(grade):
    """Return a coloured pill for a grade."""
    gclr = grade_color(grade)
    return f"{gclr}{C.BOLD}{grade:>3}{C.RST}"


# ── Progress Bar ──────────────────────────────────────────────────────────────

def progress_bar(current, total, width=40, label=""):
    """Return a premium gradient progress bar string."""
    if total == 0:
        ratio = 0.0
    else:
        ratio = min(current / total, 1.0)

    filled = int(width * ratio)
    empty = width - filled
    pct = ratio * 100

    # Build gradient filled section
    bar_chars = []
    for i in range(filled):
        t = i / max(width - 1, 1)
        if ratio >= 1.0:
            r, g, b = int(0 + 100 * t), int(220 - 20 * t), int(100 + 80 * t)
        elif ratio >= 0.6:
            r, g, b = int(255 - 55 * t), int(200 + 55 * t), int(0 + 100 * t)
        elif ratio >= 0.3:
            r, g, b = int(255), int(140 + 60 * t), int(0 + 80 * t)
        else:
            r, g, b = int(255 - 30 * t), int(70 + 30 * t), int(70 + 30 * t)
        bar_chars.append(f"\033[38;2;{r};{g};{b}m█")

    filled_str = "".join(bar_chars)
    empty_str = f"{C.GRAY}{'░' * empty}{C.RST}"

    # Percentage colour
    if ratio >= 1.0:
        pclr = C.MINT
    elif ratio >= 0.6:
        pclr = C.GOLD
    elif ratio >= 0.3:
        pclr = C.CORAL
    else:
        pclr = C.ROSE

    lbl = f"  {C.GRAY}{label}{C.RST}" if label else ""
    return f"{filled_str}{empty_str} {pclr}{C.BOLD}{pct:5.1f}%{C.RST}{lbl}"


# ── Table System ──────────────────────────────────────────────────────────────

def table_header(columns, widths):
    """Print a premium table header with underline."""
    hdr = "  "
    for col, w in zip(columns, widths):
        hdr += f" {C.LAVENDER}{C.BOLD}{col:<{w}}{C.RST}"
    print(hdr)
    # Separator
    sep = "  "
    for w in widths:
        sep += f" {C.GRAY}{Box.H2 * w}{C.RST}"
    print(sep)

def table_row(values, widths, colors=None, highlight=False):
    """Print a styled table data row."""
    prefix = f"{C.BG_ACCENT}" if highlight else ""
    suffix = f"{C.RST}" if highlight else ""
    row = f"  {prefix}"
    for i, (val, w) in enumerate(zip(values, widths)):
        clr = (colors[i] if colors and i < len(colors) else None) or C.WHITE
        row += f" {clr}{str(val):<{w}}{C.RST}"
    row += suffix
    print(row)

def table_divider(widths):
    """Print a thin table divider."""
    div = "  "
    for w in widths:
        div += f" {C.GRAY}{'·' * w}{C.RST}"
    print(div)


# ── Big Number Display ────────────────────────────────────────────────────────

def big_number(label, value, color=None, width=34):
    """Display a large emphasized number in a box."""
    clr = color or C.CYAN
    val_str = str(value)

    tl = f"{C.GRAY}{Box.TLR}{Box.H2 * (width)}{Box.TRR}{C.RST}"
    bl = f"{C.GRAY}{Box.BLR}{Box.H2 * (width)}{Box.BRR}{C.RST}"
    blank = f"{C.GRAY}│{C.RST}{' ' * width}{C.GRAY}│{C.RST}"

    lbl_pad = (width - len(label)) // 2
    lbl_line = f"{C.GRAY}│{C.RST}{' ' * lbl_pad}{C.GRAY}{C.ITAL}{label}{C.RST}{' ' * (width - lbl_pad - len(label))}{C.GRAY}│{C.RST}"

    val_pad = (width - len(val_str)) // 2
    val_line = f"{C.GRAY}│{C.RST}{' ' * val_pad}{clr}{C.BOLD}{val_str}{C.RST}{' ' * (width - val_pad - len(val_str))}{C.GRAY}│{C.RST}"

    print(f"\n  {tl}")
    print(f"  {lbl_line}")
    print(f"  {val_line}")
    print(f"  {bl}")


# ── Verdict Box ───────────────────────────────────────────────────────────────

def verdict_box(text, passed, width=42):
    """Display a pass/fail verdict in a prominent box."""
    if passed:
        clr = C.MINT
        border_clr = C.GREEN
        icon = "✓"
        bg = C.BG_SUCCESS
    else:
        clr = C.ROSE
        border_clr = C.RED
        icon = "✗"
        bg = C.BG_DANGER

    msg = f"{icon}  {text}"
    pad = (width - len(msg)) // 2

    top = f"{border_clr}{C.BOLD}{Box.TL}{Box.H * (width + 2)}{Box.TR}{C.RST}"
    mid = f"{border_clr}{C.BOLD}{Box.V}{C.RST}{bg} {' ' * pad}{clr}{C.BOLD}{msg}{C.RST}{bg}{' ' * (width - pad - len(msg))} {C.RST}{border_clr}{C.BOLD}{Box.V}{C.RST}"
    bot = f"{border_clr}{C.BOLD}{Box.BL}{Box.H * (width + 2)}{Box.BR}{C.RST}"

    print(f"\n  {top}")
    print(f"  {mid}")
    print(f"  {bot}")


# ── Checklist Item ────────────────────────────────────────────────────────────

def check_item(label, passed, detail=""):
    """Print a pass/fail checklist line."""
    if passed:
        sym = f"{C.MINT}{C.BOLD}  ✓{C.RST}"
        det = f"{C.MINT}{detail}{C.RST}" if detail else ""
    else:
        sym = f"{C.ROSE}{C.BOLD}  ✗{C.RST}"
        det = f"{C.ROSE}{detail}{C.RST}" if detail else ""
    print(f"  {sym}  {C.WHITE}{label:<40}{C.RST}  {det}")


# ── Recommendation ────────────────────────────────────────────────────────────

def recommendation(text):
    """Print a recommendation bullet."""
    print(f"    {C.GOLD}▸{C.RST}  {C.GOLD}{text}{C.RST}")


# ── Footer ────────────────────────────────────────────────────────────────────

def footer(width=76):
    """Print premium footer with timestamp."""
    line = _gradient_line("━", width, 80, 140, 255, 0, 200, 180)
    ts = datetime.now().strftime("%b %d, %Y  %H:%M")
    print(f"\n  {line}")
    print(f"  {C.GRAY}{C.ITAL}  NSU Degree Audit Engine  ·  CSE226 Project 1  ·  {ts}{C.RST}")
    print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DATA  ·  Transcript Loading
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_transcript(csv_path):
    """Load a transcript CSV → list of {course_code, grade, credits}."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [h.strip().lower().replace(" ", "_") for h in reader.fieldnames]
        for r in reader:
            code    = r.get("course_code", "").strip().upper()
            grade   = r.get("grade", "").strip().upper()
            credits = r.get("credits", r.get("credit", "0")).strip()
            if not code:
                continue
            try:
                cr = float(credits)
            except ValueError:
                cr = 0.0
            rows.append({"course_code": code, "grade": grade, "credits": cr})
    return rows


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DATA  ·  Retake Resolution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _grade_rank(grade):
    """Return a numeric rank for a grade (higher = better).

    Ranking ensures correct retake resolution:
    - A (4.0) = 14, down to D (1.0) = 11, F = 0 (worst GPA grade)
    - P/TR = 5 (better than F/W/I since they earn credits)
    - W = 1, I = 0 (no credits, no GPA impact)
    """
    if grade in GRADE_POINTS:
        if grade == "F":
            return 0                              # F is worst GPA grade (0 credits)
        return GRADE_POINTS[grade] + 10           # A=14, A-=13.7, ... D=11
    if grade in ("P", "TR"):
        return 5                                  # Pass/Transfer: earns credits, better than F
    if grade == "W":
        return 1                                  # Withdrawal: no impact
    if grade == "I":
        return 0                                  # Incomplete: needs resolution
    return -1                                     # Unknown

def resolve_retakes(rows):
    """Keep only the BEST attempt per course → (resolved, retake_history).

    Per NSU policy: 'Only the best grade will be used to calculate the CGPA.'
    """
    seen = OrderedDict()
    history = {}
    for r in rows:
        code = r["course_code"]
        if code in seen:
            if code not in history:
                history[code] = [seen[code]["grade"]]
            history[code].append(r["grade"])
            # Keep the attempt with the better grade
            if _grade_rank(r["grade"]) > _grade_rank(seen[code]["grade"]):
                seen[code] = r
        else:
            seen[code] = r
    return list(seen.values()), history


def get_academic_standing(cgpa):
    """Determine academic standing based on CGPA.

    Uses American-style Latin honors thresholds:
    - Summa Cum Laude: >= 3.90 (highest distinction)
    - Magna Cum Laude: >= 3.60 (high distinction)
    - Cum Laude: >= 3.30 (distinction)
    - Good Standing: >= 2.00 (meets requirements)
    - Academic Probation: < 2.00 (at risk)

    Note: NSU officially uses First/Second/Third Class system.
    Latin honors are displayed for enhanced user experience.

    Returns: (standing_name, icon)
    """
    if cgpa >= 3.90:
        return "Summa Cum Laude", "★★★★"
    elif cgpa >= 3.60:
        return "Magna Cum Laude", "★★★"
    elif cgpa >= 3.30:
        return "Cum Laude", "★★"
    elif cgpa >= 2.00:
        return "Good Standing", "★"
    else:
        return "ACADEMIC PROBATION", "⚠"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DATA  ·  Knowledge-Base Parsing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def parse_knowledge_base(md_path):
    """Parse knowledge_base.md → structured program data."""
    with open(md_path, encoding="utf-8") as f:
        text = f.read()

    result = {"programs": {}, "grading": dict(GRADE_POINTS)}
    prog_pattern = r'\[Program:\s*(.+?)\]'
    prog_splits = re.split(r'(?=##\s*\[Program:)', text)

    for chunk in prog_splits:
        m = re.search(prog_pattern, chunk)
        if not m:
            continue
        full_name = m.group(1).strip()
        if "CSE" in full_name.upper():
            key = "CSE"
        elif "LLB" in full_name.upper() or "LAW" in full_name.upper():
            key = "LLB"
        else:
            key = full_name.split("(")[-1].replace(")", "").strip()

        prog = {
            "full_name": full_name,
            "total_credits": 130,
            "mandatory": [],
            "choice_groups": [],
            "sections": [],
            "elective_pools": [],
            "elective_trails": {},
        }

        tc = re.search(r'Total Credits Required.*?(\d+)', chunk)
        if tc:
            prog["total_credits"] = int(tc.group(1))

        mand_section = re.search(
            r'### Mandatory Courses[^\n]*\n(?:(?!- )[^\n]*\n)*((?:- .+\n?)+)', chunk
        )
        if mand_section:
            for line in mand_section.group(1).strip().split("\n"):
                line = line.lstrip("- ").strip()
                codes = [c.strip() for c in line.split(",") if c.strip()]
                prog["mandatory"].extend(codes)

        course_line_re = re.compile(
            r'^- ([A-Z]{2,4}\d{2,4}[A-Z]?(?:\|[A-Z]{2,4}\d{2,4}[A-Z]?)*),(\d+(?:\.\d+)?),(.*)',
            re.MULTILINE,
        )
        section_header_re = re.compile(r'^#{3,4}\s+(.+)', re.MULTILINE)
        headers = list(section_header_re.finditer(chunk))

        for i, hm in enumerate(headers):
            header_title = hm.group(1).strip()
            start = hm.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(chunk)
            section_text = chunk[start:end]

            if header_title.rstrip().endswith("Trail"):
                trail_courses = []
                for cm in course_line_re.finditer(section_text):
                    codes_str, cr, name = cm.group(1), float(cm.group(2)), cm.group(3).strip()
                    for c in codes_str.split("|"):
                        trail_courses.append({"code": c.strip(), "credits": cr, "name": name})
                prog["elective_trails"][header_title] = trail_courses
                continue

            for cm in course_line_re.finditer(section_text):
                codes_str, cr, name = cm.group(1), float(cm.group(2)), cm.group(3).strip()
                codes_list = [c.strip() for c in codes_str.split("|")]
                if len(codes_list) > 1:
                    prog["choice_groups"].append({
                        "options": codes_list, "credits": cr,
                        "name": name, "section": header_title,
                    })
                else:
                    prog["sections"].append({
                        "code": codes_list[0], "credits": cr,
                        "name": name, "section": header_title,
                    })

        elective_pool_re = re.search(
            r'(?:Law Electives|Major Electives).*?Pick\s+(\d+)[^\n]*\n(?:\s*\n)*((?:- .+\n?)+)',
            chunk, re.IGNORECASE,
        )
        if elective_pool_re:
            pick_count = int(elective_pool_re.group(1))
            pool_courses = []
            for cm in course_line_re.finditer(elective_pool_re.group(2)):
                codes_str, cr, name = cm.group(1), float(cm.group(2)), cm.group(3).strip()
                pool_courses.append({"code": codes_str, "credits": cr, "name": name})
            prog["elective_pools"].append({
                "pick": pick_count, "courses": pool_courses,
                "name": "Law Electives" if key == "LLB" else "Major Electives",
            })

        result["programs"][key] = prog

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LOGIC  ·  Credit Classification
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def classify_credit(grade, credits):
    """Classify a course → (earned_credits, status_label, colour)."""
    if grade in NON_GPA_GRADES:
        if grade in ("P", "TR") and credits > 0:
            return credits, "EARNED (P/TR)", C.LAVENDER
        return 0.0, "EXCLUDED", C.GOLD
    if grade == "F":
        return 0.0, "FAILED", C.ROSE
    if credits == 0:
        return 0.0, "0-CREDIT", C.GRAY
    if grade in PASSING_GRADES:
        return credits, "EARNED", C.MINT
    return 0.0, "UNKNOWN", C.WHITE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LOGIC  ·  CGPA Computation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_cgpa(rows):
    """Compute CGPA → (cgpa, total_qp, total_gpa_cr, total_earned)."""
    total_qp = total_gpa_cr = total_earned = 0.0
    for r in rows:
        grade, credits = r["grade"], r["credits"]
        if grade in NON_GPA_GRADES:
            if grade in ("P", "TR") and credits > 0:
                total_earned += credits
            continue
        gp = GRADE_POINTS.get(grade)
        if gp is None:
            continue
        if credits > 0:
            total_qp += gp * credits
            total_gpa_cr += credits
            if grade != "F":
                total_earned += credits
    cgpa = total_qp / total_gpa_cr if total_gpa_cr > 0 else 0.0
    return cgpa, total_qp, total_gpa_cr, total_earned


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LOGIC  ·  Tuition Waiver
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_waiver(cgpa, credits_earned):
    """Return (waiver_%, label) based on CGPA & credits."""
    if credits_earned < 30:
        return 0, "Not eligible (need ≥ 30 completed credits)"
    if cgpa >= 3.97:
        return 100, "Chancellor's Award"
    elif cgpa >= 3.75:
        return 50, "Vice-Chancellor's Scholarship"
    elif cgpa >= 3.50:
        return 25, "Dean's Scholarship"
    return 0, "No waiver (CGPA < 3.50)"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UTILITY  ·  File Check
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def require_file(path, description="file"):
    """Exit with styled error if file missing."""
    if not os.path.isfile(path):
        print(f"\n  {C.ROSE}{C.BOLD}  ✗ Error:{C.RST} {description} not found: {C.GOLD}{path}{C.RST}")
        sys.exit(1)
