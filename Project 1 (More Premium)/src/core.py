"""
core.py  —  NSU Degree Audit Engine · Shared Core Module  v2.0
══════════════════════════════════════════════════════════════════
Premium terminal UI system with true-color gradient rendering,
neo-dark card layouts, animated-look data tables, grade mapping,
transcript parsing, and knowledge-base parsing.

Programs:  CSE (Computer Science) · ARCH (Architecture)
Author:    CSE226 Project 1
"""

import csv, os, re, sys
from collections import OrderedDict
from datetime import datetime

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

    # ── Ultra-premium neon accents ─────────────────────────
    NEON_CYAN  = _fg(0, 255, 255)
    NEON_PINK  = _fg(255, 50, 200)
    EMBER      = _fg(255, 90, 40)
    FROST      = _fg(200, 230, 255)
    AQUA       = _fg(0, 240, 210)
    SLATE      = _fg(120, 130, 160)
    SILVER     = _fg(190, 200, 215)
    SAPPHIRE   = _fg(80, 120, 255)
    ELECTRIC   = _fg(120, 220, 255)

    # ── Background accents ────────────────────────────────
    BG_DARK     = _bg(12, 12, 20)
    BG_CARD     = _bg(22, 22, 38)
    BG_ACCENT   = _bg(32, 32, 52)
    BG_SUCCESS  = _bg(15, 50, 25)
    BG_DANGER   = _bg(60, 15, 15)
    BG_WARN     = _bg(60, 50, 8)
    BG_INFO     = _bg(12, 35, 60)
    BG_HEADER   = _bg(25, 25, 45)
    BG_HIGHLIGHT = _bg(35, 30, 55)

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

def banner(title, subtitle="", width=78):
    """Print a premium neo-dark hero banner with decorative accents."""
    # ── Spaced title for dramatic look ────────────────────────
    spaced = "  ".join(title)
    display_len = len(spaced)
    inner = width - 4  # space inside the vertical bars

    # ── Gradient borders ────────────────────────────────────
    top = _gradient_line("━", width, 0, 220, 200, 100, 120, 255)
    bot = _gradient_line("━", width, 100, 120, 255, 0, 220, 200)
    deco = _gradient_line("─", inner - 6, 60, 60, 90, 40, 40, 65)

    # Sides
    lv = f"{C.AQUA}{Box.VH}{C.RST}"
    rv = f"{C.SAPPHIRE}{Box.VH}{C.RST}"

    prefix = f"  {C.BG_CARD}"
    suffix = f"{C.RST}"

    # ── Title line ───────────────────────────────────────────
    title_grad = _gradient_text(spaced, 80, 240, 255, 200, 140, 255)
    t_pad = (inner - display_len) // 2
    title_line = f"{lv}{C.BG_CARD}{' ' * t_pad}{C.BOLD}{title_grad}{C.RST}{C.BG_CARD}{' ' * (inner - t_pad - display_len)}{suffix}{rv}"

    # ── Subtitle line ────────────────────────────────────────
    sub_line = None
    if subtitle:
        s_pad = (inner - len(subtitle)) // 2
        sub_line = f"{lv}{C.BG_CARD}{' ' * s_pad}{C.SILVER}{C.ITAL}{subtitle}{C.RST}{C.BG_CARD}{' ' * (inner - s_pad - len(subtitle))}{suffix}{rv}"

    # ── Decorator line (inner accent) ────────────────────────
    deco_left = f"{C.GOLD}✦{C.RST}"
    deco_right = f"{C.GOLD}✦{C.RST}"
    deco_line_inner = f" {deco_left}  {deco}  {deco_right} "
    deco_pad = inner - (len("✦") + 2 + (inner - 6) + 2 + len("✦") + 2)
    deco_full = f"{lv}{C.BG_CARD}   {deco_left}  {deco}  {deco_right}   {suffix}{rv}"

    # ── Blank line with background ──────────────────────────
    blank = f"{lv}{C.BG_CARD}{' ' * inner}{suffix}{rv}"

    # ── Timestamp bar ───────────────────────────────────────
    from datetime import datetime as _dt
    ts = _dt.now().strftime("%b %d, %Y  %H:%M")
    bar_text = f"◈ NSU Degree Audit Engine v2.0  ·  {ts}"
    b_pad = (inner - len(bar_text)) // 2
    bar_line = f"{lv}{C.BG_ACCENT}{' ' * b_pad}{C.SLATE}{bar_text}{C.RST}{C.BG_ACCENT}{' ' * (inner - b_pad - len(bar_text))}{suffix}{rv}"
    mid_border = _gradient_line("─", width, 50, 50, 80, 35, 35, 55)

    print()
    print(f"  {top}")
    print(f"  {blank}")
    print(f"  {deco_full}")
    print(f"  {blank}")
    print(f"  {title_line}")
    if sub_line:
        print(f"  {sub_line}")
    print(f"  {blank}")
    print(f"  {deco_full}")
    print(f"  {blank}")
    print(f"  {mid_border}")
    print(f"  {bar_line}")
    print(f"  {bot}")


