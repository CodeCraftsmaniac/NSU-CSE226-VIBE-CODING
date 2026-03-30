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

from flask import Flask, render_template, jsonify, send_from_directory

# Enable CORS for API access
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# Application Configuration
# ═══════════════════════════════════════════════════════════════════════════════

def create_app():
    """Application factory for Flask app."""
    app = Flask(__name__)
    
    if CORS_AVAILABLE:
        CORS(app, origins="*")

    app.config['ENV'] = os.getenv('FLASK_ENV', 'production')
    app.config['DEBUG'] = os.getenv('DEBUG', 'false').lower() == 'true'
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'nsu-web-frontend')

    # Configure logging
    log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    logging.basicConfig(level=log_level, format='%(asctime)s [%(levelname)s] %(message)s')

    return app

app = create_app()
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Routes - Pure Frontend (no OCR logic)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Render main page."""
    return render_template('index.html')


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'type': 'frontend',
        'backend': 'https://ocrapi.nsunexus.app',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.1.0'
    })


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS, images)."""
    return send_from_directory('static', filename)


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Development Server
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import socket
    
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
    print("  NSU Degree Audit - Web Frontend")
    print("=" * 60)
    print(f"\n  Local       : http://localhost:{port}")
    print(f"  Network     : http://{local_ip}:{port}")
    print(f"\n  Backend API : https://ocrapi.nsunexus.app")
    print("\n  Press Ctrl+C to stop\n")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=port)


# Vercel serverless handler
handler = app
