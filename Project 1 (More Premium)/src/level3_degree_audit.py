"""
level3_degree_audit.py  —  Level 3 · Degree Audit & Deficiency Reporter
════════════════════════════════════════════════════════════════════════
Loads transcript + knowledge base, audits mandatory courses, choice
groups, elective trails/pools, credit progress, academic standing,
and renders a premium graduation eligibility verdict.

Usage:  python level3_degree_audit.py <transcript.csv> <CSE|ARCH> [knowledge_base.md]
"""

import sys, os
from core import (
    C, Box, GRADE_POINTS, PASSING_GRADES, NON_GPA_GRADES,
    load_transcript, resolve_retakes, compute_cgpa, compute_waiver,
    classify_credit, grade_color, grade_pill, parse_knowledge_base,
    _grade_rank,
    banner, section, info_line, stat_card, separator, spacer,
    table_header, table_row, progress_bar, big_number, panel,
    check_item, verdict_box, recommendation,
    footer, require_file, _gradient_text,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _completed_set(resolved):
    return {r["course_code"] for r in resolved if r["grade"] in PASSING_GRADES}

def _credit_map(resolved):
    return {r["course_code"]: r["credits"] for r in resolved if r["grade"] in PASSING_GRADES}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(f"\n  {C.ROSE}{C.BOLD}Usage:{C.RST}  python level3_degree_audit.py "
              f"{C.GOLD}<transcript.csv> <CSE|ARCH>{C.RST} "
              f"{C.SLATE}[knowledge_base.md]{C.RST}")
        sys.exit(1)

    csv_path = sys.argv[1]
    program  = sys.argv[2].strip().upper()
    kb_path  = sys.argv[3] if len(sys.argv) > 3 else "knowledge_base.md"

    if program not in ("CSE", "ARCH"):
        print(f"\n  {C.ROSE}{C.BOLD}✗ Error:{C.RST} Unknown program '{program}'. Use CSE or ARCH.")
        sys.exit(1)

    require_file(csv_path, "Transcript CSV")
    require_file(kb_path, "Knowledge Base")

    # ── Load ──────────────────────────────────────────────────────────────
    raw_rows = load_transcript(csv_path)
    resolved, retakes = resolve_retakes(raw_rows)
    kb = parse_knowledge_base(kb_path)

    if program not in kb["programs"]:
        print(f"\n  {C.ROSE}{C.BOLD}✗ Error:{C.RST} '{program}' not found in knowledge base.")
        sys.exit(1)

    prog = kb["programs"][program]
    completed = _completed_set(resolved)
    cred_map  = _credit_map(resolved)
    cgpa, total_qp, total_gpa_cr, total_earned = compute_cgpa(resolved)

    # ══════════════════════════════════════════════════════════════════════
    #  OUTPUT
    # ══════════════════════════════════════════════════════════════════════

    banner(f"DEGREE AUDIT  ·  {program}", f"Level 3  ·  {prog['full_name']}")

    # ── Quick Overview ────────────────────────────────────────────────────
    section("Student Overview", "👤")
    info_line("Transcript", csv_path)
    info_line("Program", prog["full_name"])
    info_line("Credits Required", str(prog["total_credits"]))
    info_line("Credits Earned", f"{total_earned:.1f}")

    cgpa_clr = C.MINT if cgpa >= 3.50 else (C.GOLD if cgpa >= 2.00 else C.ROSE)
    info_line("CGPA", f"{cgpa_clr}{C.BOLD}{cgpa:.2f}{C.RST}")
    spacer()

    # ══════════════════════════════════════════════════════════════════════
    #  1. MANDATORY COURSES
    # ══════════════════════════════════════════════════════════════════════

    mandatory = prog["mandatory"]
    mand_done = [c for c in mandatory if c in completed]
    mand_miss = [c for c in mandatory if c not in completed]

    section(f"Mandatory Course Audit  ({len(mandatory)} courses)", "📋")

    cols   = ["#", "Course", "Status"]
    widths = [5,   12,       20]
    table_header(cols, widths)

    for i, code in enumerate(mandatory, 1):
        if code in completed:
            table_row(
                [f"{i:>3}.", code, "✓ Completed"],
                widths,
                [C.SLATE, C.FROST, C.MINT],
            )
        else:
            table_row(
                [f"{i:>3}.", code, "✗ Missing"],
                widths,
                [C.SLATE, C.ROSE, C.ROSE],
            )

    separator()
    spacer()

    stat_card("Completed", f"{len(mand_done)} / {len(mandatory)}", C.MINT, "✓")
    stat_card("Missing", str(len(mand_miss)), C.ROSE, "✗")
    print(f"\n  {progress_bar(len(mand_done), len(mandatory), width=50)}")

    if mand_miss:
        print(f"\n  {C.ROSE}{C.BOLD}  Missing mandatory courses:{C.RST}")
        for j in range(0, len(mand_miss), 8):
            chunk = mand_miss[j:j+8]
            print(f"    {C.ROSE}" + "  ".join(chunk) + f"{C.RST}")
    spacer()

    # ══════════════════════════════════════════════════════════════════════
    #  2. CHOICE GROUPS
    # ══════════════════════════════════════════════════════════════════════

    choice_groups = prog["choice_groups"]
    cg_satisfied = 0
    cg_total = len(choice_groups)

    if choice_groups:
        section(f"Choice-Group Audit  ({cg_total} groups)", "🔀")

        for cg in choice_groups:
            options, cr = cg["options"], cg["credits"]
            label = " │ ".join(options)
            taken = [o for o in options if o in completed]

            if taken:
                cg_satisfied += 1
                print(f"  {C.MINT}{C.BOLD}  ✓{C.RST}  {C.FROST}{label:<38}{C.RST} "
                      f"{C.SLATE}({cr:.0f} cr){C.RST}  →  {C.MINT}{taken[0]}{C.RST}")
            else:
                print(f"  {C.ROSE}{C.BOLD}  ✗{C.RST}  {C.FROST}{label:<38}{C.RST} "
                      f"{C.SLATE}({cr:.0f} cr){C.RST}  →  {C.ROSE}None taken{C.RST}")

        separator(style="dots")
        stat_card("Satisfied", f"{cg_satisfied} / {cg_total}", C.MINT, "✓")
        if cg_satisfied < cg_total:
            print(f"  {C.ROSE}  ⚠ {cg_total - cg_satisfied} choice group(s) still need fulfillment.{C.RST}")
        spacer()

    # ══════════════════════════════════════════════════════════════════════
    #  3. ELECTIVE AUDIT
    # ══════════════════════════════════════════════════════════════════════

    elective_ok = True

    if program == "CSE":
        # ── CSE Major Electives (9 credits / 3 courses from trails) ───────
        section("CSE Major Elective Audit  (9 Credits)", "🎯")

        trail_hits = {}
        all_trail_codes = set()

        for trail_name, courses in prog["elective_trails"].items():
            matched = [c for c in courses if c["code"] in completed]
            trail_hits[trail_name] = matched
            for c in courses:
                all_trail_codes.add(c["code"])

        total_elective_cr = sum(
            sum(c["credits"] for c in v) for v in trail_hits.values()
        )

        for trail_name, matched in trail_hits.items():
            if matched:
                cnt = len(matched)
                cr = sum(c["credits"] for c in matched)
                print(f"  {C.MINT}●{C.RST}  {C.AQUA}{trail_name:<44}{C.RST}"
                      f" {C.MINT}{cnt} course(s), {cr:.0f} cr{C.RST}")
                for c in matched:
                    print(f"      {C.FROST}{c['code']:<10}{C.RST} {C.SLATE}{c['name']}{C.RST}")
            else:
                print(f"  {C.SLATE}○  {trail_name:<44}{C.RST} {C.SLATE}0 courses{C.RST}")

        separator(style="dots")

        trails_2plus = [t for t, m in trail_hits.items() if len(m) >= 2]
        trails_1plus = [t for t, m in trail_hits.items() if len(m) >= 1]
        trail_rule_ok = len(trails_2plus) >= 1 and len(trails_1plus) >= 2
        credit_rule_ok = total_elective_cr >= 9

        if trail_rule_ok and credit_rule_ok:
            print(f"\n  {C.MINT}{C.BOLD}  ✓ Trail rule satisfied{C.RST}"
                  f" {C.SLATE}(≥2 from one trail + ≥1 from another){C.RST}")
            print(f"  {C.MINT}{C.BOLD}  ✓ Credit rule satisfied{C.RST}"
                  f" {C.SLATE}({total_elective_cr:.0f}/9 credits){C.RST}")
        else:
            elective_ok = False
            if not trail_rule_ok:
                print(f"\n  {C.ROSE}{C.BOLD}  ✗ Trail rule NOT met{C.RST}"
                      f" {C.SLATE}(need ≥2 from one trail + ≥1 from another){C.RST}")
            if not credit_rule_ok:
                print(f"  {C.ROSE}{C.BOLD}  ✗ Credit rule NOT met{C.RST}"
                      f" {C.SLATE}({total_elective_cr:.0f}/9 credits){C.RST}")
                needed = 9 - total_elective_cr
                if needed > 0:
                    print(f"  {C.GOLD}  Need {needed:.0f} more elective credits.{C.RST}")
        spacer()

        # ── Open Electives (3 cr) ─────────────────────────────────────────
        section("Open Electives  (3 Credits)", "📂")
        known_codes = set(prog["mandatory"])
        for cg in choice_groups:
            known_codes.update(cg["options"])
        known_codes.update(all_trail_codes)
        for sec in prog["sections"]:
            known_codes.add(sec["code"])

        open_cr = sum(
            r["credits"] for r in resolved
            if r["course_code"] not in known_codes
            and r["grade"] in PASSING_GRADES
            and r["credits"] > 0
        )

        if open_cr >= 3:
            print(f"\n  {C.MINT}{C.BOLD}  ✓ Open elective requirement met{C.RST}"
                  f" {C.SLATE}({open_cr:.0f} credits){C.RST}")
        else:
            print(f"\n  {C.GOLD}{C.BOLD}  ○ Open electives:{C.RST} {open_cr:.0f}/3 credits")
            if open_cr < 3:
                elective_ok = False
        spacer()

    elif program == "ARCH":
        # ── ARCH Architecture Electives (Pick 4 from pool) ───────────────
        if prog["elective_pools"]:
            pool = prog["elective_pools"][0]
            pick = pool["pick"]

            section(f"Architecture Elective Audit  (Pick {pick}, 12 Credits)", "🏛️")

            matched = []
            for pc in pool["courses"]:
                if pc["code"] in completed:
                    matched.append(pc)
                    print(f"  {C.MINT}●{C.RST}  {C.FROST}{pc['code']:<10}{C.RST}"
                          f" {C.MINT}{pc['name']}{C.RST}")
                else:
                    print(f"  {C.SLATE}○  {pc['code']:<10}{C.RST}"
                          f" {C.SLATE}{pc['name']}{C.RST}")

            separator(style="dots")
            elec_cr = sum(c["credits"] for c in matched)
            if len(matched) >= pick:
                print(f"\n  {C.MINT}{C.BOLD}  ✓ Architecture elective requirement met{C.RST}"
                      f" {C.SLATE}({len(matched)}/{pick} courses, {elec_cr:.0f} cr){C.RST}")
            else:
                elective_ok = False
                shortfall = pick - len(matched)
                print(f"\n  {C.ROSE}{C.BOLD}  ✗ Need {shortfall} more architecture elective(s){C.RST}"
                      f" {C.SLATE}({len(matched)}/{pick}){C.RST}")
            spacer()

        # ── Open Electives (6 cr) ─────────────────────────────────────────
        section("Open Electives  (6 Credits)", "📂")
        known_codes = set(prog["mandatory"])
        for cg in choice_groups:
            known_codes.update(cg["options"])
        for sec in prog["sections"]:
            known_codes.add(sec["code"])
        if prog["elective_pools"]:
            for pc in prog["elective_pools"][0]["courses"]:
                known_codes.add(pc["code"])

        free_cr = sum(
            r["credits"] for r in resolved
            if r["course_code"] not in known_codes
            and r["grade"] in PASSING_GRADES
            and r["credits"] > 0
        )

        if free_cr >= 6:
            print(f"\n  {C.MINT}{C.BOLD}  ✓ Open elective requirement met{C.RST}"
                  f" {C.SLATE}({free_cr:.0f} credits){C.RST}")
        else:
            print(f"\n  {C.GOLD}{C.BOLD}  ○ Open electives:{C.RST} {free_cr:.0f}/6 credits")
            if free_cr < 6:
                elective_ok = False
        spacer()

    # ══════════════════════════════════════════════════════════════════════
    #  4. RETAKE HISTORY
    # ══════════════════════════════════════════════════════════════════════

    if retakes:
        section(f"Retake History  ({len(retakes)} course(s))", "🔄")

        for code, grades in retakes.items():
            arrow = f" {C.SLATE}→{C.RST} ".join(
                f"{grade_color(g)}{g if g else 'IP'}{C.RST}" for g in grades
            )
            best = max(grades, key=lambda g: _grade_rank(g))
            print(f"  {C.FROST}  {code:<10}{C.RST} {arrow}  "
                  f"{C.SLATE}(best: {grade_color(best)}{C.BOLD}{best if best else 'IP'}{C.RST}"
                  f"{C.SLATE}){C.RST}")
        spacer()

    # ══════════════════════════════════════════════════════════════════════
    #  5. CREDIT PROGRESS
    # ══════════════════════════════════════════════════════════════════════

    target = prog["total_credits"]
    remaining = max(0, target - total_earned)

    section("Credit Progress", "📊")
    stat_card("Earned", f"{total_earned:.1f} / {target}", C.MINT, "✓")
    stat_card("Remaining", f"{remaining:.1f}", C.ELECTRIC, "○")
    print(f"\n  {progress_bar(total_earned, target, width=50)}")
    spacer()

    # ══════════════════════════════════════════════════════════════════════
    #  6. ACADEMIC STANDING & WAIVER
    # ══════════════════════════════════════════════════════════════════════

    section("Academic Standing & Waiver", "🏛️")

    if cgpa >= 3.90:
        standing = "Summa Cum Laude"
    elif cgpa >= 3.60:
        standing = "Magna Cum Laude"
    elif cgpa >= 3.30:
        standing = "Cum Laude"
    elif cgpa >= 2.00:
        standing = "Good Standing"
    else:
        standing = "ACADEMIC PROBATION"

    stat_card("Standing", standing, cgpa_clr, "★")
    stat_card("CGPA", f"{cgpa:.2f}", cgpa_clr, "◆")

    waiver_pct, waiver_label = compute_waiver(cgpa, total_earned)
    if waiver_pct > 0:
        stat_card("Waiver", f"{waiver_pct}% — {waiver_label}", C.MINT, "✓")
    else:
        stat_card("Waiver", waiver_label, C.SLATE, "○")
    spacer()

    # ══════════════════════════════════════════════════════════════════════
    #  7. GRADUATION ELIGIBILITY VERDICT
    # ══════════════════════════════════════════════════════════════════════

    crit_cgpa   = cgpa >= 2.00
    crit_mand   = len(mand_miss) == 0
    crit_cg     = cg_satisfied == cg_total
    crit_elec   = elective_ok
    crit_credit = total_earned >= target
    all_pass    = crit_cgpa and crit_mand and crit_cg and crit_elec and crit_credit

    section("GRADUATION ELIGIBILITY VERDICT", "⚖️")
    spacer()

    check_item("CGPA ≥ 2.00", crit_cgpa, f"{cgpa:.2f}")
    check_item("All mandatory courses completed", crit_mand,
               f"{len(mand_done)}/{len(mandatory)}")
    check_item("All choice groups satisfied", crit_cg,
               f"{cg_satisfied}/{cg_total}")
    check_item("Elective requirements met", crit_elec,
               "Yes" if crit_elec else "No")
    check_item(f"Total credits ≥ {target}", crit_credit,
               f"{total_earned:.0f}/{target}")

    verdict_box(
        "ELIGIBLE TO GRADUATE" if all_pass else "NOT ELIGIBLE TO GRADUATE",
        all_pass,
    )

    if not all_pass:
        print(f"\n  {C.GOLD}{C.BOLD}  Recommendations:{C.RST}")
        if not crit_cgpa:
            recommendation(f"Raise CGPA above 2.00 (currently {cgpa:.2f})")
        if not crit_mand:
            recommendation(f"Complete {len(mand_miss)} missing mandatory course(s)")
        if not crit_cg:
            recommendation(f"Fulfil {cg_total - cg_satisfied} remaining choice group(s)")
        if not crit_elec:
            recommendation("Satisfy elective credit/trail requirements")
        if not crit_credit:
            recommendation(f"Earn {remaining:.0f} more credits to reach {target}")

    footer()


if __name__ == "__main__":
    main()
