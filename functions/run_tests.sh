#!/bin/bash
# Test runner script for resy_client and search functionality tests
# Usage: ./run_tests.sh [test_pattern] [test_directory]
# Examples:
#   ./run_tests.sh                    # Run all tests (resy_client + search)
#   ./run_tests.sh "pagination"       # Run tests matching "pagination" in all directories
#   ./run_tests.sh "" "api/tests"     # Run all search tests
#   ./run_tests.sh "pagination" "api/tests"  # Run pagination tests in search suite

cd "$(dirname "$0")"
source venv/bin/activate

# Set PYTHONPATH to include api directory
export PYTHONPATH=api:$PYTHONPATH

# Determine test directory - default to both test directories
if [ -z "$2" ]; then
    # Run all tests in both directories
    TEST_DIRS="api/resy_client/tests/ api/tests/"
else
    TEST_DIRS="$2"
fi

# Run pytest with any provided arguments
if [ $# -eq 0 ] || [ -z "$1" ]; then
    # Run all tests if no pattern provided
    python -m pytest $TEST_DIRS -v
else
    # Run tests matching the pattern
    python -m pytest $TEST_DIRS -k "$1" -v
fi
