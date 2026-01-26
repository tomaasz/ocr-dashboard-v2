#!/bin/bash
# OCR Dashboard V2 - Start Web Server

cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Load .env if exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

PORT="${OCR_DASHBOARD_PORT:-9090}"

echo "🚀 Starting OCR Dashboard V2 on port $PORT..."
uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
