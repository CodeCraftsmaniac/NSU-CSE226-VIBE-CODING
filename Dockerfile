# NSU Degree Audit Engine - Backend API Dockerfile
# =================================================
# FastAPI backend - High-performance async API
# Optimized for Cloud Run with auto-scaling

FROM python:3.11-slim

WORKDIR /app

# System dependencies for PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend API and shared logic
COPY backend/ ./backend/
COPY docs/knowledge_base.md .

# Create uploads directory
RUN mkdir -p uploads && chmod 777 uploads

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/backend

EXPOSE 8080

# Change to backend directory for correct module resolution
WORKDIR /app/backend

# Create startup script that uses PORT env var
RUN echo '#!/bin/bash\nexec gunicorn app.main:app --bind 0.0.0.0:${PORT:-8080} --worker-class uvicorn.workers.UvicornWorker --workers 1 --timeout 300 --access-logfile - --error-logfile -' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