# ── Section Header (Card-style) ──────────────────────────────────────────────

def section(title, icon="", width=78):
    """Print a premium neo-dark section header with icon & gradient border."""
    prefix = f"{icon}  " if icon else ""
    display = f"{prefix}{title}"
    top  = _gradient_line("═", width, 0, 180, 160, 80, 100, 220)
    bot  = _gradient_line("─", width, 50, 50, 80, 30, 30, 50)
    title_grad = _gradient_text(display, 100, 230, 255, 200, 150, 255)
    print(f"\n  {top}")
    print(f"  {C.BG_HEADER}  {C.BOLD}{title_grad}{C.RST}{C.BG_HEADER}{' ' * max(0, width - len(display) - 4)}  {C.RST}")
    print(f"  {bot}")


# ── Info Rows ─────────────────────────────────────────────────────────────────

def info_line(label, value, label_w=32):
    """Print a styled key-value pair with dim label and bright value."""
    dot_fill = f"{C.SLATE}{'·' * max(1, label_w - len(label))}{C.RST}"
    print(f"  {C.SILVER}  {label} {dot_fill} {C.FROST}{C.BOLD}{value}{C.RST}")


def stat_card(label, value, color=None, icon=""):
    """Print a premium stat line with icon and colored value."""
    clr = color or C.ELECTRIC
    ico = f"{clr}{icon}{C.RST} " if icon else ""
    print(f"  {C.BG_CARD}  {ico}{C.SILVER}{label:<26}{C.RST}{C.BG_CARD} {clr}{C.BOLD}{value}{C.RST}{C.BG_CARD}  {C.RST}")


# ── Separators ────────────────────────────────────────────────────────────────

def separator(width=78, style="light"):
    """Print a horizontal separator."""
    if style == "heavy":
        line = _gradient_line("━", width, 50, 50, 80, 30, 30, 50)
    elif style == "dots":
        line = f"{C.SLATE}{'·' * width}{C.RST}"
    elif style == "double":
        line = _gradient_line("═", width, 40, 40, 70, 25, 25, 45)
    else:
        line = f"{C.SLATE}{Box.H2 * width}{C.RST}"
    print(f"  {line}")

def spacer(lines=1):
    """Print blank lines."""
    for _ in range(lines):
        print()


# ── Badges & Pills ───────────────────────────────────────────────────────────

def pill(text, bg_color, fg_color=None):
    """Return a pill/badge string with background colour."""
    fc = fg_color or C.WHITE
    return f"{bg_color}{fc}{C.BOLD} {text} {C.RST}"

def status_pill(passed):
    """Return PASS or FAIL pill."""
    if passed:
        return pill("✓ PASS", C.BG_SUCCESS, C.MINT)
    return pill("✗ FAIL", C.BG_DANGER, C.ROSE)


# ── Grade Colour ──────────────────────────────────────────────────────────────

def grade_color(grade):
    """Return premium ANSI colour for a letter grade."""
    if grade in ("A", "A-"):
        return C.MINT
    elif grade in ("B+", "B", "B-"):
        return C.ELECTRIC
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
    elif grade == "" or grade is None:
        return C.SLATE
    return C.WHITE

def grade_pill(grade):
    """Return a coloured pill for a grade."""
    if grade == "":
        return f"{C.SLATE}{C.ITAL}{'IP':>3}{C.RST}"
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
    """Print a premium table header with background and underline."""
    hdr = f"  {C.BG_HEADER}"
    for col, w in zip(columns, widths):
        hdr += f" {C.ELECTRIC}{C.BOLD}{col:<{w}}{C.RST}{C.BG_HEADER}"
    hdr += f"  {C.RST}"
    print(hdr)
    # Gradient separator
    total_w = sum(widths) + len(widths) + 2
    sep = f"  {_gradient_line(Box.H2, total_w, 60, 100, 180, 30, 50, 90)}"
    print(sep)

