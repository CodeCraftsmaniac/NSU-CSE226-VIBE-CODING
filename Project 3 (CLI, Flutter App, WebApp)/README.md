<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0e1a,30:0d1b2e,60:0f2942,100:1F6FEB&height=220&section=header&text=NSU%20Degree%20Audit%20Engine&fontSize=50&fontColor=FFFFFF&fontAlignY=38&fontStyle=bold&desc=Project%203%20%E2%80%A2%20CLI%20%2B%20Web%20App%20%2B%20OCR%20%E2%80%A2%20CSE226&descSize=16&descAlignY=58&descColor=7DD3FC&animation=fadeIn&stroke=1F6FEB&strokeWidth=1" width="100%" alt="header"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/CSE226-Project%203-1F6FEB?style=for-the-badge&logo=python&logoColor=white" alt="CSE226"/>&nbsp;
  <img src="https://img.shields.io/badge/Web%20App-Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>&nbsp;
  <img src="https://img.shields.io/badge/OCR-Free%20API-2EA043?style=for-the-badge&logo=googlelens&logoColor=white" alt="OCR"/>&nbsp;
  <img src="https://img.shields.io/badge/Spring%202026-NSU-003366?style=for-the-badge&logo=googlescholar&logoColor=white" alt="NSU"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/CLI-Terminal%20App-58A6FF?style=flat-square" alt="CLI"/>&nbsp;
  <img src="https://img.shields.io/badge/Web-Browser%20App-BC8CFF?style=flat-square" alt="Web"/>&nbsp;
  <img src="https://img.shields.io/badge/OCR-PDF%20%2F%20Image-2EA043?style=flat-square" alt="OCR"/>&nbsp;
  <img src="https://img.shields.io/badge/Free-500%20scans%2Fmonth-D29922?style=flat-square" alt="Free"/>
</p>

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:0d1b2e,100:1F3A6E&height=40&text=%20%20%20ABOUT%20%20%20&fontColor=7DD3FC&fontSize=14&fontAlignY=68" width="60%" alt="About"/>
</p>

<br/>

<table align="center" width="90%">
<tr><td>

**NSU Degree Audit Engine** provides **three ways** to analyze your transcript:

1. **CLI Tool** &mdash; Python terminal application with premium UI
2. **Web Application** &mdash; Modern browser-based interface with drag & drop
3. **OCR Scanner** &mdash; Upload PDF/Image transcripts for instant analysis

Features **three levels of analysis**:
- **Level 1:** Credit Tally (earned, failed, progress)
- **Level 2:** CGPA Calculation & Waiver Eligibility
- **Level 3:** Full Degree Audit with Graduation Verdict

</td></tr>
</table>

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:1a0a2e,100:4C1D95&height=40&text=%20%20%20WEB%20APPLICATION%20%20%20&fontColor=E9D5FF&fontSize=14&fontAlignY=68" width="60%" alt="Web App"/>
</p>

<br/>

### Quick Start (Web)

```bash
# Navigate to web directory
cd web

# Install dependencies (first time only)
pip install -r ../requirements.txt

# Run the web server
npm run dev
# OR
python app.py

# Open in browser
# http://localhost:5000
```

### Features

- **Drag & Drop** PDF/Image upload
- **Real-time OCR** scanning animation
- **Free OCR API** (500 scans/month via OCR.space)
- **No heavy downloads** - works immediately
- **Dark mode** premium UI
- **3-level analysis** displayed in tabs

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:0d2e1a,100:064E3B&height=40&text=%20%20%20CLI%20APPLICATION%20%20%20&fontColor=6EE7B7&fontSize=14&fontAlignY=68" width="60%" alt="CLI"/>
</p>

<br/>

### Quick Start (CLI)

<table align="center" width="80%">
<thead>
<tr>
<th align="center" colspan="2"><img src="https://img.shields.io/badge/CSE-Computer%20Science%20%26%20Engineering-1F6FEB?style=flat-square" alt="CSE"/></th>
</tr>
<tr><th align="left">Command</th><th align="left">What It Shows</th></tr>
</thead>
<tbody>
<tr><td><code>scripts/cse/run_level1.bat</code></td><td>Level 1 &mdash; Credit Tally</td></tr>
<tr><td><code>scripts/cse/run_level2.bat</code></td><td>Level 2 &mdash; CGPA & Waiver</td></tr>
<tr><td><code>scripts/cse/run_level3.bat</code></td><td>Level 3 &mdash; Full Degree Audit</td></tr>
</tbody>
</table>

