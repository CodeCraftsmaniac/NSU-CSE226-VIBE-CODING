"""
NSU Degree Audit API - FastAPI Application
==========================================
Production-ready async backend for OCR transcript analysis and degree auditing.
"""
import os
import logging
import asyncio
import time as _time
from typing import Dict, Set
import json

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# CORS origin allowlist - resolve from env var when provided, otherwise use defaults
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else [
    "https://ocr.nsunexus.app",
    "https://ocrapi.nsunexus.app",
    "http://localhost:3000",
    "http://localhost:5000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5000",
]

# Create app
app = FastAPI(
    title="NSU Degree Audit API",
    version="2.5.0",
    description="NSU Degree Audit Engine - OCR-based transcript analysis API",
)

# Middleware: apply gzip compression for sufficiently large responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS: explicit origin policy (no wildcard) for tighter security
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)


# Global exception handler: avoid leaking stack traces in API responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return generic error."""
    logger.error(f"Unhandled exception on {request.url.path}: {exc}")
    # Track errors for health metrics
    try:
        from app.api.v1.health import increment_error_count
        increment_error_count()
    except Exception:
        pass
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


# Request counting middleware for health dashboard telemetry
@app.middleware("http")
async def count_requests(request: Request, call_next):
    """Count requests for real-time health dashboard.
    Separates user requests from health check polls."""
    try:
        from app.api.v1.health import count_request
        count_request(request.url.path)
    except Exception:
        pass
    response = await call_next(request)
    return response


@app.get("/")
def root():
    return {
        "name": "NSU Degree Audit API",
        "version": "2.5.0",
        "framework": "FastAPI",
        "status": "running",
    }



# Load rate limiting
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc):
        return JSONResponse(status_code=429, content={"error": "Too many requests"})
except ImportError:
    pass

# Load API router
try:
    from app.api.router import api_router
    app.include_router(api_router)
    logger.info("✅ API router loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load API router: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET: Real-time OCR Progress Updates
# ═══════════════════════════════════════════════════════════════════════════════

class ConnectionManager:
    """Manage WebSocket connections for real-time progress updates."""
    
    _PROGRESS_TTL = 600  # 10 minutes
    
    def __init__(self):
        # Map of job_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of job_id -> progress data
        self.progress_data: Dict[str, dict] = {}
        # Map of job_id -> timestamp (for TTL cleanup)
        self.progress_timestamps: Dict[str, float] = {}
    
    async def connect(self, websocket: WebSocket, job_id: str):
        """Accept WebSocket connection and track it by job_id."""
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        logger.info(f"WebSocket connected for job {job_id}")
        
        # Send current progress if available
        if job_id in self.progress_data:
            await websocket.send_json(self.progress_data[job_id])
    
    def disconnect(self, websocket: WebSocket, job_id: str):
        """Remove WebSocket connection."""
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        logger.info(f"WebSocket disconnected for job {job_id}")
    
    async def broadcast_progress(self, job_id: str, progress: dict):
        """Broadcast progress update to all connections for a job."""
        self.progress_data[job_id] = progress
        self.progress_timestamps[job_id] = _time.monotonic()
        
        if job_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_json(progress)
                except Exception:
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for conn in dead_connections:
                self.active_connections[job_id].discard(conn)
        
        # Periodic TTL cleanup — purge stale progress data (>10 min)
        self._cleanup_stale_jobs()
    
    def _cleanup_stale_jobs(self):
        """Remove progress data older than TTL to prevent memory leaks."""
        cutoff = _time.monotonic() - self._PROGRESS_TTL
        stale = [jid for jid, ts in self.progress_timestamps.items() if ts < cutoff]
        for jid in stale:
            self.progress_data.pop(jid, None)
            self.progress_timestamps.pop(jid, None)
    
    def clear_job(self, job_id: str):
        """Clear job data after completion."""
        self.progress_data.pop(job_id, None)
        self.progress_timestamps.pop(job_id, None)


# Global connection manager instance
ws_manager = ConnectionManager()


@app.websocket("/ws/ocr/{job_id}")
async def websocket_ocr_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time OCR progress updates.
    
    Connect to receive progress updates for a specific OCR job.
    Messages are JSON objects with:
    - stage: Current processing stage (upload, ocr, analyze, complete)
    - progress: Percentage complete (0-100)
    - message: Human-readable status message
    - error: Error message if failed
    """
    await ws_manager.connect(websocket, job_id)
    try:
        # Keep connection alive and wait for client messages
        while True:
            # Wait for any client message (ping/pong or disconnect)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, job_id)
    except Exception as e:
        logger.warning(f"WebSocket error for job {job_id}: {e}")
        ws_manager.disconnect(websocket, job_id)


# Export manager for use in upload endpoint
def get_ws_manager():
    """Get the WebSocket manager instance."""
    return ws_manager


# Update progress function for OCR module to call
async def update_ocr_progress(job_id: str, stage: str, progress: int, message: str, error: str = None):
    """
    Update OCR progress for a specific job.
    
    Called by OCR processing code to broadcast updates to connected clients.
    """
    progress_data = {
        "job_id": job_id,
        "stage": stage,
        "progress": progress,
        "message": message,
    }
    if error:
        progress_data["error"] = error
    
    await ws_manager.broadcast_progress(job_id, progress_data)
