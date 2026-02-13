#!/usr/bin/env bash
# Build script for Render deployment with aggressive binary wheel enforcement

set -o errexit  # Exit on error
set -o pipefail # Catch errors in pipes

echo "==> Starting build process..."

# Set environment variables to prevent compilation
export PIP_ONLY_BINARY=":all:"
export PIP_PREFER_BINARY=1
export PIP_NO_BUILD_ISOLATION=0

# Suppress compiler warnings if compilation is unavoidable
export CFLAGS="-Wno-unused-function -Wno-unused-variable -O2"
export CXXFLAGS="-Wno-unused-function -Wno-unused-variable -O2"

echo "==> Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

echo "==> Installing dependencies (binary wheels only)..."
# Try to install with strict binary-only mode first
if pip install \
    --only-binary=:all: \
    --prefer-binary \
    --no-cache-dir \
    --platform manylinux2014_x86_64 \
    --python-version 312 \
    --implementation cp \
    -r requirements.txt 2>/dev/null; then
    echo "==> Successfully installed all packages from binary wheels!"
else
    echo "==> Some packages unavailable as wheels, trying with fallback..."
    # Fallback: allow source for specific packages that might not have wheels
    pip install \
        --prefer-binary \
        --no-cache-dir \
        -r requirements.txt
fi

echo "==> Downloading spacy language model..."
python -m spacy download en_core_web_sm || echo "Warning: Could not download spacy model"

echo "==> Build completed successfully!"
