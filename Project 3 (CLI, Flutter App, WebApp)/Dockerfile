# NSU Degree Audit Engine - Backend API Dockerfile
# =================================================
# FastAPI backend - High-performance async API
# Optimized for Cloud Run with auto-scaling

FROM python:3.11-slim

WORKDIR /app

# System dependencies for PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend API and shared logic
COPY backend/ ./backend/
COPY knowledge_base.md .

# Create uploads directory
RUN mkdir -p uploads && chmod 777 uploads

# Environment
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PYTHONPATH=/app:/app/backend

EXPOSE 8080

# Change to backend directory for correct module resolution
WORKDIR /app/backend

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# FastAPI with gunicorn + uvicorn workers
# This is more stable for Cloud Run than pure uvicorn
CMD ["gunicorn", "app.main:app", \
    "--bind", "0.0.0.0:8080", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--workers", "1", \
    "--timeout", "120", \
    "--keep-alive", "120", \
    "--access-logfile", "-", \
    "--error-logfile", "-"]
