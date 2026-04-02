"""
NSU Degree Audit Web Application
================================
Pure frontend web interface - serves HTML/CSS/JS only.
All OCR and analysis handled by Cloud Run backend API.

The JavaScript (app.js) calls https://ocrapi.nsunexus.app directly.
"""

import os
import logging
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# ═══════════════════════════════════════════════════════════════════════════════
# Application Configuration
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="NSU Degree Audit - Web Frontend",
    version="2.2.0",
    docs_url=None,  # Disable docs for frontend
    redoc_url=None
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO)
logging.basicConfig(level=log_level, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Get the directory where app.py is located
try:
    BASE_DIR = Path(__file__).parent.resolve()
except Exception:
    BASE_DIR = Path.cwd()

logger.info(f"BASE_DIR resolved to: {BASE_DIR}")

# Setup templates with absolute path
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

if not TEMPLATES_DIR.exists():
    # Try alternative paths for Vercel
    alt_paths = [
        Path.cwd() / "web_app" / "templates",
        Path.cwd() / "templates",
        Path("/var/task/web_app/templates"),
        Path("/var/task/templates"),
    ]
    for alt in alt_paths:
        if alt.exists():
            TEMPLATES_DIR = alt
            STATIC_DIR = alt.parent / "static"
            logger.info(f"Using alternative template path: {TEMPLATES_DIR}")
            break

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mount static files only if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    logger.warning(f"Static directory not found: {STATIC_DIR}")

# ═══════════════════════════════════════════════════════════════════════════════
# Routes - Pure Frontend (no OCR logic)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render main page."""
    try:
        # Debug: log before attempting render
        logger.info(f"Attempting to render index.html from {TEMPLATES_DIR}")
        resp = templates.TemplateResponse("index.html", {"request": request})
        logger.info("Template rendered successfully")
        return resp
    except Exception as e:
        import traceback
        error_tb = traceback.format_exc()
        logger.error(f"Failed to render index.html: {e}")
        logger.error(f"Traceback: {error_tb}")
        return HTMLResponse(
            content=f"<html><body><h1>Error loading page</h1><pre>Template: {TEMPLATES_DIR}\n\nError: {e}\n\nTraceback:\n{error_tb}</pre></body></html>",
            status_code=500
        )


@app.get("/cli-callback", response_class=HTMLResponse)
async def cli_callback(request: Request):
    """Serve CLI OAuth callback page (legacy).
    
    This page receives OAuth tokens from Supabase and forwards them
    to the local CLI server running on the specified port.
    """
    return templates.TemplateResponse("cli_callback.html", {"request": request})


@app.get("/cli-auth", response_class=HTMLResponse)
async def cli_auth(request: Request):
    """Serve CLI device code authentication page.
    
    Like GitHub CLI / Supabase CLI flow:
    1. CLI generates device code
    2. User opens this page with code in URL
    3. User signs in with Google
    4. CLI polls and receives token
    """
    return templates.TemplateResponse("cli_auth.html", {"request": request})


@app.get("/debug/paths")
async def debug_paths():
    """Debug endpoint to check path resolution on Vercel."""
    import os
    cwd = os.getcwd()
    return {
        'cwd': cwd,
        'base_dir': str(BASE_DIR),
        'templates_dir': str(TEMPLATES_DIR),
        'templates_exists': TEMPLATES_DIR.exists(),
        'static_dir': str(STATIC_DIR),
        'static_exists': STATIC_DIR.exists(),
        'cwd_contents': os.listdir(cwd)[:20] if os.path.exists(cwd) else [],
        'templates_contents': list(TEMPLATES_DIR.iterdir()) if TEMPLATES_DIR.exists() else [],
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        'status': 'healthy',
        'type': 'frontend',
        'framework': 'FastAPI',
        'backend': 'https://ocrapi.nsunexus.app',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.2.0'
    }


@app.exception_handler(404)
async def not_found(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={'error': 'Not found'}
    )


@app.exception_handler(500)
async def server_error(request: Request, exc):
    """Handle 500 errors with details for debugging."""
    import traceback
    error_detail = str(exc) if exc else "Unknown error"
    tb = traceback.format_exc() if exc else "No traceback available"
    logger.error(f"500 Error: {error_detail}")
    logger.error(f"Traceback: {tb}")
    return JSONResponse(
        status_code=500,
        content={
            'error': 'Internal server error',
            'detail': error_detail,
            'path': str(request.url.path) if request else None,
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Development Server
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import socket
    import uvicorn
    
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    port = int(os.getenv('PORT', 5000))
    local_ip = get_local_ip()

    print("\n" + "=" * 60)
    print("  NSU Degree Audit - Web Frontend (FastAPI)")
    print("=" * 60)
    print(f"\n  Local       : http://localhost:{port}")
    print(f"  Network     : http://{local_ip}:{port}")
    print(f"\n  Backend API : https://ocrapi.nsunexus.app")
    print("\n  Press Ctrl+C to stop\n")
    print("=" * 60)

    uvicorn.run(app, host='0.0.0.0', port=port)


# Vercel/ASGI handler
handler = app
