#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# NSU Degree Audit Engine - Production Server (Linux/Mac)
# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "============================================================"
echo "  NSU Degree Audit - Production Server"
echo "============================================================"
echo ""

cd "$(dirname "$0")"

# Activate virtual environment if exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Install dependencies
pip install -q gunicorn python-dotenv

echo "Starting production server..."
echo ""

# Run with gunicorn (production WSGI server)
cd web
gunicorn -w 4 -b 0.0.0.0:5000 app:app --access-logfile - --error-logfile -
