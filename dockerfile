# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY simulator/ ./simulator/
COPY config.yaml ./config.yaml

# Create logs directory
RUN mkdir -p /logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TZ=UTC
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run the simulator
CMD ["python", "-m", "simulator.main"]