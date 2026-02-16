#!/bin/bash
# Validate response schemas and type checking
# Run this before deployment to catch schema inconsistencies

set -e  # Exit on error

echo "🔍 Running response schema validation..."
echo ""

cd "$(dirname "$0")/.."

# 1. Run pytest on response schema tests
echo "📋 Step 1: Testing response schema validation..."
pytest api/test_response_schemas.py -v --tb=short
echo "✅ Schema tests passed!"
echo ""

# 2. Run mypy type checking on API modules
echo "🔎 Step 2: Running mypy type checking..."
mypy api/snipe.py api/schedule.py api/response_schemas.py --config-file=mypy.ini
echo "✅ Type checking passed!"
echo ""

echo "🎉 All validation checks passed! Response schemas are consistent."
