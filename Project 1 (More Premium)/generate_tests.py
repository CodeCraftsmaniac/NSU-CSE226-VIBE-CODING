"""
generate_tests.py — Generate 20 test transcript CSVs (10 CSE + 10 ARCH)
═══════════════════════════════════════════════════════════════════════
Each file is a realistic NSU student transcript covering 10 distinct scenarios:
  - Different completion stages (freshman → graduated)
  - Various GPA ranges (probation → summa cum laude)
  - Retake scenarios (single, double, triple)
  - Special grades: W, I, P, TR, F
  - 0-credit labs & choice-group variations
"""

import csv, os, random, math

random.seed(42)  # reproducible

# ── Grade helpers ─────────────────────────────────────────────────────────────
GPA_GRADES   = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F"]
PASS_GRADES  = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D"]
SPECIAL      = ["W", "I", "P", "TR"]
ALL_GRADES   = GPA_GRADES + SPECIAL
GRADE_PTS    = {"A":4.0,"A-":3.7,"B+":3.3,"B":3.0,"B-":2.7,"C+":2.3,"C":2.0,"C-":1.7,"D+":1.3,"D":1.0,"F":0.0}

SEMESTERS = [
    "Spring 2022","Summer 2022","Fall 2022",
    "Spring 2023","Summer 2023","Fall 2023",
    "Spring 2024","Summer 2024","Fall 2024",
    "Spring 2025","Summer 2025","Fall 2025",
    "Spring 2026",
]

def pick_grade(profile):
    """Pick a random grade based on student profile."""
    if profile == "excellent":
        return random.choices(["A","A-","B+","B"], weights=[40,30,20,10])[0]
    elif profile == "good":
        return random.choices(["A","A-","B+","B","B-","C+","C"], weights=[10,15,20,25,15,10,5])[0]
    elif profile == "average":
        return random.choices(["B","B-","C+","C","C-","D+","D","F"], weights=[5,10,20,25,15,10,10,5])[0]
    elif profile == "struggling":
        return random.choices(["C","C-","D+","D","F","W"], weights=[10,15,15,20,30,10])[0]
    elif profile == "probation":
        return random.choices(["D+","D","F","F","W","I"], weights=[10,15,30,25,15,5])[0]
    else:  # mixed
        return random.choice(GPA_GRADES)

def assign_semester(idx, total):
    """Assign a semester proportionally."""
    pos = int(idx / max(total, 1) * min(len(SEMESTERS), 10))
    pos = min(pos, len(SEMESTERS) - 1)
    return SEMESTERS[pos]


# ═════════════════════════════════════════════════════════════════════════════
#  CSE COURSE CATALOG
# ═════════════════════════════════════════════════════════════════════════════

CSE_UNIV_CORE = [
    ("ENG102", 3), ("ENG103", 3), ("ENG111", 3), ("BEN205", 3),
    ("PHI104", 3), ("HIS102", 3), ("HIS103", 3),
]
CSE_UNIV_CHOICE = [
    [("ECO101", 3), ("ECO104", 3)],
    [("POL101", 3), ("POL104", 3)],
    [("SOC101", 3), ("ANT101", 3), ("ENV203", 3), ("GEO205", 3)],
    [("BIO103", 4), ("PHY107", 4), ("CHE101", 4)],  # science with lab (also in SEPS)
]
CSE_SEPS_CORE = [
    ("MAT116", 0), ("MAT120", 3), ("MAT130", 3), ("MAT250", 3),
    ("MAT350", 3), ("MAT361", 3), ("MAT125", 3),
    ("PHY107", 4), ("PHY108", 4), ("CHE101", 4),
    ("EEE452", 3), ("CEE110", 1),
    ("CSE115", 3), ("CSE115L", 1),
]
CSE_MAJOR_CORE = [
    ("CSE173", 3), ("CSE215", 3), ("CSE215L", 1),
    ("CSE225", 3), ("CSE225L", 0), ("CSE231", 3), ("CSE231L", 0),
    ("EEE141", 3), ("EEE141L", 1), ("EEE111", 3), ("EEE111L", 1),
    ("CSE311", 3), ("CSE311L", 0), ("CSE323", 3), ("CSE327", 3),
    ("CSE331", 3), ("CSE331L", 0), ("CSE373", 3), ("CSE332", 3),
    ("CSE425", 3),
]
CSE_CAPSTONE = [("CSE299", 1), ("CSE499A", 1.5), ("CSE499B", 1.5)]

