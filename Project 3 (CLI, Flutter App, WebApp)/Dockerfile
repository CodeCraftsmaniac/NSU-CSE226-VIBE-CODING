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

# FastAPI with uvicorn - single worker for Cloud Run
# Cloud Run handles scaling via container instances
# Use --workers=1 because Cloud Run doesn't support multi-process
CMD uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8080} \
    --workers 1 \
    --timeout-keep-alive 120 \
    --access-log \
    --log-level info
