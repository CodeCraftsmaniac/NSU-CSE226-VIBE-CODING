# NSU Degree Audit Engine - Backend API Dockerfile
# =================================================
# Pure API backend - NO UI, only JSON endpoints

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

EXPOSE 8080

# Production server - backend API only
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 120 backend.api:app
