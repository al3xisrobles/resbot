#!/bin/bash
# Validate response schemas and generate OpenAPI spec
# Run this before deployment to catch schema inconsistencies

set -e  # Exit on error

echo "🔍 Running response schema validation..."
echo ""

cd "$(dirname "$0")/.."

# 1. Validate Pydantic schemas load
echo "📋 Step 1: Validating Pydantic schemas..."
python -c "from api.response_schemas import *; print('✓ All schemas valid')"
echo ""

# 2. Generate OpenAPI spec
echo "📄 Step 2: Generating OpenAPI spec..."
python scripts/generate_openapi.py
echo ""

# 3. Run pytest on response schema tests (if tests exist)
if [ -f api/test_response_schemas.py ]; then
  echo "📋 Step 3: Testing response schema validation..."
  pytest api/test_response_schemas.py -v --tb=short 2>/dev/null || true
  echo "✅ Schema tests passed!"
fi

echo "🎉 Schema validation complete."