CSE_TRAIL_ALGO = [("CSE401",3),("CSE417",3),("CSE418",3),("CSE426",3),("CSE473",3),("CSE491",3)]
CSE_TRAIL_SE   = [("CSE411",3),("CSE424",3),("CSE427",3),("CSE428",3),("CSE429",3),("CSE492",3)]
CSE_TRAIL_NET  = [("CSE422",3),("CSE438",3),("CSE482",3),("CSE485",3),("CSE486",3),("CSE493",3)]
CSE_TRAIL_AI   = [("CSE419",3),("CSE440",3),("CSE445",3),("CSE465",3),("CSE467",3),("CSE468",3),("CSE470",3),("CSE495",3)]
CSE_TRAIL_ARCH = [("CSE433",3),("CSE435",3),("CSE413",3),("CSE414",3),("CSE415",3),("CSE494",3)]
CSE_TRAIL_BIO  = [("CSE446",3),("CSE447",3),("CSE448",3),("CSE449",3),("CSE442",3),("CSE496",3)]
CSE_ALL_TRAILS = [CSE_TRAIL_ALGO, CSE_TRAIL_SE, CSE_TRAIL_NET, CSE_TRAIL_AI, CSE_TRAIL_ARCH, CSE_TRAIL_BIO]

CSE_OPEN_ELECTIVE_POOL = [("BUS101",3),("BUS201",3),("SOC201",3),("PSY101",3),("MIS101",3),("ENV101",3),("ECO201",3),("MKT101",3)]


# ═════════════════════════════════════════════════════════════════════════════
#  ARCH (B.Arch) COURSE CATALOG — 170 credits, 5-year program
# ═════════════════════════════════════════════════════════════════════════════

ARCH_UNIV_CORE = [
    ("ENG102", 3), ("ENG103", 3), ("ENG111", 3), ("BEN205", 3),
    ("PHI104", 3), ("HIS102", 3), ("HIS103", 3),
]
ARCH_UNIV_CHOICE = [
    [("ECO101", 3), ("ECO104", 3)],
    [("POL101", 3), ("POL104", 3)],
    [("SOC101", 3), ("ANT101", 3), ("GEO205", 3)],
]
ARCH_MATH_PHYS = [
    ("MAT116", 0), ("MAT120", 3), ("PHY107", 4), ("CEE110", 1), ("ENV107", 4),
]
ARCH_DESIGN_STUDIOS = [
    ("ARC101", 6), ("ARC102", 6), ("ARC201", 6), ("ARC202", 6),
    ("ARC301", 6), ("ARC302", 6), ("ARC401", 6), ("ARC402", 6),
    ("ARC501", 6),
]
ARCH_HISTORY_THEORY = [
    ("ARC111", 3), ("ARC211", 3), ("ARC212", 3), ("ARC311", 3), ("ARC411", 3),
]
ARCH_BUILDING_TECH = [
    ("ARC121", 3), ("ARC122", 3), ("ARC221", 3), ("ARC222", 3),
    ("ARC321", 3), ("ARC322", 3), ("ARC421", 3),
]
ARCH_VISUAL_COMM = [
    ("ARC131", 3), ("ARC132", 3), ("ARC231", 3),
]
ARCH_PROFESSIONAL = [
    ("ARC412", 3), ("ARC511", 3), ("ARC512", 2), ("ARC513", 3),
]

ARCH_ELECTIVE_POOL = [
    ("ARC431", 3), ("ARC432", 3), ("ARC433", 3), ("ARC434", 3),
    ("ARC435", 3), ("ARC436", 3), ("ARC437", 3), ("ARC438", 3), ("ARC439", 3),
]

ARCH_OPEN_ELECTIVE_POOL = [
    ("BUS101", 3), ("SOC201", 3), ("PSY101", 3), ("MIS101", 3),
    ("ECO201", 3), ("POL201", 3), ("HIS201", 3), ("MKT101", 3),
]


def deduplicate_courses(course_list):
    """Remove duplicate course codes, keep first occurrence."""
    seen = set()
    result = []
    for code, cr in course_list:
        if code not in seen:
            seen.add(code)
            result.append((code, cr))
    return result


