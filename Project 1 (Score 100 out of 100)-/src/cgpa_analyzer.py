"""
cgpa_analyzer.py  —  Level 2 · CGPA & Waiver Handler
══════════════════════════════════════════════════════
Computes CGPA with retake resolution, interactively handles course
waivers, determines academic standing, and checks tuition waiver
eligibility.

Usage:  python cgpa_analyzer.py <transcript.csv>
"""

import sys
from core import (
    C, Box, GRADE_POINTS, PASSING_GRADES, NON_GPA_GRADES,
    load_transcript, resolve_retakes, compute_cgpa, compute_waiver,
    classify_credit, grade_color, grade_pill,
    banner, section, info_line, stat_card, separator, spacer,
    table_header, table_row, big_number, progress_bar,
    footer, require_file, _gradient_text,
)


def main():
    if len(sys.argv) < 2:
        print(f"\n  {C.ROSE}{C.BOLD}Usage:{C.RST}  python cgpa_analyzer.py {C.GOLD}<transcript.csv>{C.RST}")
        sys.exit(1)

    csv_path = sys.argv[1]
    require_file(csv_path, "Transcript CSV")

    # ── Load & Resolve ────────────────────────────────────────────────────
    raw_rows = load_transcript(csv_path)
    resolved, retakes = resolve_retakes(raw_rows)
    cgpa, total_qp, total_gpa_cr, total_earned = compute_cgpa(resolved)

    # ── Hero Banner ───────────────────────────────────────────────────────
    banner("CGPA & WAIVER HANDLER", "Level 2  ·  NSU Degree Audit")

    # ── Quick Stats ───────────────────────────────────────────────────────
    section("Transcript Overview", "📋")
    info_line("Source File", csv_path)
    info_line("Total Entries (raw)", str(len(raw_rows)))
    info_line("Unique Courses", str(len(resolved)))
    info_line("Retaken Courses", str(len(retakes)))
    spacer()

    # ── Grade Detail Table ────────────────────────────────────────────────
    section("Grade Detail Table", "📊")

    cols   = ["#", "Course", "Grade", "Credits", "Gr.Pts", "Qual.Pts"]
    widths = [5,   10,       7,       9,         9,         11]
    table_header(cols, widths)

    for i, r in enumerate(resolved, 1):
        code, grade, credits = r["course_code"], r["grade"], r["credits"]
        gp = GRADE_POINTS.get(grade)
        gclr = grade_color(grade)

        if grade in NON_GPA_GRADES:
            gp_str, qp_str, qp_clr = "—", "—", C.GRAY
        else:
            gp_str = f"{gp:.2f}" if gp is not None else "?"
            if gp is not None and credits > 0:
                qp_str = f"{gp * credits:.2f}"
                qp_clr = C.WHITE
            else:
                qp_str = "0.00"
                qp_clr = C.GRAY

        table_row(
            [f"{i:>3}.", code, grade, f"{credits:.1f}", gp_str, qp_str],
            widths,
            [C.GRAY, C.WHITE, gclr, C.WHITE, gclr, qp_clr],
        )

    separator()
    spacer()

    # ── CGPA Computation ──────────────────────────────────────────────────
    section("CGPA Computation", "🧮")
    stat_card("Total Quality Points", f"{total_qp:.2f}", C.SKY, "◆")
    stat_card("GPA-Eligible Credits", f"{total_gpa_cr:.1f}", C.SKY, "◆")
    stat_card("Total Earned Credits", f"{total_earned:.1f}", C.MINT, "✓")
    separator(style="dots")

    # CGPA colour
    if cgpa >= 3.50:
        cgpa_clr = C.MINT
    elif cgpa >= 2.00:
        cgpa_clr = C.GOLD
    else:
        cgpa_clr = C.ROSE

    big_number("Cumulative GPA", f"{cgpa:.2f}", cgpa_clr)
    spacer()

    # ── Academic Standing ─────────────────────────────────────────────────
    section("Academic Standing", "🏛️")

    if cgpa >= 3.90:
        standing, st_clr, st_icon = "Summa Cum Laude", C.MINT, "★★★★"
    elif cgpa >= 3.60:
        standing, st_clr, st_icon = "Magna Cum Laude", C.MINT, "★★★"
    elif cgpa >= 3.30:
        standing, st_clr, st_icon = "Cum Laude", C.SKY, "★★"
    elif cgpa >= 2.00:
        standing, st_clr, st_icon = "Good Standing", C.GOLD, "★"
    else:
        standing, st_clr, st_icon = "ACADEMIC PROBATION", C.ROSE, "⚠"

    grad_standing = _gradient_text(
        f"  {st_icon}  {standing}",
        *(
            (100, 255, 180, 0, 220, 180) if cgpa >= 3.30
            else (255, 215, 0, 255, 180, 80) if cgpa >= 2.00
            else (255, 100, 100, 255, 50, 50)
        ),
    )
    print(f"\n  {C.BOLD}{grad_standing}{C.RST}")

    if cgpa < 2.00:
        print(f"  {C.ROSE}  CGPA is below 2.00 — student is on academic probation.{C.RST}")
        print(f"  {C.ROSE}  Immediate improvement required to avoid dismissal.{C.RST}")
    spacer()

    # ── Course Waiver Handler (Interactive) ───────────────────────────────
    section("Course Waiver Handler", "📝")

    completed_codes = {r["course_code"] for r in resolved if r["grade"] in PASSING_GRADES}
    waived_courses = []

    print(f"\n  {C.SKY}{C.BOLD}  The admin may grant waivers for specific courses.{C.RST}")
    print(f"  {C.GRAY}  Waived courses are exempted from requirements but do{C.RST}")
    print(f"  {C.GRAY}  NOT earn credits or affect GPA.{C.RST}")
    print()
    print(f"  {C.GOLD}{C.BOLD}  ? Waivers granted for any courses?{C.RST}")
    print(f"  {C.GRAY}    Enter course codes separated by commas (e.g. ENG102, BUS112){C.RST}")
    print(f"  {C.GRAY}    Or press Enter to skip:{C.RST}")

    try:
        waiver_input = input(f"  {C.TEAL}{C.BOLD}  ▸ {C.RST}").strip()
    except (EOFError, KeyboardInterrupt):
        waiver_input = ""

    if waiver_input:
        raw_codes = [c.strip().upper() for c in waiver_input.split(",") if c.strip()]
        for code in raw_codes:
            if code in completed_codes:
                print(f"    {C.GOLD}⚠ {code} — already completed, waiver not needed.{C.RST}")
            else:
                waived_courses.append(code)
                print(f"    {C.MINT}✓ {code} — waiver applied (requirement exempted).{C.RST}")

    if waived_courses:
        separator(style="dots")
        stat_card("Waived Courses", ", ".join(waived_courses), C.TEAL, "◆")
        stat_card("Waiver Count", f"{len(waived_courses)} course(s)", C.TEAL, "◆")
        stat_card("Adjusted Status", "Requirements now satisfied", C.MINT, "✓")
        print(f"\n  {C.GRAY}  Note: Waived courses satisfy requirements but do not{C.RST}")
        print(f"  {C.GRAY}  contribute to earned credits or CGPA.{C.RST}")
    else:
        print(f"\n  {C.GRAY}  No waivers applied.{C.RST}")
    spacer()

    # ── Retake Impact Analysis ────────────────────────────────────────────
    if retakes:
        section(f"Retake Impact Analysis  ({len(retakes)} retake(s))", "🔄")

        cols2   = ["Course", "Old", "New", "Impact"]
        widths2 = [10, 8, 8, 24]
        table_header(cols2, widths2)

        for code, grades in retakes.items():
            old, new = grades[0], grades[-1]
            old_gp = GRADE_POINTS.get(old, 0)
            new_gp = GRADE_POINTS.get(new, 0)
            diff = new_gp - old_gp
            if diff > 0:
                change_str = f"+{diff:.2f} ↑ improved"
                ch_clr = C.MINT
            elif diff < 0:
                change_str = f"{diff:.2f} ↓ declined"
                ch_clr = C.ROSE
            else:
                change_str = " 0.00   no change"
                ch_clr = C.GRAY

            table_row(
                [code, old, new, change_str],
                widths2,
                [C.WHITE, grade_color(old), grade_color(new), ch_clr],
            )

        separator()
        spacer()

    # ── Tuition Waiver Eligibility ────────────────────────────────────────
    section("Tuition Waiver Eligibility", "💰")

    waiver_pct, waiver_label = compute_waiver(cgpa, total_earned)

    if waiver_pct > 0:
        print(f"\n  {C.MINT}{C.BOLD}  ✓ Eligible:  {waiver_pct}% Tuition Waiver{C.RST}")
        print(f"     {C.TEAL}{waiver_label}{C.RST}")
    else:
        print(f"\n  {C.GOLD}{C.BOLD}  ○ {waiver_label}{C.RST}")
        if total_earned < 30:
            print(f"     {C.GRAY}Complete at least 30 credits to be considered.{C.RST}")
        else:
            print(f"     {C.GRAY}Raise CGPA to 3.50+ for Dean's Scholarship.{C.RST}")

    # Scholarship ladder
    print()
    thresholds = [
        (3.50, "25%", "Dean's Scholarship", C.SKY),
        (3.75, "50%", "VC Scholarship", C.LAVENDER),
        (3.97, "100%", "Chancellor's Award", C.MINT),
    ]
    for threshold, pct_str, label, clr in thresholds:
        if cgpa >= threshold:
            marker = f"{C.MINT}●{C.RST}"
        else:
            marker = f"{C.GRAY}○{C.RST}"
        print(f"  {marker}  {C.WHITE}≥ {threshold:.2f}{C.RST}  →  {clr}{C.BOLD}{pct_str:<5}{C.RST} {C.GRAY}{label}{C.RST}")

    footer()


if __name__ == "__main__":
    main()
