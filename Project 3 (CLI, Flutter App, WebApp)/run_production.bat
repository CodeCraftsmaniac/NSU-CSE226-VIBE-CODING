@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM NSU Degree Audit Engine - Production Server (Windows)
REM ═══════════════════════════════════════════════════════════════════════════════

echo.
echo ============================================================
echo   NSU Degree Audit - Production Server
echo ============================================================
echo.

cd /d "%~dp0"

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Install dependencies if needed
pip install -q waitress python-dotenv

echo Starting production server...
echo.

REM Run with waitress (production WSGI server)
cd web
python -c "from waitress import serve; from app import app; print('Server running at http://0.0.0.0:5000'); serve(app, host='0.0.0.0', port=5000)"