def build_cse_transcript(scenario_id):
    """Build a CSE transcript as a list of (code, credits, grade, semester) rows."""
    rows = []
    added = set()

    # Determine student profile
    profiles = ["excellent", "good", "average", "struggling", "probation", "mixed"]

    # Scenario-based deterministic category assignment (10 scenarios)
    if scenario_id == 1:      # Freshman — excellent
        stage, profile = "early", "excellent"
        num_courses_target = random.randint(8, 14)
    elif scenario_id == 2:    # Freshman — struggling
        stage, profile = "early", "struggling"
        num_courses_target = random.randint(6, 12)
    elif scenario_id == 3:    # Sophomore — good
        stage, profile = "mid", "good"
        num_courses_target = random.randint(18, 26)
    elif scenario_id == 4:    # Sophomore — average
        stage, profile = "mid", "average"
        num_courses_target = random.randint(18, 26)
    elif scenario_id == 5:    # Junior — excellent
        stage, profile = "late", "excellent"
        num_courses_target = random.randint(30, 40)
    elif scenario_id == 6:    # Junior — good
        stage, profile = "late", "good"
        num_courses_target = random.randint(30, 40)
    elif scenario_id == 7:    # Graduated — excellent (summa cum laude range)
        stage, profile = "complete", "excellent"
        num_courses_target = 999
    elif scenario_id == 8:    # Graduated — average GPA
        stage, profile = "complete", "average"
        num_courses_target = 999
    elif scenario_id == 9:    # Academic probation
        stage, profile = "mid", "probation"
        num_courses_target = random.randint(12, 22)
    else:                     # Retake-heavy (triple retakes)
        stage, profile = "mid", "mixed"
        num_courses_target = random.randint(16, 26)

    # Build course sequence
    all_courses = []

    # 1) University Core (fixed)
    all_courses.extend(CSE_UNIV_CORE)

    # 2) Choice groups - pick one from each
    for group in CSE_UNIV_CHOICE:
        pick = random.choice(group)
        all_courses.append(pick)

    # 3) SEPS Core
    all_courses.extend(CSE_SEPS_CORE)

    # 4) Major Core
    all_courses.extend(CSE_MAJOR_CORE)

    # 5) Capstone
    all_courses.extend(CSE_CAPSTONE)

    # 6) Major electives: pick 2 from one trail + 1 from another
    primary_trail = random.choice(CSE_ALL_TRAILS)
    secondary_trail = random.choice([t for t in CSE_ALL_TRAILS if t is not primary_trail])
    primary_picks = random.sample(primary_trail, min(2, len(primary_trail)))
    secondary_picks = random.sample(secondary_trail, 1)
    all_courses.extend(primary_picks)
    all_courses.extend(secondary_picks)

    # 7) Open elective
    open_pick = random.choice(CSE_OPEN_ELECTIVE_POOL)
    all_courses.append(open_pick)

    # Deduplicate
    all_courses = deduplicate_courses(all_courses)

    # Trim to target
    if num_courses_target < len(all_courses):
        all_courses = all_courses[:num_courses_target]

    # Decide on retakes
    retake_count = 0
    if scenario_id == 10:
        retake_count = random.randint(3, 6)  # retake-heavy
    elif profile in ("struggling", "probation"):
        retake_count = random.randint(1, 4)
    elif profile == "average":
        retake_count = random.randint(0, 2)
    elif profile in ("good", "mixed"):
        retake_count = random.randint(0, 1)

    # Decide on special grades injection
    special_count = 0
    if profile == "probation":
        special_count = random.randint(1, 3)
    elif profile in ("struggling", "average"):
        special_count = random.randint(0, 2)
    elif profile == "mixed":
        special_count = random.randint(1, 2)

    # Build rows
    for idx, (code, cr) in enumerate(all_courses):
        if code in added:
            continue
        added.add(code)
        grade = pick_grade(profile)
        sem = assign_semester(idx, len(all_courses))
        rows.append((code, cr, grade, sem))

    # Inject special grades (replace some existing)
    if special_count > 0 and len(rows) > 3:
        special_indices = random.sample(range(min(len(rows), len(rows))), min(special_count, len(rows)))
        for si in special_indices:
            code, cr, _, sem = rows[si]
            sg = random.choice(["W", "I", "P", "TR"])
            if sg in ("P", "TR") and cr == 0:
                sg = "W"
            rows[si] = (code, cr, sg, sem)

    # Add retakes
    retake_candidates = [(i, r) for i, r in enumerate(rows) if r[2] in ("F", "D", "D+", "W")]
    if not retake_candidates and retake_count > 0:
        # Force some fails first
        forceable = [i for i, r in enumerate(rows) if r[2] not in ("W", "I", "P", "TR")]
        for fi in random.sample(forceable, min(retake_count, len(forceable))):
            code, cr, _, sem = rows[fi]
            rows[fi] = (code, cr, "F", sem)
            retake_candidates.append((fi, rows[fi]))

    retakes_added = 0
    for ri, (orig_idx, orig_row) in enumerate(retake_candidates):
        if retakes_added >= retake_count:
            break
        code, cr, old_grade, old_sem = orig_row
        # Find a later semester
        old_sem_idx = SEMESTERS.index(old_sem) if old_sem in SEMESTERS else 5
        new_sem_idx = min(old_sem_idx + random.randint(1, 3), len(SEMESTERS) - 1)
        new_sem = SEMESTERS[new_sem_idx]
        # Improved grade
        improved = pick_grade("good" if profile != "probation" else "average")
        rows.append((code, cr, improved, new_sem))
        retakes_added += 1

        # Chance of triple retake
        if scenario_id == 10 and random.random() < 0.3:
            triple_sem_idx = min(new_sem_idx + random.randint(1, 2), len(SEMESTERS) - 1)
            rows.append((code, cr, pick_grade("excellent"), SEMESTERS[triple_sem_idx]))

    # Sort by semester order
    sem_order = {s: i for i, s in enumerate(SEMESTERS)}
    rows.sort(key=lambda r: sem_order.get(r[3], 99))

    return rows