```bash
# Terminal commands
python src/credit_engine.py data/cse/transcript.csv
python src/cgpa_analyzer.py data/cse/transcript.csv
python src/degree_audit.py  data/cse/transcript.csv CSE knowledge_base.md
```

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:2e1a0d,100:7C2D12&height=40&text=%20%20%20OCR%20ENGINE%20%20%20&fontColor=FED7AA&fontSize=14&fontAlignY=68" width="60%" alt="OCR"/>
</p>

<br/>

### OCR Features

| Feature | Description |
|---------|-------------|
| **Free API** | OCR.space - 500 requests/month free |
| **PDF Support** | Scanned or digital PDFs |
| **Image Support** | PNG, JPG, JPEG |
| **No Downloads** | No large model files needed |
| **Fast** | Results in seconds |
| **Fallback** | Native PDF text extraction for digital PDFs |

### Supported Formats

- **PDF** (scanned transcripts, digital transcripts)
- **PNG/JPG/JPEG** (photos of transcripts)
- Max file size: 16MB

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:0d1b2e,100:164E63&height=40&text=%20%20%20PROJECT%20STRUCTURE%20%20%20&fontColor=A5F3FC&fontSize=14&fontAlignY=68" width="60%" alt="Structure"/>
</p>

<br/>

```
Project 3 (CLI, Flutter App, WebApp)/
|
+-- src/
|   +-- core.py                 # Shared engine - UI, parsers, grading
|   +-- credit_engine.py        # Level 1 - Credit tally
|   +-- cgpa_analyzer.py        # Level 2 - CGPA & waiver
|   +-- degree_audit.py         # Level 3 - Degree audit
|   +-- ocr_engine.py           # Heavy OCR (PaddleOCR/EasyOCR)
|   +-- ocr_web.py              # Lightweight OCR (OCR.space API)
|
+-- web/
|   +-- app.py                  # Flask web application
|   +-- templates/
|   |   +-- index.html          # Main web page
|   +-- static/
|   |   +-- css/style.css       # Premium dark mode styles
|   |   +-- js/app.js           # Frontend JavaScript
|   +-- uploads/                # Temporary upload storage
|
+-- data/
|   +-- cse/transcript.csv      # Sample CSE transcript
|   +-- llb/transcript.csv      # Sample LLB transcript
|
+-- scripts/                    # One-click .bat run scripts
|
+-- docs/                       # Documentation
|
+-- knowledge_base.md           # Curriculum data (CSE + LLB)
+-- requirements.txt            # Python dependencies
+-- README.md
```

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:1a0d2e,100:581C87&height=40&text=%20%20%20INSTALLATION%20%20%20&fontColor=E9D5FF&fontSize=14&fontAlignY=68" width="60%" alt="Install"/>
</p>

<br/>

### Requirements

- Python 3.10+
- pip (Python package manager)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Dependencies

| Package | Purpose |
|---------|---------|
| Flask | Web framework |
| PyMuPDF | PDF handling |
| Pillow | Image processing |
| rich | Terminal UI (CLI) |

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:0d2e1a,100:064E3B&height=40&text=%20%20%20NSU%20GRADING%20%20%20&fontColor=6EE7B7&fontSize=14&fontAlignY=68" width="60%" alt="Grading"/>
</p>

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

**Tuition Waiver (NSU Merit Scholarship)**

| CGPA | Waiver | Name |
|------|--------|------|
| >= 3.97 | 100% | Chancellor's Award |
| >= 3.75 | 50% | Vice-Chancellor's Scholarship |
| >= 3.50 | 25% | Dean's Scholarship |

<p align="center"><sub>Requires minimum 30 completed credits</sub></p>

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:1F6FEB,50:0f2942,100:0a0e1a&height=120&section=footer&text=CSE226%20%E2%80%A2%20Project%203%20%E2%80%A2%20NSU%20Spring%202026&fontSize=16&fontColor=7DD3FC&fontAlignY=65&animation=fadeIn" width="100%" alt="footer"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Built%20with-Claude%20Code-D97706?style=flat-square&logo=anthropic&logoColor=white" alt="Claude"/>&nbsp;
  <img src="https://img.shields.io/badge/OCR-OCR.space%20API-2EA043?style=flat-square&logo=googlelens&logoColor=white" alt="OCR.space"/>&nbsp;
  <img src="https://img.shields.io/badge/Web-Flask%20%2B%20JS-000000?style=flat-square&logo=flask&logoColor=white" alt="Flask"/>
</p>
