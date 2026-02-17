#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit  # Exit on error
set -o pipefail # Catch errors in pipes

echo "==> Starting build process..."

# Upgrade pip to latest version
echo "==> Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Install dependencies with binary wheels only
echo "==> Installing dependencies (binary wheels only)..."
pip install \
    --only-binary=:all: \
    --prefer-binary \
    --no-cache-dir \
    -r requirements.txt

echo "==> Build completed successfully!"
