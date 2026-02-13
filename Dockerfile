FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including build tools
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for binary wheel enforcement
ENV PIP_ONLY_BINARY=":all:" \
    PIP_PREFER_BINARY=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CFLAGS="-Wno-unused-function -Wno-unused-variable -O2" \
    CXXFLAGS="-Wno-unused-function -Wno-unused-variable -O2"

# Upgrade pip to latest version for better wheel support
RUN pip install --upgrade pip setuptools wheel

# Copy pip configuration
COPY pip.conf /etc/pip.conf

# Copy requirements and install with preference for binary wheels
COPY requirements.txt .
RUN pip install --only-binary=:all: --prefer-binary --no-cache-dir -r requirements.txt || \
    pip install --prefer-binary --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p audio transcripts

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
