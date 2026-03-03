<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0e1a,30:0d1b2e,60:0f2942,100:1F6FEB&height=220&section=header&text=NSU%20Degree%20Audit%20Engine&fontSize=50&fontColor=FFFFFF&fontAlignY=38&fontStyle=bold&desc=CSE226%20Project%201%20%E2%80%A2%20Score%20100%20out%20of%20100%20%E2%80%A2%20CSE%20%2B%20LLB&descSize=16&descAlignY=58&descColor=7DD3FC&animation=fadeIn&stroke=1F6FEB&strokeWidth=1" width="100%" alt="header"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/CSE226-Project%201-1F6FEB?style=for-the-badge&logo=python&logoColor=white" alt="CSE226"/>&nbsp;
  <img src="https://img.shields.io/badge/Score-100%20out%20of%20100-2EA043?style=for-the-badge&logo=checkmarx&logoColor=white" alt="Score"/>&nbsp;
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>&nbsp;
  <img src="https://img.shields.io/badge/Spring%202026-NSU-003366?style=for-the-badge&logo=googlescholar&logoColor=white" alt="NSU"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Programs-CSE%20%2B%20LLB-58A6FF?style=flat-square" alt="Programs"/>&nbsp;
  <img src="https://img.shields.io/badge/Levels-3%20(Credit%20%7C%20CGPA%20%7C%20Audit)-BC8CFF?style=flat-square" alt="Levels"/>&nbsp;
  <img src="https://img.shields.io/badge/Standard%20Library-Only-2EA043?style=flat-square&logo=python&logoColor=white" alt="StdLib"/>&nbsp;
  <img src="https://img.shields.io/badge/Demo-One%20Click%20.bat-D29922?style=flat-square" alt="Demo"/>
</p>

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:0d1b2e,100:1F3A6E&height=40&text=%20%20%20ABOUT%20%20%20&fontColor=7DD3FC&fontSize=14&fontAlignY=68" width="60%" alt="About"/>
</p>

<br/>

<table align="center" width="90%">
<tr><td>

A **Python CLI tool** that reads student transcripts and performs **credit tallying**, **CGPA computation with waiver handling**, and a **full degree audit** with a graduation eligibility verdict.

Covers **two programs from two different departments**:
- **CSE** &mdash; Computer Science &amp; Engineering (ECE, SEPS)
- **LLB** &mdash; Bachelor of Laws (Law, SHSS)

</td></tr>
</table>

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:1a0a2e,100:4C1D95&height=40&text=%20%20%20QUICK%20START%20%20%20&fontColor=E9D5FF&fontSize=14&fontAlignY=68" width="60%" alt="Quick Start"/>
</p>

<br/>

<p align="center">Each department has one-click <code>.bat</code> run scripts inside <code>scripts/</code>. Just <strong>double-click</strong> any file:</p>

<table align="center" width="80%">
<thead>
<tr>
<th align="center" colspan="2"><img src="https://img.shields.io/badge/CSE-Computer%20Science%20%26%20Engineering-1F6FEB?style=flat-square" alt="CSE"/></th>
</tr>
<tr><th align="left">File</th><th align="left">What It Shows</th></tr>
</thead>
<tbody>
<tr><td><code>scripts/cse/run_level1.bat</code></td><td>Level 1 &mdash; Credit Tally</td></tr>
<tr><td><code>scripts/cse/run_level2.bat</code></td><td>Level 2 &mdash; CGPA &amp; Waiver (interactive)</td></tr>
<tr><td><code>scripts/cse/run_level3.bat</code></td><td>Level 3 &mdash; Full Degree Audit + Graduation Verdict</td></tr>
</tbody>
</table>

<br/>

