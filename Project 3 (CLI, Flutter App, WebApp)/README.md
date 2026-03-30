<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0e1a,30:0d1b2e,60:0f2942,100:1F6FEB&height=220&section=header&text=NSU%20Degree%20Audit%20Engine&fontSize=50&fontColor=FFFFFF&fontAlignY=38&fontStyle=bold&desc=Project%203%20%E2%80%A2%20Web%20App%20%2B%20Flutter%20%2B%20CLI%20%2B%20OCR%20%E2%80%A2%20CSE226&descSize=16&descAlignY=58&descColor=7DD3FC&animation=fadeIn&stroke=1F6FEB&strokeWidth=1" width="100%" alt="header"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/CSE226-Project%203-1F6FEB?style=for-the-badge&logo=python&logoColor=white" alt="CSE226"/>&nbsp;
  <img src="https://img.shields.io/badge/Backend-Cloud%20Run-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white" alt="Cloud Run"/>&nbsp;
  <img src="https://img.shields.io/badge/Mobile-Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white" alt="Flutter"/>&nbsp;
  <img src="https://img.shields.io/badge/OCR-Google%20Vision-4285F4?style=for-the-badge&logo=googlelens&logoColor=white" alt="OCR"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/CLI-Terminal%20App-BC8CFF?style=flat-square" alt="CLI"/>&nbsp;
  <img src="https://img.shields.io/badge/Web-Vercel-000000?style=flat-square" alt="Web"/>&nbsp;
  <img src="https://img.shields.io/badge/Flutter-Mobile%20App-02569B?style=flat-square" alt="Flutter"/>&nbsp;
  <img src="https://img.shields.io/badge/API-ocrapi.nsunexus.app-00C7B7?style=flat-square" alt="API"/>
</p>

<br/>

## 🌐 Live URLs

| Component | URL | Description |
|-----------|-----|-------------|
| **Web App** | [ocr.nsunexus.app](https://ocr.nsunexus.app) | Frontend UI on Vercel |
| **Backend API** | [ocrapi.nsunexus.app](https://ocrapi.nsunexus.app) | Cloud Run API |
| **Health Check** | [ocrapi.nsunexus.app/health](https://ocrapi.nsunexus.app/health) | API status & OCR limits |

<br/>

## About

**NSU Degree Audit Engine** scans university transcripts via **OCR** and provides:

- **Level 1:** Credit Tally (earned, failed, progress)
- **Level 2:** CGPA Calculation & Waiver Eligibility  
- **Level 3:** Full Degree Audit with Graduation Verdict

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SINGLE BACKEND API                        │
│              ocrapi.nsunexus.app (Cloud Run)                │
│         backend/api.py + src/ (shared logic)                │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  ┌──────────┐       ┌──────────┐       ┌──────────┐
  │   CLI    │       │   Web    │       │ Flutter  │
  │ Terminal │       │ Browser  │       │  Mobile  │
  └──────────┘       └──────────┘       └──────────┘
   cli_app/          ocr.nsunexus.app   flutter_app/
```

All 3 frontends call the **same backend API** — only the UI differs:

| Platform | Location | Technology |
|----------|----------|------------|
| 🖥️ **CLI** | `cli_app/main.py` | Python + Rich |
| 🌐 **Web** | `ocr.nsunexus.app` (Vercel) | HTML/CSS/JS |
| 📱 **Flutter** | `flutter_app/` | Dart + Flutter |

<br/>

## Project Structure

```
Project 3/
│
├── backend/                    # 🚀 CLOUD RUN API (ocrapi.nsunexus.app)
│   └── api.py                  #   Pure REST API - /health, /upload
│
├── src/                        # 🧠 SHARED BACKEND LOGIC
│   ├── core.py                 #   Grade mapping, CGPA, credit logic
│   ├── ocr_web.py              #   OCR via Google Vision / OCR.space
│   ├── credit_engine.py        #   Level 1 - Credit tally
│   ├── cgpa_analyzer.py        #   Level 2 - CGPA & waiver
│   └── degree_audit.py         #   Level 3 - Degree audit
│
├── cli_app/                    # 🖥️ CLI APPLICATION
│   └── main.py                 #   Terminal UI (Rich library)
│
├── web_app/                    # 🌐 WEB FRONTEND (ocr.nsunexus.app)
│   ├── app.py                  #   Flask server (Vercel)
│   ├── templates/index.html    #   Main page
│   └── static/                 #   CSS, JS, SVG assets
│
├── flutter_app/                # 📱 FLUTTER MOBILE APP
│   ├── lib/main.dart           #   Full Flutter app
│   └── pubspec.yaml            #   Dependencies
│
├── knowledge_base.md           # 📚 Program requirements (CSE/LLB)
├── Dockerfile                  # 🐳 Cloud Run container config
├── requirements.txt            # Python dependencies
└── .env.example                # Environment variable template
```

<br/>

## Quick Start

### CLI App (connects to Cloud API)
```bash
pip install -r requirements.txt
python cli_app/main.py --cloud    # Uses ocrapi.nsunexus.app
```

### Flutter App
```bash
cd flutter_app
flutter pub get
flutter run                       # Connects to ocrapi.nsunexus.app
```

### Local Development (Optional)
```bash
cp .env.example .env              # Add your OCR API keys
python backend/api.py             # Local API at localhost:8080
```

<br/>

## Environment Variables

Create `.env` file (see `.env.example`):

```env
GOOGLE_VISION_API_KEY=your_key_here
OCR_SPACE_API_KEY=your_key_here
```

<br/>

## NSU Grading Scale

| Grade | Points | Grade | Points |
|:-----:|:------:|:-----:|:------:|
| A | 4.00 | C | 2.00 |
| A- | 3.70 | C- | 1.70 |
| B+ | 3.30 | D+ | 1.30 |
| B | 3.00 | D | 1.00 |
| B- | 2.70 | F | 0.00 |
| C+ | 2.30 | | |

**Tuition Waiver (Merit Scholarship)**

| CGPA | Waiver | Name |
|------|--------|------|
| ≥ 3.97 | 100% | Chancellor's Award |
| ≥ 3.75 | 50% | Vice-Chancellor's Scholarship |
| ≥ 3.50 | 25% | Dean's Scholarship |

<br/>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:1F6FEB,50:0f2942,100:0a0e1a&height=100&section=footer" width="100%" alt="footer"/>
</p>

<p align="center">
  <sub>CSE226 • Project 3 • NSU Spring 2026</sub>
</p>
