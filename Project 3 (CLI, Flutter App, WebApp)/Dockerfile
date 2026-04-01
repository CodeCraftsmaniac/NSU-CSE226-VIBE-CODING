# NSU Degree Audit Engine - Backend API Dockerfile
# =================================================
# FastAPI backend - High-performance async API
# Optimized for 20+ concurrent users with uvicorn

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
ENV PYTHONPATH=/app/backend

# Concurrency settings for 20+ users
ENV WEB_CONCURRENCY=4
ENV UVICORN_WORKERS=4

EXPOSE 8080

# FastAPI with uvicorn - high-performance async server
# Supports async operations for better concurrency
# Cloud Run will scale instances for additional load
CMD exec uvicorn backend.app.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers ${UVICORN_WORKERS:-4} \
    --timeout-keep-alive 5 \
    --access-log \
    --log-level info
