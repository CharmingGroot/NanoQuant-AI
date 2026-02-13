# Use Python 3.12 base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY *.py .
COPY *.md .
COPY .env.example .

# Create .env from example if not exists
RUN if [ ! -f .env ]; then cp .env.example .env; fi

# Expose port (for future web dashboard)
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command - run tests
CMD ["python", "-c", "import sys; print('NanoQuant AI Docker Container Ready'); print('Run tests with: docker exec <container> python <module>.py')"]
