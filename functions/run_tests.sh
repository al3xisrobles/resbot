#!/bin/bash
# Test runner script for resy_client tests
# Usage: ./run_tests.sh [test_pattern]

cd "$(dirname "$0")"
source venv/bin/activate

# Set PYTHONPATH to include api directory
export PYTHONPATH=api:$PYTHONPATH

# Run pytest with any provided arguments
if [ $# -eq 0 ]; then
    # Run all tests if no pattern provided
    python -m pytest api/resy_client/tests/ -v
else
    # Run tests matching the pattern
    python -m pytest api/resy_client/tests/ -k "$1" -v
fi
