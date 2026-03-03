"""
level1_credit_tally.py  —  Level 1 · Credit Tally Engine
═════════════════════════════════════════════════════════
Reads a student transcript CSV, resolves retakes, classifies each
course's credit status, and produces a premium styled credit report.

Usage:  python level1_credit_tally.py <transcript.csv> [target_credits]
"""

import sys
from core import (
    C, Box, GRADE_POINTS, PASSING_GRADES, NON_GPA_GRADES,
    load_transcript, resolve_retakes, classify_credit, grade_color, grade_pill,
    _grade_rank,
    banner, section, info_line, stat_card, separator, spacer,
    table_header, table_row, progress_bar, panel, footer, require_file,
)


def main():
    if len(sys.argv) < 2:
        print(f"\n  {C.ROSE}{C.BOLD}Usage:{C.RST}  python level1_credit_tally.py {C.GOLD}<transcript.csv> [target_credits]{C.RST}")
        sys.exit(1)

    csv_path = sys.argv[1]
    credit_target = int(sys.argv[2]) if len(sys.argv) >= 3 else 130
    require_file(csv_path, "Transcript CSV")

    # ── Load & Resolve ────────────────────────────────────────────────────
    raw_rows = load_transcript(csv_path)
    resolved, retakes = resolve_retakes(raw_rows)

    # ── Hero Banner ───────────────────────────────────────────────────────
    banner("CREDIT TALLY ENGINE", "Level 1  ·  NSU Degree Audit")

    # ── Transcript Overview ───────────────────────────────────────────────
    section("Transcript Overview", "📋")
    info_line("Source File", csv_path)
    info_line("Total Entries (raw)", str(len(raw_rows)))
    info_line("Unique Courses", str(len(resolved)))
    info_line("Retaken Courses", str(len(retakes)))
    spacer()

    # ── Course Breakdown Table ────────────────────────────────────────────
    section("Course-by-Course Breakdown", "📊")

    cols   = ["#", "Course", "Grade", "Credits", "Earned", "Status"]
    widths = [5,   10,       7,       9,         9,        16]
    table_header(cols, widths)

    total_credits    = 0.0
    total_earned     = 0.0
    earned_courses   = 0
    failed_courses   = 0
    excluded_courses = 0
    zero_credit_cnt  = 0

    for i, r in enumerate(resolved, 1):
        code    = r["course_code"]
        grade   = r["grade"]
        credits = r["credits"]

        earned, status, sclr = classify_credit(grade, credits)
        total_credits += credits
        total_earned  += earned

        if status in ("EARNED", "EARNED (P/TR)"):
            earned_courses += 1
        elif status == "FAILED":
            failed_courses += 1
        elif status == "EXCLUDED":
            excluded_courses += 1
        elif status == "0-CREDIT":
            zero_credit_cnt += 1

        gclr = grade_color(grade)
        display_grade = grade if grade else "IP"
        earned_str = f"{earned:.1f}" if earned > 0 else "—"
        table_row(
            [f"{i:>3}.", code, display_grade, f"{credits:.1f}", earned_str, status],
            widths,
            [C.SLATE, C.FROST, gclr, C.FROST, sclr, sclr],
        )

    separator()
    spacer()

    # ── Credit Summary Cards ──────────────────────────────────────────────
    section("Credit Summary", "📈")
    stat_card("Attempted Credits", f"{total_credits:.1f}", C.ELECTRIC, "◆")
    stat_card("Earned Credits", f"{total_earned:.1f}", C.MINT, "✓")
    stat_card("Courses Earned", str(earned_courses), C.MINT, "●")
    stat_card("Courses Failed", str(failed_courses), C.ROSE, "●")
    stat_card("Excluded (W/I)", str(excluded_courses), C.GOLD, "○")
    stat_card("Zero-Credit Labs", str(zero_credit_cnt), C.SLATE, "○")
    spacer()

    # ── Retake History ────────────────────────────────────────────────────
    if retakes:
        section(f"Retake History  ({len(retakes)} course(s))", "🔄")

        cols2   = ["Course", "Attempts", "Grade Journey", "Best"]
        widths2 = [10, 10, 28, 10]
        table_header(cols2, widths2)

        for code, grades in retakes.items():
            journey = f" {C.SLATE}→{C.RST} ".join(
                f"{grade_color(g)}{g if g else 'IP'}{C.RST}" for g in grades
            )
            best = max(grades, key=lambda g: _grade_rank(g))
            table_row(
                [code, str(len(grades)), journey, best if best else "IP"],
                widths2,
                [C.FROST, C.ELECTRIC, None, grade_color(best)],
            )

        separator()
        print(f"\n  {C.GOLD}  ⚠  Only the best grade is used for CGPA (per NSU policy).{C.RST}")
        spacer()

    # ── Degree Progress ───────────────────────────────────────────────────
    section("Degree Credit Progress", "🎓")
    print(f"\n  {progress_bar(total_earned, credit_target, width=50)}")
    remaining = max(0, credit_target - total_earned)
    if remaining > 0:
        print(f"  {C.SLATE}  {remaining:.0f} credits remaining to reach {credit_target}{C.RST}")
    else:
        print(f"  {C.MINT}{C.BOLD}  ✓ Credit requirement met!{C.RST}")

    footer()


if __name__ == "__main__":
    main()