<table align="center" width="80%">
<thead>
<tr>
<th align="center" colspan="2"><img src="https://img.shields.io/badge/LLB-Bachelor%20of%20Laws-D29922?style=flat-square" alt="LLB"/></th>
</tr>
<tr><th align="left">File</th><th align="left">What It Shows</th></tr>
</thead>
<tbody>
<tr><td><code>scripts/llb/run_level1.bat</code></td><td>Level 1 &mdash; Credit Tally</td></tr>
<tr><td><code>scripts/llb/run_level2.bat</code></td><td>Level 2 &mdash; CGPA &amp; Waiver (interactive)</td></tr>
<tr><td><code>scripts/llb/run_level3.bat</code></td><td>Level 3 &mdash; Full Degree Audit + Graduation Verdict</td></tr>
</tbody>
</table>

<p align="center"><sub>Demo order: CSE Level 1 -> 2 -> 3, then LLB Level 1 -> 2 -> 3</sub></p>

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:0d2e1a,100:064E3B&height=40&text=%20%20%20TERMINAL%20COMMANDS%20%20%20&fontColor=6EE7B7&fontSize=14&fontAlignY=68" width="60%" alt="Terminal"/>
</p>

<br/>

```bash
# CSE student
python src/credit_engine.py data/cse/transcript.csv
python src/cgpa_analyzer.py data/cse/transcript.csv
python src/degree_audit.py  data/cse/transcript.csv CSE knowledge_base.md

# LLB student
python src/credit_engine.py data/llb/transcript.csv
python src/cgpa_analyzer.py data/llb/transcript.csv
python src/degree_audit.py  data/llb/transcript.csv LLB knowledge_base.md
```

<p align="center">
  <img src="https://img.shields.io/badge/Requires-Python%203.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>&nbsp;
  <img src="https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-2EA043?style=flat-square" alt="StdLib"/>
</p>

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:2e1a0d,100:7C2D12&height=40&text=%20%20%20WHAT%20EACH%20LEVEL%20DOES%20%20%20&fontColor=FED7AA&fontSize=14&fontAlignY=68" width="60%" alt="Levels"/>
</p>

<br/>

<table align="center" width="90%">
<tr>
<td align="center" width="33%">
<img src="https://img.shields.io/badge/Level%201-Credit%20Tally-1F6FEB?style=for-the-badge" alt="L1"/>
<br/><br/>
<sub>Reads transcript &rarr; resolves retakes (best grade) &rarr; classifies credits &rarr; course-by-course table with grade colors &rarr; retake history &rarr; progress bar toward 130 credits.</sub>
</td>
<td align="center" width="33%">
<img src="https://img.shields.io/badge/Level%202-CGPA%20%26%20Waiver-BC8CFF?style=for-the-badge" alt="L2"/>
<br/><br/>
<sub>Computes CGPA with quality points &rarr; big CGPA display &rarr; <strong>interactive course waiver prompt</strong> &rarr; academic standing &rarr; retake impact analysis &rarr; tuition waiver eligibility ladder.</sub>
</td>
<td align="center" width="33%">
<img src="https://img.shields.io/badge/Level%203-Degree%20Audit-2EA043?style=for-the-badge" alt="L3"/>
<br/><br/>
<sub>Full audit against knowledge base &rarr; mandatory course checklist &rarr; choice group satisfaction &rarr; elective trails (CSE) / elective pool (LLB) &rarr; credit progress &rarr; <strong>5-criteria graduation verdict</strong> with recommendations.</sub>
</td>
</tr>
</table>

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:0d1b2e,100:164E63&height=40&text=%20%20%20PROGRAMS%20COVERED%20%20%20&fontColor=A5F3FC&fontSize=14&fontAlignY=68" width="60%" alt="Programs"/>
</p>

<br/>

