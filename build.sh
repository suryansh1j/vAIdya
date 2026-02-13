#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit  # Exit on error

# Upgrade pip to latest version
pip install --upgrade pip

# Install dependencies with preference for binary wheels
pip install --prefer-binary --no-cache-dir -r requirements.txt

# Download spacy language model if needed
python -m spacy download en_core_web_sm || true

echo "Build completed successfully!"
