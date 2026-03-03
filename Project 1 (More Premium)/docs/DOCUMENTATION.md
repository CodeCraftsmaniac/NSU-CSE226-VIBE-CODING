# NSU Degree Audit Engine — Complete Project Documentation

> **Course:** CSE226.1 — Vibe Coding (Spring 2026)
> **Project:** Project 1 — The Dept. Admin "Audit Core"
> **Instructor:** Dr. Nabeel Mohammed
> **Due Date:** February 24, 2026 (in-class demonstration)

---

## Table of Contents

1. [The Big Picture — What Is This?](#1-the-big-picture--what-is-this)
2. [How the Whole Project Is Organized](#2-how-the-whole-project-is-organized)
3. [How to Run Everything — Step by Step](#3-how-to-run-everything--step-by-step)
4. [The 4 Python Files — What Each One Does](#4-the-4-python-files--what-each-one-does)
5. [core.py — The Brain (Every Function Explained)](#5-corepy--the-brain-every-function-explained)
6. [credit_engine.py — Level 1 (Line by Line)](#6-credit_enginepy--level-1-line-by-line)
7. [cgpa_analyzer.py — Level 2 (Line by Line)](#7-cgpa_analyzerpy--level-2-line-by-line)
8. [degree_audit.py — Level 3 (Line by Line)](#8-degree_auditpy--level-3-line-by-line)
9. [The Knowledge Base — How Curriculum Data Works](#9-the-knowledge-base--how-curriculum-data-works)
10. [The CSV Files — Transcripts and Test Data](#10-the-csv-files--transcripts-and-test-data)
11. [The Batch Files — What They Are and Why](#11-the-batch-files--what-they-are-and-why)
12. [NSU Grading System — Every Rule Explained](#12-nsu-grading-system--every-rule-explained)
13. [How Retakes Work — The Best-Grade Logic](#13-how-retakes-work--the-best-grade-logic)
14. [How CGPA Is Calculated — The Math](#14-how-cgpa-is-calculated--the-math)
15. [How the Waiver System Works](#15-how-the-waiver-system-works)
16. [How the UI / Colors Work](#16-how-the-ui--colors-work)
17. [Every Edge Case and How It's Handled](#17-every-edge-case-and-how-its-handled)
18. [How to Change Things — Modification Guide](#18-how-to-change-things--modification-guide)
19. [What the Faculty Wants to See — Demo Guide](#19-what-the-faculty-wants-to-see--demo-guide)
20. [Every Question Faculty Might Ask — Q&A](#20-every-question-faculty-might-ask--qa)

---

## 1. The Big Picture — What Is This?

Imagine you're a **Department Admin at NSU**. A student walks in and says "Can I graduate?" You need to:

1. Look at their transcript (list of courses, grades, credits)
2. Figure out how many credits they actually earned (F = 0, W = excluded, etc.)
3. Calculate their CGPA
4. Check if they meet all graduation requirements (mandatory courses done? electives done? enough credits?)
5. Give a yes/no verdict

**This project automates all of that.** It's a command-line tool (no GUI, runs in terminal) that reads a CSV file (the transcript) and gives you a full analysis.

### The 3 Levels

The project is built in 3 levels, each building on the previous one:

| Level | File | What It Does | Think of it as... |
|-------|------|-------------|-------------------|
| **Level 1** | `credit_engine.py` | Reads transcript → counts credits | "How many credits does this student have?" |
| **Level 2** | `cgpa_analyzer.py` | Calculates CGPA + handles waivers | "What's their GPA and can they get a scholarship?" |
| **Level 3** | `degree_audit.py` | Full graduation check | "Can this student graduate? What's missing?" |

All 3 levels share a common file called `core.py` that has all the reusable code (the grading logic, the pretty printing, the CSV reading, etc.).

### Two Programs, Two Departments

The project spec requires us to audit **two programs from two different departments**:

| Program | Department | What it is |
|---------|-----------|-----------|
| **CSE** | ECE (Electrical & Computer Engineering) | Computer Science degree — 130 credits, 44 mandatory courses, 6 elective trails |
| **ARCH** | Architecture | Bachelor of Architecture — 170 credits, 47 mandatory courses, pick-4 architecture electives |

Each program has its own:
- Transcript CSV file (fake student data)
- Test CSV files (edge case data)
- Run scripts (batch files)

But they share the same Python code and knowledge base.

---

## 2. How the Whole Project Is Organized

```
CSE226_Project_01/
│
├── src/                              ← ALL the Python code lives here
│   ├── core.py                       The shared "brain" — 651 lines
│   ├── credit_engine.py              Level 1 script — 132 lines
│   ├── cgpa_analyzer.py              Level 2 script — 230 lines
│   └── degree_audit.py               Level 3 script — 400 lines
│
├── data/                             ← Student data (CSV files)
│   ├── cse/                          CSE department data
│   │   ├── transcript.csv            The "real" CSE student transcript (29 rows)
│   │   ├── test_L1.csv               Test file for Level 1 edge cases
│   │   ├── test_L2.csv               Test file for Level 2 CGPA math
│   │   └── test_retake.csv           Test file for retake scenarios
│   └── ARCH/                          ARCH department data
│       ├── transcript.csv            The "real" ARCH student transcript (30 rows)
│       ├── test_L1.csv               Test file for Level 1 edge cases
│       ├── test_L2.csv               Test file for Level 2 CGPA math
│       └── test_retake.csv           Test file for retake scenarios
│
├── scripts/                          ← Double-click .bat files to run demos
│   ├── cse/                          6 batch files for CSE
│   │   ├── run_level1.bat            Runs Level 1 with CSE transcript
│   │   ├── run_level2.bat            Runs Level 2 with CSE transcript
│   │   ├── run_level3.bat            Runs Level 3 with CSE transcript
│   │   ├── run_test_L1.bat           Runs Level 1 with test_L1.csv
│   │   ├── run_test_L2.bat           Runs Level 2 with test_L2.csv
│   │   └── run_test_retake.bat       Runs Level 3 with test_retake.csv
│   └── ARCH/                          6 batch files for ARCH
│       ├── run_level1.bat            Runs Level 1 with ARCH transcript
│       ├── run_level2.bat            Runs Level 2 with ARCH transcript
│       ├── run_level3.bat            Runs Level 3 with ARCH transcript
│       ├── run_test_L1.bat           Runs Level 1 with test_L1.csv
│       ├── run_test_L2.bat           Runs Level 2 with test_L2.csv
│       └── run_test_retake.bat       Runs Level 3 with test_retake.csv
│
├── docs/
│   ├── DOCUMENTATION.md              THIS FILE
│   └── CSE226_Proj_1.pdf             Original project specification from faculty
│
├── knowledge_base.md                 ← The curriculum data (what courses are required)
├── README.md                         ← Quick-start guide
└── .gitignore                        ← Tells git to ignore __pycache__/ etc.
```

**Total: 28 files** (4 Python + 1 knowledge base + 8 CSVs + 12 batch scripts + 2 docs + 1 README)

### Why this structure?

- **`src/`** — All code in one place. Easy to find.
- **`data/cse/` and `data/arch/`** — Each department has its own folder so transcripts don't mix.
- **`scripts/cse/` and `scripts/arch/`** — Faculty can just double-click a `.bat` file. No need to type commands.
- **`docs/`** — Documentation separate from code.
- **`knowledge_base.md`** at root — Both programs use one knowledge base file.

---

## 3. How to Run Everything — Step by Step

### Method 1: Double-Click (Easiest — Use This for Demo)

1. Open the `scripts/cse/` or `scripts/arch/` folder in File Explorer
2. Double-click any `.bat` file
3. A terminal window opens, shows the output, waits for you to press a key
4. Press any key to close

### Method 2: Terminal Commands

Open a terminal in the project root folder, then:

```bash
# ── CSE Department ──
python src/credit_engine.py data/cse/transcript.csv              # Level 1
python src/cgpa_analyzer.py data/cse/transcript.csv              # Level 2
python src/degree_audit.py data/cse/transcript.csv CSE knowledge_base.md  # Level 3

# ── ARCH Department ──
python src/credit_engine.py data/arch/transcript.csv 170          # Level 1
python src/cgpa_analyzer.py data/arch/transcript.csv              # Level 2
python src/degree_audit.py data/arch/transcript.csv ARCH knowledge_base.md  # Level 3

# ── Test Files ──
python src/credit_engine.py data/cse/test_L1.csv                 # L1 edge case test
python src/cgpa_analyzer.py data/cse/test_L2.csv                 # L2 CGPA math test
python src/degree_audit.py data/cse/test_retake.csv CSE knowledge_base.md  # Retake test
```

### What You Need

- **Python 3.10+** (we use 3.13)
- **No pip installs** — everything uses Python's built-in standard library
- **Modern terminal** — Windows Terminal or VS Code terminal (for colors to show properly)

---

## 4. The 4 Python Files — What Each One Does

### How they connect

```
credit_engine.py ──┐
                    ├──→ imports from ──→ core.py
cgpa_analyzer.py ──┤
                    │
degree_audit.py ───┘
```

All three scripts import functions from `core.py`. They don't import from each other. `core.py` is never run directly — it's a library.

### Quick summary

| File | Lines | Arguments | What it produces |
|------|-------|-----------|-----------------|
| `core.py` | 651 | (not run directly) | Shared functions: loading, grading, UI |
| `credit_engine.py` | 132 | `<transcript.csv>` | Credit tally report |
| `cgpa_analyzer.py` | 230 | `<transcript.csv>` | CGPA report + interactive waiver prompt |
| `degree_audit.py` | 400 | `<transcript.csv> <CSE\|ARCH> [knowledge_base.md]` | Full degree audit + graduation verdict |

---

## 5. core.py — The Brain (Every Function Explained)

This is the largest file (651 lines). Everything reusable lives here. Here's every piece:

### 5.1 Imports (Line 12)

```python
import csv, os, re, sys
from collections import OrderedDict
from datetime import datetime
```

- `csv` — reads CSV files
- `os` — file existence checks, enables Windows terminal colors
- `re` — regular expressions (for parsing the knowledge base Markdown)
- `sys` — exit on errors
- `OrderedDict` — keeps courses in the order they appear in the transcript
- `datetime` — timestamp in the footer

All standard library. Zero pip installs.

### 5.2 Windows Color Fix (Line 17)

```python
os.system("")
```

This one line enables "Virtual Terminal Processing" on Windows. Without it, you'd see raw `\033[...` codes instead of colors. It works by running an empty command which has the side effect of enabling ANSI escape sequences.

### 5.3 Color System — Class `C` (Lines 24-85)

The class `C` holds all color codes. Colors work by printing special "escape sequences" before text:

```python
print(f"{C.MINT}This text is mint green{C.RST}")
#       ↑ turns on color              ↑ resets back to normal
```

**How true-color works:** Normal terminals support 16 colors. We use "true-color" (24-bit RGB) which lets us pick any of 16 million colors:

```python
def _fg(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"
```

This creates a string like `\033[38;2;100;255;180m` which tells the terminal "use foreground color RGB(100, 255, 180)".

**The colors we use:**

| Name | RGB | What it's used for |
|------|-----|-------------------|
| `MINT` | (100, 255, 180) | Passed items, A/A- grades, success |
| `ROSE` | (255, 100, 130) | Failed items, F grade, errors |
| `GOLD` | (255, 215, 0) | Warnings, W/I grades, C+ grades |
| `SKY` | (135, 206, 250) | B grades, stats |
| `TEAL` | (0, 200, 180) | Borders, headers |
| `CORAL` | (255, 127, 80) | D grades |
| `LAVENDER` | (180, 160, 255) | Table headers, P/TR grades |
| `VIOLET` | (160, 100, 255) | Section gradients |

### 5.4 Box Drawing Characters — Class `Box` (Lines 90-101)

Unicode characters for drawing borders:

```
╔═══════╗   ← Double line (TL, H, TR, V, BL, BR) — used in verdict boxes
║       ║
╚═══════╝

┏━━━━━━━┓   ← Heavy line (TLH, HH, TRH, VH) — used in banner
┃       ┃
┗━━━━━━━┛

╭───────╮   ← Rounded (TLR, H2, TRR) — used in big number display
│       │
╰───────╯
```

### 5.5 Grade Point Mapping — `GRADE_POINTS` dict (Lines 107-113)

```python
GRADE_POINTS = {
    "A": 4.00, "A-": 3.70,
    "B+": 3.30, "B": 3.00, "B-": 2.70,
    "C+": 2.30, "C": 2.00, "C-": 1.70,
    "D+": 1.30, "D": 1.00,
    "F": 0.00,
}
```

This is NSU's official grading scale. Maps letter grades to their numeric grade point values.

**Important:** W, I, P, TR are NOT in this dict. They're in `NON_GPA_GRADES` because they don't have grade points.

### 5.6 Grade Sets (Lines 115-116)

```python
PASSING_GRADES = {"A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "P", "TR"}
NON_GPA_GRADES = {"W", "I", "P", "TR"}
```

- `PASSING_GRADES` — any grade that means "you passed" (D is the lowest passing grade)
- `NON_GPA_GRADES` — grades that should NOT be included in GPA math. Notice P and TR are in BOTH sets (they count as passing, but don't affect GPA).

### 5.7 Gradient Functions (Lines 122-135)

```python
def _gradient_text(text, r1, g1, b1, r2, g2, b2):
```

Takes a string like "CREDIT TALLY ENGINE" and colors each character with a smoothly interpolated color from (r1,g1,b1) to (r2,g2,b2). Character 1 gets the start color, the last character gets the end color, and everything in between is linearly interpolated.

Used for the banner title, section headers, and the progress bar.

### 5.8 UI Functions — The Visual Components

Here's every UI function and exactly what it prints:

#### `banner(title, subtitle)` — The Hero Banner
The big box at the top of every output. Has gradient borders (teal→cyan→blue) and the title in gradient text. Example output:
```
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ┃                                                 ┃
  ┃              CREDIT TALLY ENGINE                ┃
  ┃          Level 1  ·  NSU Degree Audit           ┃
  ┃                                                 ┃
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### `section(title, icon)` — Section Headers
Prints a horizontal line, then the title with an emoji icon, then another line. Used to separate the report into logical parts.

#### `info_line(label, value)` — Key-Value Rows
```
    Source File ·····················  data/cse/transcript.csv
    Total Entries (raw) ············  29
```
The dots are generated dynamically to fill the space.

#### `stat_card(label, value, color, icon)` — Single Stats
```
    ◆ Attempted Credits          63.0
    ✓ Earned Credits             63.0
```

#### `table_header(cols, widths)` and `table_row(values, widths, colors)` — Data Tables
```
   #     Course     Grade   Credits   Earned    Status
   ───── ────────── ─────── ───────── ───────── ────────────────
     1.  ENG102     A       3.0       3.0       EARNED
     2.  MAT116     B       0.0       —         0-CREDIT
```
You pass column names and widths, and it formats everything with proper coloring.

#### `progress_bar(current, total)` — Gradient Progress Bar
```
  ████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░  48.5%
```
The filled portion has a color gradient. Green = good (≥100%), orange = medium, red = low.

#### `big_number(label, value)` — CGPA Display Box
```
  ╭──────────────────────────────────╮
  │         Cumulative GPA           │
  │              3.22                │
  ╰──────────────────────────────────╯
```

#### `verdict_box(text, passed)` — Pass/Fail Verdict
```
  ╔════════════════════════════════════════════╗
  ║      ✗  NOT ELIGIBLE TO GRADUATE          ║
  ╚════════════════════════════════════════════╝
```
Green background for pass, red for fail.

#### `check_item(label, passed, detail)` — Checklist Line
```
  ✓  CGPA ≥ 2.00                              3.22
  ✗  All mandatory courses completed           22/44
```

#### `recommendation(text)` — Gold Bullet Point
```
    ▸  Complete 22 missing mandatory course(s)
```

#### `footer()` — Timestamp Footer
```
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    NSU Degree Audit Engine  ·  CSE226 Project 1  ·  Feb 21, 2026  18:19
```

### 5.9 Data Functions — Loading & Processing

#### `load_transcript(csv_path)` — Reads a CSV File

**Input:** Path to a CSV file with columns `Course_Code`, `Credits`, `Grade` (and optionally `Semester`)

**What it does:**
1. Opens the CSV with `utf-8-sig` encoding (handles Excel BOM)
2. Normalizes headers to lowercase with underscores (`Course_Code` → `course_code`)
3. For each row: extracts code, grade, credits
4. Skips rows with empty course codes
5. Returns a list of dictionaries: `[{"course_code": "ENG102", "grade": "A", "credits": 3.0}, ...]`

**Important detail:** It reads `credits` OR `credit` (handles both spellings). If the credit value can't be parsed as a number, it defaults to 0.0.

#### `resolve_retakes(rows)` — Keeps Only Best Grade

**Input:** List of rows from `load_transcript()`

**Returns:** `(resolved_list, retake_history_dict)`

**How it works:**
1. Uses an `OrderedDict` called `seen` to track each course
2. When a course code appears for the second time → it's a retake
3. Records ALL grades in `history` dict (e.g., `{"CSE115": ["F", "C+", "A-"]}`)
4. Keeps only the row with the BEST grade (using `_grade_rank()`)
5. Returns the deduplicated list + the history

**The `_grade_rank()` function:**
```python
A = 14.0, A- = 13.7, B+ = 13.3, ... D = 11.0, F = 10.0
P/TR = 5, W = 1, I = 0
```
Higher number = better grade. GPA grades get +10 so they always rank above non-GPA grades.

#### `parse_knowledge_base(md_path)` — Reads Curriculum Data

**Input:** Path to `knowledge_base.md`

**Returns:** A big nested dictionary:
```python
{
  "programs": {
    "CSE": {
      "full_name": "Computer Science & Engineering (CSE)",
      "total_credits": 130,
      "mandatory": ["ENG102", "ENG103", ...],        # 44 course codes
      "choice_groups": [                               # ECO101|ECO104 etc.
        {"options": ["ECO101", "ECO104"], "credits": 3, "name": "..."},
      ],
      "sections": [                                    # Regular courses
        {"code": "MAT116", "credits": 0, "name": "Pre-Calculus"},
      ],
      "elective_trails": {                             # CSE only
        "Algorithms and Computation Trail": [
          {"code": "CSE401", "credits": 3, "name": "..."},
        ],
      },
      "elective_pools": [],                            # ARCH only (pool-based)
    },
    "ARCH": { ... }
  },
  "grading": {"A": 4.0, "A-": 3.7, ...}
}
```

**How the parsing works:**
1. Splits the Markdown by `## [Program: ...]` headers
2. For each program:
   - Finds `Total Credits Required: 130`
   - Finds the `### Mandatory Courses` section → parses comma-separated course codes
   - Scans every `### Section` and `#### Section` header
   - Parses course lines like `- CSE115,3,Programming Language I`
   - Lines with `|` (like `ECO101|ECO104`) → become **choice groups**
   - Sections ending in "Trail" → become **elective trails** (CSE only)
   - Sections matching "Pick N" → become **elective pools** (ARCH only (pool-based))
   - Everything else → goes into `sections` list

#### `classify_credit(grade, credits)` — Decides If a Course Earns Credits

**Input:** A grade string and credit count

**Returns:** `(earned_credits, status_label, color)`

**The decision tree:**

```
Is grade W, I, P, or TR?
  ├── Yes → Is it P or TR with credits > 0?
  │   ├── Yes → EARNED (P/TR) — credits earned but not in GPA
  │   └── No  → EXCLUDED — W or I, 0 credits
  └── No →
      Is grade F?
      ├── Yes → FAILED — 0 credits earned
      └── No →
          Are credits 0?
          ├── Yes → 0-CREDIT — lab co-requisite
          └── No →
              Is grade in passing grades?
              ├── Yes → EARNED — full credits
              └── No  → UNKNOWN
```

#### `compute_cgpa(rows)` — The CGPA Math

**Input:** Resolved rows (after retake deduplication)

**Returns:** `(cgpa, total_quality_points, total_gpa_credits, total_earned_credits)`

**The algorithm:**
```
For each course:
  If grade is W/I/P/TR:
    If P or TR with credits > 0: add to earned (but NOT gpa)
    Skip to next course
  Get grade_point from GRADE_POINTS dict
  If credits > 0:
    quality_points += grade_point × credits
    gpa_credits += credits
    If grade is NOT F:
      earned_credits += credits
CGPA = quality_points ÷ gpa_credits
```

**Key insight:** F grade courses ARE counted in `gpa_credits` (they drag down CGPA) but are NOT counted in `earned_credits` (you didn't pass).

#### `compute_waiver(cgpa, credits_earned)` — Tuition Scholarship Check

```python
if earned < 30:  return 0%, "Not eligible (need ≥ 30 credits)"
if cgpa >= 3.97: return 100%, "Chancellor's Award"
if cgpa >= 3.75: return 50%, "Vice-Chancellor's Scholarship"
if cgpa >= 3.50: return 25%, "Dean's Scholarship"
else:            return 0%, "No waiver"
```

#### `require_file(path, description)` — File Existence Check

If the file doesn't exist, prints a styled red error and exits. Prevents confusing tracebacks.

---

## 6. credit_engine.py — Level 1 (Line by Line)

**What it answers:** "How many credits has this student earned?"

### The Flow

1. **Parse arguments** — needs 1 argument: the CSV path. If missing, prints usage and exits.
2. **`require_file(csv_path)`** — checks the file exists.
3. **`load_transcript(csv_path)`** — reads all rows from CSV.
4. **`resolve_retakes(raw_rows)`** — deduplicates retakes (keeps best grade).
5. **Print banner** — "CREDIT TALLY ENGINE"
6. **Print transcript overview** — source file, total entries, unique courses, retakes count.
7. **Course-by-course table:**
   - For each resolved course, calls `classify_credit()` to get status
   - Tracks totals: attempted credits, earned credits, earned/failed/excluded/zero-credit counts
   - Prints a colored table row for each course
8. **Credit summary cards** — shows all the totals
9. **Retake history** (if any retakes exist):
   - Shows grade journey: `F → C+ → A-`
   - Note at bottom: "Only the best grade is used for CGPA"
10. **Degree progress** — progress bar toward 130 credits
11. **Footer** with timestamp

### What the output looks like (sections)

```
📋  Transcript Overview
📊  Course-by-Course Breakdown  (the big table)
📈  Credit Summary
🔄  Retake History
🎓  Degree Credit Progress
```

---

## 7. cgpa_analyzer.py — Level 2 (Line by Line)

**What it answers:** "What's the student's CGPA? Are they eligible for a scholarship?"

### The Flow

1. **Parse arguments** — 1 argument: CSV path.
2. **Load → Resolve → Compute CGPA** — same loading pipeline as Level 1, but also calls `compute_cgpa()`.
3. **Print banner** — "CGPA & WAIVER HANDLER"
4. **Transcript overview** — same as Level 1.
5. **Grade detail table:**
   - Shows grade points and quality points per course
   - W/I/P/TR courses show "—" for grade points (not applicable)
   - Quality Points = Grade Point × Credits (e.g., A at 3 credits = 4.00 × 3 = 12.00)
6. **CGPA computation:**
   - Shows total quality points, GPA-eligible credits, earned credits
   - Big number box with the CGPA value
   - Color: mint if ≥3.50, gold if ≥2.00, rose if <2.00
7. **Academic standing:**

   | CGPA | Standing | Stars |
   |------|----------|-------|
   | ≥ 3.90 | Summa Cum Laude | ★★★★ |
   | ≥ 3.60 | Magna Cum Laude | ★★★ |
   | ≥ 3.30 | Cum Laude | ★★ |
   | ≥ 2.00 | Good Standing | ★ |
   | < 2.00 | ACADEMIC PROBATION | ⚠ |

   If CGPA < 2.00, prints a red warning about probation.

8. **Interactive course waiver handler (THIS IS THE INTERACTIVE PART):**
   - Prints a prompt asking the admin if any courses should be waived
   - Waits for keyboard input: type course codes separated by commas (e.g., `ENG102, BUS112`)
   - Or press Enter to skip
   - For each code:
     - If already completed → shows "⚠ already completed, waiver not needed"
     - If not completed → shows "✓ waiver applied"
   - Waived courses satisfy requirements but DON'T earn credits or affect CGPA

9. **Retake impact analysis:**
   - Shows the grade point change for each retake
   - E.g., `F → B+ = +3.30 ↑ improved`

10. **Tuition waiver eligibility:**
    - Shows if student qualifies for scholarship
    - Shows the ladder: 3.50→25%, 3.75→50%, 3.97→100%
    - Filled/empty circles show which thresholds are met

### What the output looks like (sections)

```
📋  Transcript Overview
📊  Grade Detail Table
🧮  CGPA Computation (big number box)
🏛️  Academic Standing
📝  Course Waiver Handler (INTERACTIVE — waits for input)
🔄  Retake Impact Analysis
💰  Tuition Waiver Eligibility (scholarship ladder)
```

---

## 8. degree_audit.py — Level 3 (Line by Line)

**What it answers:** "Can this student graduate? If not, what's missing?"

### The Flow

1. **Parse arguments** — needs 2-3 arguments: CSV path, program code (CSE or ARCH), optionally knowledge base path (defaults to `knowledge_base.md`).
2. **Load transcript + Resolve retakes + Compute CGPA** — same as Level 2.
3. **`parse_knowledge_base()`** — reads the curriculum Markdown file.
4. **Build completed set** — set of course codes where grade is passing.
5. **Print banner** — "DEGREE AUDIT · CSE" or "DEGREE AUDIT · ARCH"
6. **Student overview** — file, program name, credits required vs earned, CGPA.

7. **AUDIT 1 — Mandatory Courses:**
   - Goes through every mandatory course code from the knowledge base
   - For each: checks if it's in the completed set → "✓ Completed" or "✗ Missing"
   - Shows completed/total count and progress bar
   - Lists all missing courses at the bottom

8. **AUDIT 2 — Choice Groups:**
   - Each choice group is like "take ECO101 OR ECO104" (either one satisfies)
   - Shows each group with → which option the student took, or "None taken"
   - Counts how many groups are satisfied

9. **AUDIT 3 — Electives (different per program):**

   **For CSE:**
   - **Major Electives (9 credits):** There are 6 "trails" (Algorithms, Software Engineering, Networks, AI, Computer Architecture, Bioinformatics). Each trail has ~6 courses. Student must take ≥2 courses from one trail + ≥1 from another = minimum 9 credits.
   - **Open Electives (3 credits):** Any course that isn't already part of the mandatory/trail/choice-group requirements.

   **For ARCH:**
   - **architecture electives (12 credits):** There's a pool of 9 architecture elective courses. Student must pick any 4 (3 credits each = 12 credits).
   - **Free Electives (6 credits):** Any 2 additional courses from any department (3 credits each).

10. **AUDIT 4 — Retake History:** Shows grade journey for any retaken courses.

11. **AUDIT 5 — Credit Progress:** Earned vs. required (130), with progress bar.

12. **AUDIT 6 — Academic Standing & Waiver:** Same standing levels + tuition waiver check.

13. **THE VERDICT — 5 Criteria Graduation Check:**

    | # | Criterion | What it checks |
    |---|-----------|---------------|
    | 1 | CGPA ≥ 2.00 | Minimum GPA to graduate |
    | 2 | All mandatory completed | Every required course passed |
    | 3 | All choice groups satisfied | Pick-one groups all fulfilled |
    | 4 | Electives met | Trail/pool rules + credit minimums |
    | 5 | Credits ≥ 130 | Total earned credits enough |

    All 5 pass = **"✓ ELIGIBLE TO GRADUATE"** (green box)
    Any fail = **"✗ NOT ELIGIBLE TO GRADUATE"** (red box) + specific recommendations

### What the output looks like (sections)

```
👤  Student Overview
📋  Mandatory Course Audit (44 courses for CSE / 23 for ARCH)
🔀  Choice-Group Audit
🎯  CSE Major Elective Audit / ⚖️ architecture elective Audit
📂  Open/Free Electives
🔄  Retake History
📊  Credit Progress
🏛️  Academic Standing & Waiver
⚖️  GRADUATION ELIGIBILITY VERDICT (the 5-criteria checklist + verdict box)
```

---

## 9. The Knowledge Base — How Curriculum Data Works

### What is it?

`knowledge_base.md` is a Markdown file (286 lines) that contains the complete curriculum for both CSE and ARCH programs. It's the "brain" that Level 3 audits against. The Python code NEVER hardcodes course lists — it reads them from this file.

### Structure

```markdown
## Grading Scale (NSU Standard)
(grade table)

## [Program: Computer Science & Engineering (CSE)]
- Total Credits Required: 130

### University Core (34 Credits)
#### Languages (12 Credits)
- ENG102,3,Introduction to Composition
- ENG103,3,Intermediate Composition

### Mandatory Courses (All Must Be Completed)
- ENG102,ENG103,ENG111,BEN205
- CSE115,CSE115L
...

## [Program: Bachelor of Laws (ARCH)]
(same structure for ARCH)
```

### How the parser reads it

1. **Program detection:** Splits on `## [Program: ...]` headers. If name contains "CSE" → key is `CSE`. If "ARCH" or "LAW" → key is `ARCH`.

2. **Course lines:** Matches pattern `- CODE,CREDITS,NAME`. Example: `- ENG102,3,Introduction to Composition` → `{code: "ENG102", credits: 3, name: "Introduction to Composition"}`

3. **Choice groups:** Lines with `|` in the code, like `- ECO101|ECO104,3,Intro to Micro OR Macro` → `{options: ["ECO101", "ECO104"], credits: 3}`

4. **Trails:** Sections whose title ends with "Trail" → courses go into `elective_trails` dict.

5. **Elective pools:** Sections matching "Pick N" → courses go into `elective_pools` list.

6. **Mandatory courses:** Parsed from the `### Mandatory Courses` section — comma-separated codes per line.

### How to add a new program

1. Add a new section in `knowledge_base.md`:
   ```markdown
   ## [Program: My New Program (MNP)]
   - Total Credits Required: 120

   ### Some Course Category
   - MNP101,3,Some Course

   ### Mandatory Courses
   - MNP101,MNP102
   ```

2. In `degree_audit.py`, you'd need to add an `elif program == "MNP":` block for its elective logic (or generalize the existing logic).

3. That's it. The parser handles everything else automatically.

---

## 10. The CSV Files — Transcripts and Test Data

### CSV Format

Every transcript has these columns:

```csv
Course_Code,Credits,Grade,Semester
ENG102,3,A,Spring 2023
```

- `Course_Code` — course identifier (e.g., `CSE115`, `LAW301`)
- `Credits` — number of credits (0 for labs, 1-4 for regular courses)
- `Grade` — letter grade (A, A-, B+, ..., F, W, I, P, TR)
- `Semester` — when taken (not used by the code, just for reference)

The code only uses `Course_Code`, `Credits`, and `Grade`. `Semester` is ignored.

### The "Real" Transcripts

**`data/cse/transcript.csv`** — A CSE student who:
- Has 29 entries, 26 unique courses (3 retakes)
- Retakes: HIS103 (F→B+), CSE173 (W→B), CSE225 (F→B+)
- Has 63 earned credits out of 130 required
- CGPA ≈ 3.22 (Good Standing)
- Missing 22 out of 44 mandatory courses
- Result: NOT ELIGIBLE TO GRADUATE

**`data/arch/transcript.csv`** — An ARCH student who:
- Has 29 entries, 29 unique courses (no retakes)
- Has 97 earned credits out of 130 required
- CGPA ≈ 3.29 (Good Standing)
- Missing 6 out of 23 mandatory courses
- All 7 choice groups satisfied
- Result: NOT ELIGIBLE TO GRADUATE

### The Test Files — WHY They Exist

The project specification explicitly requires test data files for each level. These are small, carefully designed CSV files that prove the code handles edge cases correctly. Think of them as "proof" — when faculty asks "how do you know your F handling works?", you run the test file and show them.

#### `test_L1.csv` — Tests Level 1 Credit Classification

This file has one example of EVERY type of grade:

| Row | Course | Grade | Credits | Expected Result |
|-----|--------|-------|---------|----------------|
| 1 | ENG102 | A | 3 | EARNED (normal pass) |
| 2 | CSE115 | A- | 3 | EARNED (another pass) |
| 3 | CSE115L | A | 0 | 0-CREDIT (lab, 0 credits) |
| 4 | PHY107 | **F** | 3 | FAILED (0 credits earned) |
| 5 | CSE173 | **W** | 3 | EXCLUDED (withdrawal) |
| 6 | HIS103 | **I** | 3 | EXCLUDED (incomplete) |
| 7 | MAT250 | **P** | 3 | EARNED (P/TR) (pass, non-GPA) |
| 8 | CSE225 | **TR** | 3 | EARNED (P/TR) (transfer, non-GPA) |
| 9 | BIO105 | B+ | 0 | 0-CREDIT (0-credit with passing grade) |
| 10 | ENG103 | **D** | 3 | EARNED (lowest passing grade) |

By running Level 1 with this file, you can verify that each grade type is classified correctly.

#### `test_L2.csv` — Tests Level 2 CGPA Math

This file is designed so you can manually verify the CGPA calculation:
- Contains W, I, P, TR entries that must be EXCLUDED from GPA math
- Contains a retake (MAT130: F→C+) to prove the best grade is used
- You can add up the quality points and credits by hand and confirm the CGPA matches

#### `test_retake.csv` — Tests Level 3 Retake Logic

This file has extreme retake scenarios:

| Course | Attempts | Grades | Best Grade Kept |
|--------|----------|--------|----------------|
| CSE115 | 3 (triple!) | F → C+ → A- | **A-** (best of all 3) |
| CSE115L | 2 | F → B | **B** |
| PHY107 | 2 | D → C+ | **C+** |
| HIS103 | 3 | W → F → B+ | **B+** (W and F both dropped) |
| CSE225 | 2 | F → B+ | **B+** |

This proves the best-grade logic works even with:
- Triple retakes (3 attempts)
- W followed by F followed by pass
- Multiple retakes in the same transcript

---

## 11. The Batch Files — What They Are and Why

### What is a .bat file?

A `.bat` (batch) file is a Windows script. When you double-click it, Windows runs the commands inside it in a terminal window. It's like a shortcut that types commands for you.

### The Two Types

There are **12 batch files total** — 6 per department, split into two categories:

#### Type 1: Main Run Scripts (3 per department)

These run the program with the **real transcript** (`transcript.csv`):

```bat
@echo off
title NSU Degree Audit - Level 1 - CSE Credit Tally
cd /d "%~dp0..\.."
python src\credit_engine.py data\cse\transcript.csv
echo.
pause
```

What each line does:
- `@echo off` — hides the commands themselves (only shows output)
- `title ...` — sets the window title bar text
- `cd /d "%~dp0..\.."` — navigates to the project root (the `.bat` is in `scripts/cse/`, so `..\..\` goes up 2 levels to the project root)
- `python src\credit_engine.py data\cse\transcript.csv` — runs the actual Python script
- `echo.` — prints a blank line
- `pause` — shows "Press any key to continue..." so the window stays open after the script finishes

#### Type 2: Test Run Scripts (3 per department)

These run the program with **test data** to prove edge cases work:

```bat
@echo off
title NSU Degree Audit - Level 3 TEST - CSE Retake Scenario
cd /d "%~dp0..\.."
echo ============================================================
echo   TEST: Level 3 Retake Scenario
echo   File: data/cse/test_retake.csv
echo   Tests: Triple retake, W then retake, F then retake
echo ============================================================
echo.
python src\degree_audit.py data\cse\test_retake.csv CSE knowledge_base.md
echo.
pause
```

The test scripts have an extra header banner that explains what's being tested and which file is being used, so anyone running it immediately knows the purpose.

### The Complete List

| Folder | File | What it runs | Data file used |
|--------|------|-------------|---------------|
| `scripts/cse/` | `run_level1.bat` | Level 1 (credit tally) | `data/cse/transcript.csv` |
| | `run_level2.bat` | Level 2 (CGPA + waiver) | `data/cse/transcript.csv` |
| | `run_level3.bat` | Level 3 (degree audit) | `data/cse/transcript.csv` |
| | `run_test_L1.bat` | Level 1 test | `data/cse/test_L1.csv` |
| | `run_test_L2.bat` | Level 2 test | `data/cse/test_L2.csv` |
| | `run_test_retake.bat` | Level 3 test | `data/cse/test_retake.csv` |
| `scripts/arch/` | `run_level1.bat` | Level 1 (credit tally) | `data/arch/transcript.csv` |
| | `run_level2.bat` | Level 2 (CGPA + waiver) | `data/arch/transcript.csv` |
| | `run_level3.bat` | Level 3 (degree audit) | `data/arch/transcript.csv` |
| | `run_test_L1.bat` | Level 1 test | `data/arch/test_L1.csv` |
| | `run_test_L2.bat` | Level 2 test | `data/arch/test_L2.csv` |
| | `run_test_retake.bat` | Level 3 test | `data/arch/test_retake.csv` |

### Why 12 files?

- 3 levels × 2 departments = 6 main scripts
- 3 test files × 2 departments = 6 test scripts
- Total = 12

---

## 12. NSU Grading System — Every Rule Explained

All grading data is verified against NSU's official grading policy page.

### The Grade Scale

| Score Range | Letter | Grade Points | What It Means |
|-------------|--------|-------------|---------------|
| 93+ | A | 4.00 | Excellent |
| 90-92 | A- | 3.70 | |
| 87-89 | B+ | 3.30 | |
| 83-86 | B | 3.00 | Good |
| 80-82 | B- | 2.70 | |
| 77-79 | C+ | 2.30 | |
| 73-76 | C | 2.00 | Average |
| 70-72 | C- | 1.70 | |
| 67-69 | D+ | 1.30 | |
| 60-66 | D | 1.00 | Poor (lowest pass) |
| Below 60 | F | 0.00 | Failure |

### Special Grades (Non-GPA)

| Grade | Full Name | Earns Credits? | In GPA? | What We Do |
|-------|-----------|---------------|---------|-----------|
| W | Withdrawal | No | No | Completely excluded |
| I | Incomplete | No | No | Completely excluded |
| P | Pass | Yes | No | Credits counted toward total, NOT in GPA math |
| TR | Transfer | Yes | No | Credits counted toward total, NOT in GPA math |

### F Grade — The Tricky One

F is different from W/I because:
- F **IS** included in GPA calculation (it adds 0 quality points but increases the denominator → drags CGPA down)
- F earns **0 credits** (you failed, you didn't pass)
- F stays in GPA until the student retakes the course and gets a better grade

### 0-Credit Courses

Some courses have 0 credits (like lab co-requisites: CSE225L, CSE231L). These:
- Must be completed (appear in mandatory list)
- Don't count toward earned credits
- Don't affect GPA (0 × grade_point = 0 quality points, and 0 credits don't add to denominator)

---

## 13. How Retakes Work — The Best-Grade Logic

### NSU's Official Policy

> "When a student retakes a course, the actual grade will be recorded. In case of a retake course, only the **best grade** will be used to calculate the CGPA."

### How Our Code Handles It

When the same course code appears multiple times in the transcript, the `resolve_retakes()` function:

1. Records all attempts in order (for history display)
2. Compares each new attempt against the current best using `_grade_rank()`
3. Keeps the row with the highest-ranked grade
4. Returns the deduplicated list (one row per course, the best grade)

### Example: CSE115 taken 3 times

```csv
CSE115,3,F,Spring 2023     ← Attempt 1: F (rank 10.0)
CSE115,3,C+,Summer 2023    ← Attempt 2: C+ (rank 12.3) — better than F, replaces
CSE115,3,A-,Fall 2023      ← Attempt 3: A- (rank 13.7) — better than C+, replaces
```

Result: Only `CSE115, A-, 3` is kept for CGPA calculation.
History shown as: `F → C+ → A-`

### Why "best" instead of "last"?

NSU's policy says **best**, not last. If a student retakes a course and gets a WORSE grade, the original better grade is kept. Example:

```csv
PHY107,3,B+,Spring 2023    ← Attempt 1: B+ (rank 13.3)
PHY107,3,C,Fall 2023       ← Attempt 2: C (rank 12.0) — WORSE, original B+ kept
```

Result: B+ is kept, C is recorded in history but doesn't replace B+.

---

## 14. How CGPA Is Calculated — The Math

### The Formula (from NSU official)

$$\text{CGPA} = \frac{\sum (\text{Grade Point} \times \text{Credits})}{\sum \text{GPA-Eligible Credits}}$$

Where:
- **GPA-Eligible Credits** = only courses with grades A through F (NOT W, I, P, TR)
- **Quality Points** = Grade Point × Credits for each course

### Worked Example (CSE test_L2.csv)

| Course | Grade | Credits | Grade Point | Quality Points | In GPA? |
|--------|-------|---------|-------------|---------------|---------|
| ENG102 | A | 3 | 4.00 | 12.00 | Yes |
| MAT120 | B+ | 3 | 3.30 | 9.90 | Yes |
| CSE115 | A- | 3 | 3.70 | 11.10 | Yes |
| CSE115L | A | 0 | 4.00 | 0.00 | Yes (but 0 cr) |
| PHY107 | C+ | 3 | 2.30 | 6.90 | Yes |
| PHY107L | B | 1 | 3.00 | 3.00 | Yes |
| HIS103 | W | 3 | — | — | **NO (excluded)** |
| CSE173 | I | 3 | — | — | **NO (excluded)** |
| MAT250 | P | 3 | — | — | **NO (credits only)** |
| CSE225 | TR | 3 | — | — | **NO (credits only)** |
| ENG103 | B | 3 | 3.00 | 9.00 | Yes |
| MAT130 | C+ | 3 | 2.30 | 6.90 | Yes (best of F→C+) |
| PHI104 | A- | 3 | 3.70 | 11.10 | Yes |
| BEN205 | B | 3 | 3.00 | 9.00 | Yes |

**Total Quality Points** = 12.00 + 9.90 + 11.10 + 0.00 + 6.90 + 3.00 + 9.00 + 6.90 + 11.10 + 9.00 = **78.90**
**Total GPA Credits** = 3 + 3 + 3 + 0 + 3 + 1 + 3 + 3 + 3 + 3 = **25.0**
**CGPA** = 78.90 ÷ 25.0 = **3.156** → displays as **3.16**

Note: W, I, P, TR are completely excluded from both numerator and denominator. The F from MAT130's first attempt is replaced by the best grade (C+) before CGPA calculation.

---

## 15. How the Waiver System Works

### Course Waivers (Level 2 Interactive Feature)

This is the **interactive part** the project spec requires. When Level 2 runs, it pauses and asks:

```
  ? Waivers granted for any courses?
    Enter course codes separated by commas (e.g. ENG102, BUS112)
    Or press Enter to skip:
  ▸ _
```

The admin types course codes (or presses Enter to skip).

**What a waiver does:**
- The course is marked as "requirement satisfied"
- The course does NOT earn credits
- The course does NOT affect CGPA in any way
- It only satisfies the "you need to take this course" requirement

**Example:** If a student transferred from another university and had already taken an English course, the admin might waive ENG102. The student doesn't get 3 more credits, but the ENG102 requirement is considered fulfilled.

**Edge case:** If the student already passed the course (e.g., they got a B in ENG102), and the admin tries to waive it, the system shows: "⚠ ENG102 — already completed, waiver not needed."

### Tuition Waiver (Scholarship — Automatic Check)

This is a completely different "waiver" — it's a tuition discount based on CGPA:

| CGPA | Discount | Name |
|------|----------|------|
| ≥ 3.97 | 100% | Chancellor's Award |
| ≥ 3.75 | 50% | Vice-Chancellor's Scholarship |
| ≥ 3.50 | 25% | Dean's Scholarship |
| < 3.50 | 0% | No waiver |

**Additional requirement:** You need at least 30 completed credits to be eligible for any scholarship. A freshman with a 4.0 GPA but only 15 credits doesn't qualify yet.

---

## 16. How the UI / Colors Work

### True Color (24-bit RGB)

Normal ANSI supports 16 colors (red, green, blue, etc.). We use **true-color** which lets us specify exact RGB values. This is what makes the gradients possible.

```python
# This tells the terminal: "set foreground to RGB(100, 255, 180)"
print("\033[38;2;100;255;180m This is mint green \033[0m")
#      ↑ escape sequence                        ↑ reset
```

The `\033` is the "escape" character. `[38;2;R;G;B` sets foreground. `[48;2;R;G;B` sets background.

### How Gradients Work

The `_gradient_text()` function colors EACH CHARACTER individually:

```python
def _gradient_text(text, r1, g1, b1, r2, g2, b2):
    for i, ch in enumerate(text):
        # Linear interpolation between start color and end color
        r = int(r1 + (r2 - r1) * i / n)
        g = int(g1 + (g2 - g1) * i / n)
        b = int(b1 + (b2 - b1) * i / n)
        out.append(f"\033[38;2;{r};{g};{b}m{ch}")
```

For "CREDIT TALLY ENGINE" (19 chars):
- Char 1 gets color (100, 220, 255) (light cyan)
- Char 19 gets color (200, 160, 255) (lavender)
- Chars 2-18 are smoothly interpolated between

### How the Progress Bar Colors Work

The progress bar changes color based on percentage:
- ≥100% → green gradient (you're done)
- ≥60% → yellow-green gradient (getting there)
- ≥30% → orange gradient (needs work)
- <30% → red gradient (just starting)

### Windows Compatibility

The `os.system("")` call on line 17 is critical. Without it, Windows CMD would show raw escape codes like `[38;2;100;255;180m` instead of colors. This trick enables "Virtual Terminal Processing" mode.

For best results, use **Windows Terminal** (the modern one) or **VS Code's integrated terminal**. The old `cmd.exe` works too (because of the `os.system("")` trick) but colors may look slightly different.

---

## 17. Every Edge Case and How It's Handled

| Edge Case | What Happens | Where in Code |
|-----------|-------------|---------------|
| Student retakes a course | Best grade kept, all attempts in history | `core.resolve_retakes()` |
| Triple retake (3 attempts) | Still works — best of all 3 kept | `_grade_rank()` comparison |
| F grade | 0 credits earned, but 0.00 in GPA denominator (drags down CGPA) | `compute_cgpa()` and `classify_credit()` |
| W (Withdrawal) | Excluded from everything — no credits, not in GPA | `NON_GPA_GRADES` set |
| I (Incomplete) | Same as W — excluded from everything | `NON_GPA_GRADES` set |
| P (Pass) | Credits earned, NOT in GPA math | `classify_credit()` → "EARNED (P/TR)" |
| TR (Transfer) | Same as P — credits earned, NOT in GPA math | `classify_credit()` → "EARNED (P/TR)" |
| 0-credit lab (e.g., CSE225L) | Classified as "0-CREDIT", must be completed but doesn't add credits | `classify_credit()` → credits == 0 check |
| Empty course code in CSV | Skipped during loading | `load_transcript()` → `if not code: continue` |
| Missing file | Styled red error message, exits cleanly | `require_file()` |
| Unknown program code | Red error + exit if not "CSE" or "ARCH" | `degree_audit.py` → program check |
| CSV with BOM | Handled — uses `utf-8-sig` encoding | `load_transcript()` |
| Header spelling variations | `credits` or `credit` both work | `r.get("credits", r.get("credit", "0"))` |
| CGPA exactly 2.00 | "Good Standing" (threshold is ≥ 2.00) | Standing check uses `>=` |
| Credits < 30 | No tuition waiver regardless of CGPA | `compute_waiver()` |
| Waiver for already-passed course | Warning shown: "already completed, waiver not needed" | `cgpa_analyzer.py` waiver section |
| Student already has 130+ credits | Progress bar shows 100%, "✓ Credit requirement met" | `progress_bar()` clips at 1.0 |
| Retake where later grade is WORSE | Original better grade is kept (best, not last) | `_grade_rank()` comparison with `>` |

---

## 18. How to Change Things — Modification Guide

### Change the grading scale

Edit `GRADE_POINTS` dictionary in `core.py` (line 105):

```python
GRADE_POINTS = {
    "A": 4.00, "A-": 3.70,
    ...
}
```

Add or remove grades here. Also update `PASSING_GRADES` and `NON_GPA_GRADES` if needed.

### Add a new program (e.g., BBA)

1. **Add to `knowledge_base.md`:**
   ```markdown
   ## [Program: Bachelor of Business Administration (BBA)]
   - Total Credits Required: 124

   ### Core Courses
   - BUS101,3,Introduction to Business
   ...

   ### Mandatory Courses
   - BUS101,BUS102,...
   ```

2. **Update `degree_audit.py`:**
   - Change the program check from `if program not in ("CSE", "ARCH")` to include `"BBA"`
   - Add an `elif program == "BBA":` block in the elective audit section (or make the existing logic generic)

3. **Create data files:**
   - `data/bba/transcript.csv`
   - `data/bba/test_L1.csv`, etc.

4. **Create run scripts:**
   - `scripts/bba/run_level1.bat`, etc.

### Change the credit requirement (from 130 to something else)

Edit `knowledge_base.md` — change `Total Credits Required: 130` to the new number. The code reads this value; it's not hardcoded.

### Change the tuition waiver thresholds

Edit `compute_waiver()` in `core.py` (line 637):

```python
if cgpa >= 3.97: return 100, "Chancellor's Award"
elif cgpa >= 3.75: return 50, "Vice-Chancellor's Scholarship"
elif cgpa >= 3.50: return 25, "Dean's Scholarship"
```

### Change colors

Edit the `C` class in `core.py`. Colors use RGB values:

```python
MINT = _fg(100, 255, 180)    # Change these 3 numbers
```

### Add a new column to the table

In any level script, modify the `cols` and `widths` lists:

```python
cols   = ["#", "Course", "Grade", "Credits", "Earned", "Status"]
widths = [5,   10,       7,       9,         9,        16]
```

Add your column name to `cols` and its width to `widths`. Then add the corresponding value in the `table_row()` call.

### Add a new elective trail (CSE)

Add to `knowledge_base.md`:

```markdown
#### My New Trail
- CSE500,3,Some New Course
- CSE501,3,Another Course
```

The parser automatically picks up sections ending in "Trail". No code changes needed.

### Change the progress bar width

In any script's `progress_bar()` call, change the `width` parameter:

```python
progress_bar(total_earned, 130, width=50)   # 50 chars wide
progress_bar(total_earned, 130, width=30)   # narrower
```

### Change the minimum credits for waiver eligibility

In `compute_waiver()` in `core.py`:

```python
if credits_earned < 30:    # Change 30 to whatever
```

---

## 19. What the Faculty Wants to See — Demo Guide

### What the Faculty Is Looking For

Based on the project spec, the faculty will check:

1. **Does it work?** — Does it actually run and produce correct output?
2. **Is there a knowledge base?** — Is the curriculum stored separately from the code (not hardcoded)?
3. **Does Level 1 handle edge cases?** — F, W, I, P, TR, 0-credit all classified correctly?
4. **Does CGPA exclude non-GPA grades?** — W/I/P/TR must NOT affect GPA math
5. **Is there an interactive waiver prompt?** — Level 2 must pause and ask for input
6. **Does Level 3 do a real audit?** — Missing courses, choice groups, electives, verdict
7. **Two programs from different departments?** — Not two programs from the same department
8. **Standard library only?** — No pip installs, no third-party libraries
9. **Test files provided?** — test_L1.csv, test_L2.csv, test_retake.csv exist and prove edge cases

### Recommended Demo Order (6 runs, ~5 minutes)

**CSE Department first:**

1. **Double-click `scripts/cse/run_level1.bat`**
   - Point out: the course table with color-coded grades
   - Point out: 3 retakes shown in history (HIS103 F→B+, CSE173 W→B, CSE225 F→B+)
   - Point out: 0-credit labs (MAT116, CSE225L, CSE231L)
   - Point out: progress bar at 48.5%

2. **Double-click `scripts/cse/run_level2.bat`**
   - Point out: the CGPA calculation (3.22)
   - Point out: the quality points per course
   - **Interactive moment:** When it asks about waivers:
     - Type `CSE499A` and press Enter → shows "✓ waiver applied"
     - OR type `ENG102` → shows "⚠ already completed"
     - OR just press Enter to skip
   - Point out: scholarship ladder (need 3.50+ for Dean's)

3. **Double-click `scripts/cse/run_level3.bat`**
   - Point out: 22/44 mandatory courses completed
   - Point out: choice groups (ECO101 taken, SOC101 taken, etc.)
   - Point out: the 5-criteria verdict at the bottom
   - Point out: recommendations (complete 22 missing courses, earn 67 more credits)

**ARCH Department second:**

4. **Double-click `scripts/arch/run_level1.bat`**
   - Point out: different department (Law), no retakes
   - Point out: 97 credits earned (more than CSE student)

5. **Double-click `scripts/arch/run_level2.bat`**
   - Point out: CGPA 3.29 — Good Standing
   - Interactive waiver prompt

6. **Double-click `scripts/arch/run_level3.bat`**
   - Point out: different audit structure (architecture electives instead of trails)
   - Point out: 7/7 choice groups satisfied
   - Point out: still NOT eligible (6 missing mandatory, not enough credits)

### If Faculty Asks "Show Me the Test Files"

Run the test scripts:

- `scripts/cse/run_test_L1.bat` → shows every grade type classified correctly
- `scripts/cse/run_test_L2.bat` → shows CGPA math with W/I/P/TR excluded
- `scripts/cse/run_test_retake.bat` → shows triple retake (F→C+→A-) resolved correctly

### Tips for Demo

- **Maximize the terminal window** — output is 76 characters wide
- **Use Windows Terminal or VS Code terminal** — best color rendering
- **For the waiver prompt in Level 2:** type a course code to show it works, or press Enter to skip. Both are valid demonstrations.
- **Have this documentation open** in case you need to explain something

---

## 20. Every Question Faculty Might Ask — Q&A

**Q: How many files in total?**
A: 28 files — 4 Python source, 1 knowledge base, 8 CSV data files (2 real transcripts + 6 test files), 12 batch scripts (6 main runs + 6 test runs), 2 docs, 1 README.

**Q: How many total runs to demo everything?**
A: 12 runs — 6 main runs (3 levels × 2 departments) + 6 test runs. Each has a one-click `.bat` file.

**Q: How many lines of code?**
A: ~1,413 total Python lines — core.py (651), credit_engine.py (132), cgpa_analyzer.py (230), degree_audit.py (400).

**Q: Did you use any external libraries?**
A: No. Standard library only: csv, os, re, sys, collections.OrderedDict, datetime.datetime.

**Q: How does your grading system work?**
A: NSU's official scale — A=4.00 through F=0.00. W and I are excluded from everything. P and TR earn credits but aren't in GPA.

**Q: How are retakes handled?**
A: Best grade is used (per NSU official policy), not the last grade. If a student gets B+ first and C second, the B+ is kept.

**Q: What if CGPA is below 2.00?**
A: The system flags "ACADEMIC PROBATION" in Level 2, and criterion #1 fails in Level 3's graduation verdict.

**Q: How does the interactive waiver work?**
A: Level 2 pauses and asks the admin to type course codes. Waived courses satisfy requirements but don't earn credits or affect CGPA.

**Q: What is the knowledge base?**
A: A Markdown file (`knowledge_base.md`) with the full curriculum for both programs — mandatory courses, choice groups, elective trails/pools, credit requirements. The code reads from this file; nothing is hardcoded.

**Q: Can you add a new program?**
A: Yes — add a section to `knowledge_base.md` with the right format, create a transcript CSV, and add an elective handling block in `degree_audit.py`.

**Q: How is the data structured?**
A: Transcripts are CSV files (course_code, credits, grade). The knowledge base is structured Markdown. No database needed.

**Q: Why two different departments?**
A: The spec requires programs from different departments. CSE is in ECE (Engineering), ARCH is in Law.

**Q: How does the graduation verdict work?**
A: 5 criteria must ALL pass: (1) CGPA ≥ 2.00, (2) all mandatory courses completed, (3) all choice groups satisfied, (4) elective requirements met, (5) total credits ≥ 130. If any fails, the student gets "NOT ELIGIBLE" with specific recommendations.

**Q: Why are there test files?**
A: The project spec requires them. test_L1.csv proves credit classification works for every grade type. test_L2.csv proves CGPA math doesn't break with non-GPA entries. test_retake.csv proves the best-grade retake logic works for complex scenarios (triple retakes, W→F→pass).

**Q: What happens if I feed a different CSV?**
A: It works — the code is generic. Any CSV with `Course_Code`, `Credits`, `Grade` columns will be processed. The knowledge base determines which courses are "mandatory" etc.

**Q: How do the colors work?**
A: True-color ANSI escape sequences (24-bit RGB). Each character can have its own color, which enables the gradient effects on banners and progress bars.

**Q: Why `.bat` files instead of just running commands?**
A: Faculty can just double-click — no need to open a terminal, navigate to the folder, or remember command syntax. The `.bat` file handles all of that.

**Q: What's the GitHub repo?**
A: `https://github.com/CodeCraftsmaniac/CSE226_Project_01` — main branch, all files committed.