def table_row(values, widths, colors=None, highlight=False):
    """Print a styled table data row with optional subtle background."""
    bg = C.BG_CARD if highlight else ""
    row = f"  {bg}"
    for i, (val, w) in enumerate(zip(values, widths)):
        clr = (colors[i] if colors and i < len(colors) else None) or C.FROST
        row += f" {clr}{str(val):<{w}}{C.RST}{bg}"
    if highlight:
        row += f"  {C.RST}"
    print(row)

def table_divider(widths):
    """Print a thin table divider."""
    total_w = sum(widths) + len(widths) + 2
    div = f"  {C.SLATE}{'·' * total_w}{C.RST}"
    print(div)


# ── Big Number Display ────────────────────────────────────────────────────────

def big_number(label, value, color=None, width=36):
    """Display a large emphasized number in a double-line premium box."""
    clr = color or C.ELECTRIC
    val_str = str(value)

    tl = f"{C.SLATE}{Box.TL}{Box.H * (width)}{Box.TR}{C.RST}"
    bl = f"{C.SLATE}{Box.BL}{Box.H * (width)}{Box.BR}{C.RST}"
    mid_bar = f"{C.SLATE}{Box.V}{C.RST}{C.BG_CARD}{_gradient_line('─', width, 40, 40, 70, 25, 25, 45)}{C.RST}{C.SLATE}{Box.V}{C.RST}"

    lbl_pad = (width - len(label)) // 2
    lbl_line = f"{C.SLATE}{Box.V}{C.RST}{C.BG_CARD}{' ' * lbl_pad}{C.SILVER}{C.ITAL}{label}{C.RST}{C.BG_CARD}{' ' * (width - lbl_pad - len(label))}{C.RST}{C.SLATE}{Box.V}{C.RST}"

    val_pad = (width - len(val_str)) // 2
    val_line = f"{C.SLATE}{Box.V}{C.RST}{C.BG_CARD}{' ' * val_pad}{clr}{C.BOLD}{val_str}{C.RST}{C.BG_CARD}{' ' * (width - val_pad - len(val_str))}{C.RST}{C.SLATE}{Box.V}{C.RST}"

    blank = f"{C.SLATE}{Box.V}{C.RST}{C.BG_CARD}{' ' * width}{C.RST}{C.SLATE}{Box.V}{C.RST}"

    print(f"\n  {tl}")
    print(f"  {blank}")
    print(f"  {lbl_line}")
    print(f"  {mid_bar}")
    print(f"  {val_line}")
    print(f"  {blank}")
    print(f"  {bl}")


# ── Verdict Box ───────────────────────────────────────────────────────────────

def verdict_box(text, passed, width=48):
    """Display a premium pass/fail verdict in a prominent box."""
    if passed:
        clr = C.MINT
        border_clr = C.AQUA
        icon = "✓"
        bg = C.BG_SUCCESS
    else:
        clr = C.ROSE
        border_clr = C.NEON_PINK
        icon = "✗"
        bg = C.BG_DANGER

    msg = f"{icon}  {text}"
    pad = (width - len(msg)) // 2

    outer_top = f"{border_clr}{C.BOLD}{Box.TL}{Box.H * (width + 4)}{Box.TR}{C.RST}"
    outer_bot = f"{border_clr}{C.BOLD}{Box.BL}{Box.H * (width + 4)}{Box.BR}{C.RST}"
    blank = f"{border_clr}{C.BOLD}{Box.V}{C.RST}{bg}{' ' * (width + 4)}{C.RST}{border_clr}{C.BOLD}{Box.V}{C.RST}"
    mid = f"{border_clr}{C.BOLD}{Box.V}{C.RST}{bg}  {' ' * pad}{clr}{C.BOLD}{msg}{C.RST}{bg}{' ' * (width - pad - len(msg))}  {C.RST}{border_clr}{C.BOLD}{Box.V}{C.RST}"

    print(f"\n  {outer_top}")
    print(f"  {blank}")
    print(f"  {mid}")
    print(f"  {blank}")
    print(f"  {outer_bot}")


# ── Checklist Item ────────────────────────────────────────────────────────────

