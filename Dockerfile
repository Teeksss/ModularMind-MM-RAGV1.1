# Backend Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set up environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run migrations and start server
CMD alembic upgrade head && uvicorn ModularMind.API.main:app --host 0.0.0.0 --port 8000