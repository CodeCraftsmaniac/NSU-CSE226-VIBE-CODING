# NSU Degree Audit Engine - Backend API Dockerfile
# =================================================
# Pure API backend - NO UI, only JSON endpoints
# Optimized for 20+ concurrent users

FROM python:3.11-slim

WORKDIR /app

# System dependencies for PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend API and shared logic (all in backend/ now)
COPY backend/ ./backend/
COPY knowledge_base.md .

# Create uploads directory
RUN mkdir -p uploads && chmod 777 uploads

# Environment
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Concurrency settings for 20+ users
# WEB_CONCURRENCY can be overridden at runtime
ENV WEB_CONCURRENCY=4
ENV GUNICORN_WORKERS=4
ENV GUNICORN_THREADS=4

EXPOSE 8080

# Production server - Optimized for 20+ concurrent users
# Formula: workers = (2 * CPU cores) + 1, with 4 threads each
# This supports: 4 workers * 4 threads = 16 concurrent requests + queueing
# Cloud Run will scale instances for additional load
CMD exec gunicorn \
    --bind :$PORT \
    --workers ${GUNICORN_WORKERS:-4} \
    --threads ${GUNICORN_THREADS:-4} \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile - \
    backend.api:app
