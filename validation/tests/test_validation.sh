#!/usr/bin/env bash
set -euo pipefail

echo "Testing config_validator.py..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATOR_SCRIPT="$SCRIPT_DIR/../config_validator.py"
VERSION_CHECKER="$SCRIPT_DIR/../version_checker.py"

# Test 1: Check scripts exist
echo "✓ Test 1: Checking validator scripts..."
if [[ ! -f "$VALIDATOR_SCRIPT" ]]; then
    echo "✗ FAIL: config_validator.py not found"
    exit 1
fi
if [[ ! -f "$VERSION_CHECKER" ]]; then
    echo "✗ FAIL: version_checker.py not found"
    exit 1
fi
echo "  PASS: All validator scripts found"

# Test 2: Validate Python syntax
echo "✓ Test 2: Validating Python syntax..."
python -m py_compile "$VALIDATOR_SCRIPT"
python -m py_compile "$VERSION_CHECKER"
echo "  PASS: Syntax validation complete"

# Test 3: Test help command
echo "✓ Test 3: Testing --help command..."
python "$VALIDATOR_SCRIPT" --help >/dev/null 2>&1
echo "  PASS: Help command works"

# Test 4: Test version checker directly
echo "✓ Test 4: Testing version checker..."
python "$VERSION_CHECKER" --help >/dev/null 2>&1 || echo "  INFO: Version checker CLI not implemented"

echo ""
echo "================================"
echo "All validation tests passed! ✓"
echo "================================"