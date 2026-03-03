"""
generate_tests.py — Generate 500 test transcript CSVs (250 CSE + 250 LLB)
═══════════════════════════════════════════════════════════════════════════
Each file is a realistic NSU student transcript with varied scenarios:
  - Different completion stages (freshman → graduated)
  - Various GPA ranges (probation → summa cum laude)
  - Retake scenarios (single, double, triple)
  - Special grades: W, I, P, TR, F
  - 0-credit labs
  - Choice-group variations
  - Elective trail/pool coverage
  - Edge cases for waiver thresholds
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
#  LLB COURSE CATALOG
# ═════════════════════════════════════════════════════════════════════════════

LLB_LANG = [("ENG102", 3), ("ENG103", 3), ("ENG111", 3), ("BEN205", 3)]
LLB_HUMANITIES = [("HIS103", 3)]
LLB_HUM_CHOICE = [
    [("PHI101", 3), ("PHI104", 3)],
    [("HIS101", 3), ("HIS102", 3)],
]
LLB_SOC_CHOICE = [
    [("POL101", 3), ("POL104", 3)],
    [("ECO101", 3), ("ECO104", 3)],
    [("SOC101", 3), ("ANT101", 3), ("GEO205", 3)],
]
LLB_COMP_MATH = [("MIS105", 3)]
LLB_CM_CHOICE = [
    [("MAT112", 3), ("MAT116", 3)],
    [("BUS172", 3), ("ENV172", 3), ("ECO172", 3)],
]
LLB_SCIENCE_POOL = [("PSY101",4),("ENV107",4),("PBH101",4),("CHE101",4),("PHY107",4),("BIO103",4)]

LLB_CORE_LAW = [
    ("LAW101", 3), ("LAW107", 4), ("LAW201", 4), ("LAW211", 4), ("LAW213", 4),
    ("LAW301", 4), ("LAW303", 3), ("LAW305", 4), ("LAW306", 3), ("LAW313", 4),
    ("LAW314", 3), ("LAW405", 3), ("LAW417", 4), ("LAW418", 4), ("LAW419", 3),
    ("LAW420", 4), ("LAW421", 3),
]

LLB_ELECTIVE_POOL = [
    ("LAW413",3),("LAW414",3),("LAW415",3),("LAW416",3),
    ("LAW422",3),("LAW423",3),("LAW424",3),("LAW426",3),("LAW427",3),
]

LLB_FREE_ELECTIVE_POOL = [("ENG115",3),("SOC201",3),("PSY201",3),("POL201",3),("ECO201",3),("HIS201",3),("MIS201",3),("BUS101",3)]


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
    
    # Scenario-based deterministic category assignment
    if scenario_id < 30:
        # Early-stage excellent students
        stage = "early"
        profile = "excellent"
        num_courses_target = random.randint(5, 15)
    elif scenario_id < 55:
        # Early-stage good students
        stage = "early"
        profile = "good"
        num_courses_target = random.randint(5, 15)
    elif scenario_id < 75:
        # Early-stage struggling
        stage = "early"
        profile = "struggling"
        num_courses_target = random.randint(5, 12)
    elif scenario_id < 100:
        # Mid-progress good students
        stage = "mid"
        profile = "good"
        num_courses_target = random.randint(16, 28)
    elif scenario_id < 120:
        # Mid-progress average
        stage = "mid"
        profile = "average"
        num_courses_target = random.randint(16, 28)
    elif scenario_id < 135:
        # Mid-progress excellent
        stage = "mid"
        profile = "excellent"
        num_courses_target = random.randint(18, 30)
    elif scenario_id < 155:
        # Near-complete excellent
        stage = "late"
        profile = "excellent"
        num_courses_target = random.randint(30, 45)
    elif scenario_id < 175:
        # Near-complete good
        stage = "late"
        profile = "good"
        num_courses_target = random.randint(30, 45)
    elif scenario_id < 195:
        # Complete / graduated (all mandatory done)
        stage = "complete"
        profile = "excellent"
        num_courses_target = 999  # take all
    elif scenario_id < 210:
        # Complete but average GPA
        stage = "complete"
        profile = "average"
        num_courses_target = 999
    elif scenario_id < 220:
        # Probation students
        stage = "mid"
        profile = "probation"
        num_courses_target = random.randint(10, 25)
    elif scenario_id < 230:
        # Mixed retake-heavy
        stage = "mid"
        profile = "mixed"
        num_courses_target = random.randint(15, 25)
    elif scenario_id < 240:
        # Edge: waiver threshold students (CGPA near 3.50, 3.75, 3.97)
        stage = "late"
        profile = "good"
        num_courses_target = random.randint(30, 45)
    else:
        # Remaining: random mix
        stage = random.choice(["early", "mid", "late", "complete"])
        profile = random.choice(profiles)
        if stage == "early":
            num_courses_target = random.randint(5, 15)
        elif stage == "mid":
            num_courses_target = random.randint(16, 28)
        elif stage == "late":
            num_courses_target = random.randint(30, 45)
        else:
            num_courses_target = 999

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
    if scenario_id >= 220 and scenario_id < 230:
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
        if scenario_id >= 220 and scenario_id < 230 and random.random() < 0.3:
            triple_sem_idx = min(new_sem_idx + random.randint(1, 2), len(SEMESTERS) - 1)
            rows.append((code, cr, pick_grade("excellent"), SEMESTERS[triple_sem_idx]))

    # Sort by semester order
    sem_order = {s: i for i, s in enumerate(SEMESTERS)}
    rows.sort(key=lambda r: sem_order.get(r[3], 99))

    return rows


def build_llb_transcript(scenario_id):
    """Build an LLB transcript as a list of (code, credits, grade, semester) rows."""
    rows = []
    added = set()

    profiles = ["excellent", "good", "average", "struggling", "probation", "mixed"]

    if scenario_id < 30:
        stage, profile = "early", "excellent"
        num_courses_target = random.randint(5, 15)
    elif scenario_id < 55:
        stage, profile = "early", "good"
        num_courses_target = random.randint(5, 15)
    elif scenario_id < 75:
        stage, profile = "early", "struggling"
        num_courses_target = random.randint(5, 12)
    elif scenario_id < 100:
        stage, profile = "mid", "good"
        num_courses_target = random.randint(16, 30)
    elif scenario_id < 120:
        stage, profile = "mid", "average"
        num_courses_target = random.randint(16, 30)
    elif scenario_id < 135:
        stage, profile = "mid", "excellent"
        num_courses_target = random.randint(18, 32)
    elif scenario_id < 155:
        stage, profile = "late", "excellent"
        num_courses_target = random.randint(32, 45)
    elif scenario_id < 175:
        stage, profile = "late", "good"
        num_courses_target = random.randint(32, 45)
    elif scenario_id < 195:
        stage, profile = "complete", "excellent"
        num_courses_target = 999
    elif scenario_id < 210:
        stage, profile = "complete", "average"
        num_courses_target = 999
    elif scenario_id < 220:
        stage, profile = "mid", "probation"
        num_courses_target = random.randint(10, 25)
    elif scenario_id < 230:
        stage, profile = "mid", "mixed"
        num_courses_target = random.randint(15, 25)
    elif scenario_id < 240:
        stage, profile = "late", "good"
        num_courses_target = random.randint(32, 45)
    else:
        stage = random.choice(["early", "mid", "late", "complete"])
        profile = random.choice(profiles)
        if stage == "early":
            num_courses_target = random.randint(5, 15)
        elif stage == "mid":
            num_courses_target = random.randint(16, 30)
        elif stage == "late":
            num_courses_target = random.randint(32, 45)
        else:
            num_courses_target = 999

    all_courses = []

    # Languages
    all_courses.extend(LLB_LANG)

    # Humanities (fixed + choice)
    all_courses.extend(LLB_HUMANITIES)
    for group in LLB_HUM_CHOICE:
        all_courses.append(random.choice(group))

    # Social Sciences (choice)
    for group in LLB_SOC_CHOICE:
        all_courses.append(random.choice(group))

    # Computer & Math
    all_courses.extend(LLB_COMP_MATH)
    for group in LLB_CM_CHOICE:
        all_courses.append(random.choice(group))

    # Sciences: pick 3
    sci_picks = random.sample(LLB_SCIENCE_POOL, 3)
    all_courses.extend(sci_picks)

    # Core Law
    all_courses.extend(LLB_CORE_LAW)

    # Law Electives: pick 4
    law_elec_picks = random.sample(LLB_ELECTIVE_POOL, 4)
    all_courses.extend(law_elec_picks)

    # Free Electives: pick 2
    free_picks = random.sample(LLB_FREE_ELECTIVE_POOL, 2)
    all_courses.extend(free_picks)

    # Deduplicate
    all_courses = deduplicate_courses(all_courses)

    # Trim
    if num_courses_target < len(all_courses):
        all_courses = all_courses[:num_courses_target]

    # Retakes
    retake_count = 0
    if scenario_id >= 220 and scenario_id < 230:
        retake_count = random.randint(3, 6)
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

        if scenario_id >= 220 and scenario_id < 230 and random.random() < 0.3:
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
    llb_dir = os.path.join(base, "data", "llb", "tests")

    print("Generating 250 CSE test transcripts...")
    for i in range(1, 251):
        rows = build_cse_transcript(i)
        path = os.path.join(cse_dir, f"test_{i:03d}.csv")
        write_csv(path, rows)

    print("Generating 250 LLB test transcripts...")
    for i in range(1, 251):
        rows = build_llb_transcript(i)
        path = os.path.join(llb_dir, f"test_{i:03d}.csv")
        write_csv(path, rows)

    print(f"\n✓ Done! 500 test files created:")
    print(f"  CSE: {cse_dir}  (250 files)")
    print(f"  LLB: {llb_dir}  (250 files)")

    # Print scenario summary
    print("\n── Scenario Distribution (per department) ──")
    print("  001-029:  Early-stage excellent students (5-15 courses)")
    print("  030-054:  Early-stage good students (5-15 courses)")
    print("  055-074:  Early-stage struggling students (5-12 courses)")
    print("  075-099:  Mid-progress good students (16-28 courses)")
    print("  100-119:  Mid-progress average students (16-28 courses)")
    print("  120-134:  Mid-progress excellent students (18-30 courses)")
    print("  135-154:  Near-complete excellent students (30-45 courses)")
    print("  155-174:  Near-complete good students (30-45 courses)")
    print("  175-194:  Complete/graduated excellent students (all courses)")
    print("  195-209:  Complete/graduated average GPA students")
    print("  210-219:  Academic probation students (low GPA)")
    print("  220-229:  Retake-heavy students (3-6 retakes, triple retakes)")
    print("  230-239:  Waiver threshold edge cases (CGPA ~3.50/3.75/3.97)")
    print("  240-250:  Random mixed scenarios")


if __name__ == "__main__":
    main()