def build_arch_transcript(scenario_id):
    """Build an ARCH (B.Arch) transcript as a list of (code, credits, grade, semester) rows."""
    rows = []
    added = set()

    profiles = ["excellent", "good", "average", "struggling", "probation", "mixed"]

    # Scenario-based deterministic category assignment (10 scenarios)
    if scenario_id == 1:      # Freshman — excellent
        stage, profile = "early", "excellent"
        num_courses_target = random.randint(10, 18)
    elif scenario_id == 2:    # Freshman — struggling
        stage, profile = "early", "struggling"
        num_courses_target = random.randint(8, 15)
    elif scenario_id == 3:    # Sophomore — good
        stage, profile = "mid", "good"
        num_courses_target = random.randint(22, 34)
    elif scenario_id == 4:    # Sophomore — average
        stage, profile = "mid", "average"
        num_courses_target = random.randint(22, 34)
    elif scenario_id == 5:    # Junior — excellent
        stage, profile = "late", "excellent"
        num_courses_target = random.randint(36, 48)
    elif scenario_id == 6:    # Junior — good
        stage, profile = "late", "good"
        num_courses_target = random.randint(36, 48)
    elif scenario_id == 7:    # Graduated — excellent (summa cum laude range)
        stage, profile = "complete", "excellent"
        num_courses_target = 999
    elif scenario_id == 8:    # Graduated — average GPA
        stage, profile = "complete", "average"
        num_courses_target = 999
    elif scenario_id == 9:    # Academic probation
        stage, profile = "mid", "probation"
        num_courses_target = random.randint(14, 26)
    else:                     # Retake-heavy (triple retakes)
        stage, profile = "mid", "mixed"
        num_courses_target = random.randint(18, 30)

    all_courses = []

    # 1) University Core — fixed courses (7 courses, 21 cr)
    all_courses.extend(ARCH_UNIV_CORE)

    # 2) University Core — choice groups (pick 1 from each, 3 picks = 9 cr)
    for group in ARCH_UNIV_CHOICE:
        pick = random.choice(group)
        all_courses.append(pick)

    # 3) Math & Physical Sciences (5 courses, 12 cr)
    all_courses.extend(ARCH_MATH_PHYS)

    # 4) Design Studios (9 courses, 54 cr)
    all_courses.extend(ARCH_DESIGN_STUDIOS)

    # 5) History & Theory (5 courses, 15 cr)
    all_courses.extend(ARCH_HISTORY_THEORY)

    # 6) Building Technology (7 courses, 21 cr)
    all_courses.extend(ARCH_BUILDING_TECH)

    # 7) Visual Communication (3 courses, 9 cr)
    all_courses.extend(ARCH_VISUAL_COMM)

    # 8) Professional Practice & Research (4 courses, 11 cr)
    all_courses.extend(ARCH_PROFESSIONAL)

    # 9) Architecture Electives: pick 4 from pool (12 cr)
    arch_elec_picks = random.sample(ARCH_ELECTIVE_POOL, 4)
    all_courses.extend(arch_elec_picks)

    # 10) Open Electives: pick 2 (6 cr)
    open_picks = random.sample(ARCH_OPEN_ELECTIVE_POOL, 2)
    all_courses.extend(open_picks)

    # Deduplicate
    all_courses = deduplicate_courses(all_courses)

    # Trim
    if num_courses_target < len(all_courses):
        all_courses = all_courses[:num_courses_target]

    # Retakes
    retake_count = 0
    if scenario_id == 10:
        retake_count = random.randint(3, 6)  # retake-heavy
    elif profile in ("struggling", "probation"):
        retake_count = random.randint(1, 4)
    elif profile == "average":
        retake_count = random.randint(0, 2)
    elif profile in ("good", "mixed"):
        retake_count = random.randint(0, 1)

    special_count = 0
    if profile == "probation":
        special_count = random.randint(1, 3)
    elif profile in ("struggling", "average"):
        special_count = random.randint(0, 2)
    elif profile == "mixed":
        special_count = random.randint(1, 2)

    for idx, (code, cr) in enumerate(all_courses):
        if code in added:
            continue
        added.add(code)
        grade = pick_grade(profile)
        sem = assign_semester(idx, len(all_courses))
        rows.append((code, cr, grade, sem))

    # Special grades
    if special_count > 0 and len(rows) > 3:
        special_indices = random.sample(range(len(rows)), min(special_count, len(rows)))
        for si in special_indices:
            code, cr, _, sem = rows[si]
            sg = random.choice(["W", "I", "P", "TR"])
            if sg in ("P", "TR") and cr == 0:
                sg = "W"
            rows[si] = (code, cr, sg, sem)

    # Retakes
    retake_candidates = [(i, r) for i, r in enumerate(rows) if r[2] in ("F", "D", "D+", "W")]
    if not retake_candidates and retake_count > 0:
        forceable = [i for i, r in enumerate(rows) if r[2] not in ("W", "I", "P", "TR")]
        for fi in random.sample(forceable, min(retake_count, len(forceable))):
            code, cr, _, sem = rows[fi]
            rows[fi] = (code, cr, "F", sem)
            retake_candidates.append((fi, rows[fi]))

    retakes_added = 0
    for ri, (orig_idx, orig_row) in enumerate(retake_candidates):
        if retakes_added >= retake_count:
            break
        code, cr, old_grade, old_sem = orig_row
        old_sem_idx = SEMESTERS.index(old_sem) if old_sem in SEMESTERS else 5
        new_sem_idx = min(old_sem_idx + random.randint(1, 3), len(SEMESTERS) - 1)
        new_sem = SEMESTERS[new_sem_idx]
        improved = pick_grade("good" if profile != "probation" else "average")
        rows.append((code, cr, improved, new_sem))
        retakes_added += 1

        if scenario_id == 10 and random.random() < 0.3:
            triple_sem_idx = min(new_sem_idx + random.randint(1, 2), len(SEMESTERS) - 1)
            rows.append((code, cr, pick_grade("excellent"), SEMESTERS[triple_sem_idx]))

    sem_order = {s: i for i, s in enumerate(SEMESTERS)}
    rows.sort(key=lambda r: sem_order.get(r[3], 99))

    return rows