<table align="center" width="80%">
<thead>
<tr>
<th align="center">Program</th>
<th align="center">Department</th>
<th align="center">School</th>
<th align="center">Total Credits</th>
</tr>
</thead>
<tbody>
<tr>
<td align="center"><img src="https://img.shields.io/badge/CSE-Computer%20Science%20%26%20Eng-1F6FEB?style=flat-square" alt="CSE"/></td>
<td align="center">ECE</td>
<td align="center">SEPS</td>
<td align="center"><strong>130</strong></td>
</tr>
<tr>
<td align="center"><img src="https://img.shields.io/badge/LLB-Bachelor%20of%20Laws-D29922?style=flat-square" alt="LLB"/></td>
<td align="center">Law</td>
<td align="center">SHSS</td>
<td align="center"><strong>130</strong></td>
</tr>
</tbody>
</table>

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:1a0d2e,100:581C87&height=40&text=%20%20%20NSU%20GRADING%20SYSTEM%20%20%20&fontColor=E9D5FF&fontSize=14&fontAlignY=68" width="60%" alt="Grading"/>
</p>

<p align="center"><sub>Verified against <a href="https://www.northsouth.edu/academic/grading-policy.html">NSU official grading policy</a></sub></p>

<br/>

<table align="center" width="60%">
<thead>
<tr><th align="center">Grade</th><th align="center">Points</th><th align="center">Grade</th><th align="center">Points</th></tr>
</thead>
<tbody>
<tr><td align="center">A</td><td align="center">4.00</td><td align="center">C</td><td align="center">2.00</td></tr>
<tr><td align="center">A-</td><td align="center">3.70</td><td align="center">C-</td><td align="center">1.70</td></tr>
<tr><td align="center">B+</td><td align="center">3.30</td><td align="center">D+</td><td align="center">1.30</td></tr>
<tr><td align="center">B</td><td align="center">3.00</td><td align="center">D</td><td align="center">1.00</td></tr>
<tr><td align="center">B-</td><td align="center">2.70</td><td align="center">F</td><td align="center">0.00</td></tr>
<tr><td align="center">C+</td><td align="center">2.30</td><td align="center"></td><td align="center"></td></tr>
</tbody>
</table>

<br/>

<table align="center" width="75%">
<tr><td>

- **Retakes:** Best grade used for CGPA (per NSU official policy)
- **F:** 0 credits earned, included in GPA calculation
- **W/I:** Excluded from GPA and credits
- **P/TR:** Credits earned, excluded from GPA

</td></tr>
</table>

<br/>

<p align="center"><strong>Tuition Waiver (NSU Merit Scholarship)</strong></p>

<table align="center" width="55%">
<thead>
<tr><th align="center">CGPA</th><th align="center">Waiver</th><th align="center">Name</th></tr>
</thead>
<tbody>
<tr><td align="center">&ge; 3.97</td><td align="center"><img src="https://img.shields.io/badge/100%25-FFD700?style=flat-square" alt="100%"/></td><td align="center">Chancellor's Award</td></tr>
<tr><td align="center">&ge; 3.75</td><td align="center"><img src="https://img.shields.io/badge/50%25-FFA500?style=flat-square" alt="50%"/></td><td align="center">Vice-Chancellor's Scholarship</td></tr>
<tr><td align="center">&ge; 3.50</td><td align="center"><img src="https://img.shields.io/badge/25%25-58A6FF?style=flat-square" alt="25%"/></td><td align="center">Dean's Scholarship</td></tr>
</tbody>
</table>

<p align="center"><sub>Requires minimum 30 completed credits</sub></p>

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:0a1929,100:003366&height=40&text=%20%20%20PROJECT%20STRUCTURE%20%20%20&fontColor=93C5FD&fontSize=14&fontAlignY=68" width="60%" alt="Structure"/>
</p>

<br/>

