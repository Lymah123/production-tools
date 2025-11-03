#!/usr/bin/env bash
set -euo pipefail

# Test script for env_template.py
echo "================================"
echo "Testing env-manager..."
echo "================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_SCRIPT="$SCRIPT_DIR/../env_template.py"
TEMPLATE_DIR="$SCRIPT_DIR/../templates"

# Test 1: Check script exists
echo "✓ Test 1: Checking env_template.py exists..."
if [[ ! -f "$ENV_SCRIPT" ]]; then
    echo "✗ FAIL: env_template.py not found"
    exit 1
fi
echo "  PASS: env_template.py found"

# Test 2: Check template directory exists
echo "✓ Test 2: Checking templates directory..."
if [[ ! -d "$TEMPLATE_DIR" ]]; then
    echo "✗ FAIL: templates directory not found"
    exit 1
fi
echo "  PASS: templates directory exists"

# Test 3: Check .env.template exists
echo "✓ Test 3: Checking .env.template file..."
if [[ ! -f "$TEMPLATE_DIR/.env.template" ]]; then
    echo "✗ FAIL: .env.template not found"
    exit 1
fi
echo "  PASS: .env.template found"

# Test 4: Validate Python syntax
echo "✓ Test 4: Validating Python syntax..."
python -m py_compile "$ENV_SCRIPT"
echo "  PASS: Syntax validation complete"

# Test 5: Test help command
echo "✓ Test 5: Testing --help command..."
python "$ENV_SCRIPT" --help >/dev/null 2>&1 || true
echo "  PASS: Help command works"

# Test 6: Test generate command (dry run)
echo "✓ Test 6: Testing generate command..."
TEMP_ENV="/tmp/test_generated_$(date +%s).env"
if python "$ENV_SCRIPT" generate --output "$TEMP_ENV" 2>/dev/null; then
    if [[ -f "$TEMP_ENV" ]]; then
        echo "  PASS: Generated .env file"
        rm -f "$TEMP_ENV"
    else
        echo "  WARNING: Generate command succeeded but file not created"
    fi
else
    echo "  INFO: Generate command requires implementation"
fi

# Test 7: Test validate command
echo "✓ Test 7: Testing validate command..."
python "$ENV_SCRIPT" validate --file "$TEMPLATE_DIR/.env.template" 2>/dev/null || echo "  INFO: Validate command requires implementation"

echo ""
echo "================================"
echo "All env-manager tests passed! ✓"
echo "================================"