def check_item(label, passed, detail=""):
    """Print a premium pass/fail checklist line."""
    if passed:
        sym = f"{C.MINT}{C.BOLD}  ✓{C.RST}"
        det = f"{C.MINT}{detail}{C.RST}" if detail else ""
    else:
        sym = f"{C.ROSE}{C.BOLD}  ✗{C.RST}"
        det = f"{C.ROSE}{detail}{C.RST}" if detail else ""
    print(f"  {C.BG_CARD} {sym}  {C.FROST}{label:<42}{C.RST}{C.BG_CARD}  {det}  {C.RST}")


# ── Recommendation ────────────────────────────────────────────────────────────

def recommendation(text):
    """Print a premium recommendation bullet."""
    print(f"    {C.GOLD}▸{C.RST}  {C.GOLD}{C.ITAL}{text}{C.RST}")


def panel(label, items, color=None, width=78):
    """Print a compact multi-item panel."""
    clr = color or C.ELECTRIC
    hdr = _gradient_text(f"  {label}", 100, 200, 255, 160, 140, 255)
    print(f"\n  {C.BOLD}{hdr}{C.RST}")
    line = f"  {C.SLATE}{'~' * width}{C.RST}"
    print(line)
    for icon, key, val in items:
        print(f"  {C.BG_CARD}  {clr}{icon}{C.RST}{C.BG_CARD} {C.SILVER}{key:<28}{C.RST}{C.BG_CARD} {clr}{C.BOLD}{val}{C.RST}{C.BG_CARD}  {C.RST}")
    print(line)


# ── Footer ────────────────────────────────────────────────────────────────────

def footer(width=78):
    """Print premium footer with version, timestamp, and gradient border."""
    top_line = _gradient_line("═", width, 80, 140, 255, 0, 200, 180)
    bot_line = _gradient_line("━", width, 0, 200, 180, 80, 140, 255)
    ts = datetime.now().strftime("%b %d, %Y  %H:%M")
    text = f"◈  NSU Degree Audit Engine v2.0  ·  CSE226 Project 1  ·  {ts}"
    pad = (width - len(text)) // 2
    print(f"\n  {top_line}")
    print(f"  {C.BG_CARD}{' ' * pad}{C.SLATE}{C.ITAL}{text}{C.RST}{C.BG_CARD}{' ' * (width - pad - len(text))}{C.RST}")
    print(f"  {bot_line}")
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
    """Return a numeric rank for a grade (higher = better)."""
    if grade in GRADE_POINTS:
        return GRADE_POINTS[grade] + 10          # GPA grades rank 10–14
    if grade in ("P", "TR"):
        return 10.5                               # Pass/Transfer: above F(10), below D(11)
    if grade == "W":
        return 1                                  # Withdrawal
    if grade == "I":
        return 0                                  # Incomplete
    if grade == "":
        return -2                                 # In-progress / empty
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
        elif "ARCH" in full_name.upper() or "ARCHITECTURE" in full_name.upper():
            key = "ARCH"
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
            r'(?:Law Electives|Major Electives|Architecture Electives).*?Pick\s+(\d+)[^\n]*\n(?:\s*\n)*((?:- .+\n?)+)',
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
                "name": "Architecture Electives" if key == "ARCH" else "Major Electives",
            })

        result["programs"][key] = prog

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LOGIC  ·  Credit Classification
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def classify_credit(grade, credits):
    """Classify a course → (earned_credits, status_label, colour)."""
    if grade == "":
        return 0.0, "IN PROGRESS", C.ELECTRIC
    if grade in NON_GPA_GRADES:
        if grade in ("P", "TR") and credits > 0:
            return credits, "EARNED (P/TR)", C.LAVENDER
        return 0.0, "EXCLUDED", C.GOLD
    if grade == "F":
        return 0.0, "FAILED", C.ROSE
    if credits == 0:
        return 0.0, "0-CREDIT", C.SLATE
    if grade in PASSING_GRADES:
        return credits, "EARNED", C.MINT
    return 0.0, "UNKNOWN", C.FROST


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LOGIC  ·  CGPA Computation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_cgpa(rows):
    """Compute CGPA → (cgpa, total_qp, total_gpa_cr, total_earned)."""
    total_qp = total_gpa_cr = total_earned = 0.0
    for r in rows:
        grade, credits = r["grade"], r["credits"]
        if grade == "" or grade in NON_GPA_GRADES:
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