```
Project 1 (Score 100 out of 100)/
|
+-- src/
|   +-- core.py                        Shared engine - UI, parsers, grading logic
|   +-- credit_engine.py               Level 1 - Credit tally & classification
|   +-- cgpa_analyzer.py               Level 2 - CGPA, waivers, academic standing
|   +-- degree_audit.py                Level 3 - Degree audit & graduation verdict
|
+-- data/
|   +-- cse/
|   |   +-- transcript.csv             CSE student (29 entries, 3 retakes)
|   |   +-- test_L1.csv                L1 test: F, W, I, P, TR, 0-credit, D
|   |   +-- test_L2.csv                L2 test: CGPA math with non-grade entries
|   |   +-- test_retake.csv            L3 test: triple retake, W->F->pass
|   +-- llb/
|       +-- transcript.csv             LLB student (29 entries)
|       +-- test_L1.csv                L1 test: F, W, I, P, TR, 0-credit, D
|       +-- test_L2.csv                L2 test: CGPA math with non-grade entries
|       +-- test_retake.csv            L3 test: triple retake, W->I->pass
|
+-- scripts/
|   +-- cse/                           6 one-click .bat files for CSE
|   +-- llb/                           6 one-click .bat files for LLB
|
+-- docs/
|   +-- DOCUMENTATION.md               Comprehensive A-Z project documentation
|   +-- CSE226_Proj_1.pdf              Original project specification
|
+-- knowledge_base.md                  Curriculum data (CSE + LLB programs)
+-- generate_tests.py                  Auto-generates test CSVs
+-- README.md
+-- .gitignore
```

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:0d2e1a,100:064E3B&height=40&text=%20%20%20FACULTY%20Q%26A%20%20%20&fontColor=6EE7B7&fontSize=14&fontAlignY=68" width="60%" alt="FAQ"/>
</p>

<br/>

<table align="center" width="88%">
<tr><td>

**Q: How many files?** &mdash; 28 files: 4 Python source, 1 knowledge base, 8 transcript/test CSVs, 12 run scripts, 2 docs, 1 README.

**Q: Where are the test files?** &mdash; `data/cse/test_L1.csv` (credit edge cases), `test_L2.csv` (CGPA math), `test_retake.csv` (retake scenario). Same set in `data/llb/`. Each has a matching `.bat` run script.

**Q: How many runs to demo?** &mdash; 6 main runs (3 levels x 2 departments) + 6 test runs = 12 total. Each is a one-click `.bat` file.

**Q: How does the grading system work?** &mdash; NSU official scale (A=4.00 to F=0.00). W/I excluded from GPA. F = 0 credits but counted in GPA denominator.

**Q: How are retakes handled?** &mdash; Per NSU policy: best grade used for CGPA. All attempts recorded in history.

**Q: How does the waiver work?** &mdash; NSU merit scholarship: &ge;3.50 = 25% (Dean's), &ge;3.75 = 50% (VC), &ge;3.97 = 100% (Chancellor's). Needs 30+ credits.

**Q: Can you add a new program?** &mdash; Yes, add a section to `knowledge_base.md`. No code changes needed.

**Q: What is the knowledge base?** &mdash; Markdown file with full curriculum (mandatory, choice groups, electives). The "brain" that Level 3 audits against.

**Q: What if CGPA &lt; 2.00?** &mdash; System flags "ACADEMIC PROBATION", graduation verdict shows failing criteria with recommendations.

**Q: Why standard library only?** &mdash; Project spec requirement. Uses csv, sys, os, re, collections, datetime &mdash; zero pip installs.

</td></tr>
</table>

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:1F6FEB,50:0f2942,100:0a0e1a&height=120&section=footer&text=CSE226%20%E2%80%A2%20Project%201%20%E2%80%A2%20NSU%20Spring%202026&fontSize=16&fontColor=7DD3FC&fontAlignY=65&animation=fadeIn" width="100%" alt="footer"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Built%20with-GitHub%20Copilot-000000?style=flat-square&logo=githubcopilot&logoColor=white" alt="Copilot"/>&nbsp;
  <img src="https://img.shields.io/badge/Powered%20by-Claude-D97706?style=flat-square&logo=anthropic&logoColor=white" alt="Claude"/>&nbsp;
  <img src="https://img.shields.io/badge/Coded%20in-Cursor-000000?style=flat-square&logo=cursor&logoColor=white" alt="Cursor"/>&nbsp;
  <img src="https://img.shields.io/badge/AI%20Assisted-Gemini%20CLI-8E75B2?style=flat-square&logo=googlegemini&logoColor=white" alt="Gemini"/>
</p>