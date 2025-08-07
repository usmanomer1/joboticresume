#!/bin/bash
# Simple startup script for debugging

echo "Starting app on PORT: ${PORT:-8000}"
echo "Environment: ${ENVIRONMENT}"
echo "Python version: $(python --version)"

# Try to start with uvicorn directly first
exec uvicorn app_secure:app --host 0.0.0.0 --port ${PORT:-8000}