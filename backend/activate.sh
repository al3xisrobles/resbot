#!/bin/bash
# Helper script to activate the virtual environment
# Usage: source activate.sh

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Run ./setup.sh first to create it."
    return 1
fi

source venv/bin/activate
echo "✅ Virtual environment activated!"
echo ""
echo "Available commands:"
echo "  python interactive.py              - Run interactive UI"
echo "  python main.py [creds] [config]    - Run with config files"
echo "  deactivate                         - Exit virtual environment"
echo ""
