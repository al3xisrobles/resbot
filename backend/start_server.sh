#!/bin/bash

# Start Resy Bot Flask Server
# This script activates the virtual environment and starts the Flask server

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Check for GEMINI_API_KEY
if [ -z "$GEMINI_API_KEY" ]; then
    if [ -f ".env" ]; then
        echo "🔑 Loading environment variables from .env..."
        export $(cat .env | grep -v '^#' | xargs)
    else
        echo "⚠️  GEMINI_API_KEY not set. AI features will be disabled."
        echo "   Set it with: export GEMINI_API_KEY=your_key_here"
    fi
fi

# Start Flask server
echo ""
python app.py