def write_csv(path, rows):
    """Write transcript rows to CSV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Course_Code", "Credits", "Grade", "Semester"])
        for code, cr, grade, sem in rows:
            # Format credits: int if whole number, else float
            cr_str = str(int(cr)) if cr == int(cr) else str(cr)
            writer.writerow([code, cr_str, grade, sem])


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    cse_dir = os.path.join(base, "data", "cse", "tests")
    arch_dir = os.path.join(base, "data", "arch", "tests")

    print("Generating 10 CSE test transcripts...")
    for i in range(1, 11):
        rows = build_cse_transcript(i)
        path = os.path.join(cse_dir, f"test_{i:02d}.csv")
        write_csv(path, rows)

    print("Generating 10 ARCH test transcripts...")
    for i in range(1, 11):
        rows = build_arch_transcript(i)
        path = os.path.join(arch_dir, f"test_{i:02d}.csv")
        write_csv(path, rows)

    print(f"\n✓ Done! 20 test files created:")
    print(f"  CSE:  {cse_dir}   (10 files)")
    print(f"  ARCH: {arch_dir}  (10 files)")

    # Print scenario summary
    print("\n── Scenario Distribution (per department) ──")
    print("  01  Freshman — excellent")
    print("  02  Freshman — struggling")
    print("  03  Sophomore — good")
    print("  04  Sophomore — average")
    print("  05  Junior — excellent")
    print("  06  Junior — good")
    print("  07  Graduated — excellent (summa cum laude)")
    print("  08  Graduated — average GPA")
    print("  09  Academic probation")
    print("  10  Retake-heavy (triple retakes)")


if __name__ == "__main__":
    main()
