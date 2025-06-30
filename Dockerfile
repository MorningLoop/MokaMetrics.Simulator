# Multi-stage Docker build for MokaMetrics.Simulator
# Stage 1: Build React frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies (including dev dependencies needed for build)
RUN npm ci

# Copy source code
COPY frontend/ ./

# Build the React app
RUN npm run build

# Stage 2: Python runtime with React build
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY Simulator/ ./Simulator/
COPY config.yaml .
COPY *.py .

# Copy React build from frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy and set up entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash simulator && \
    chown -R simulator:simulator /app
USER simulator

# Expose web interface port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Set entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command - start web interface with React frontend
CMD ["python", "-m", "Simulator.web_interface"]
