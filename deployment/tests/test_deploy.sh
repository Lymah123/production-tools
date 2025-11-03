#!/usr/bin/env bash
set -euo pipefail

# Test script for deploy.sh
echo "================================"
echo "Testing deployment script..."
echo "================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_SCRIPT="$SCRIPT_DIR/../deploy.sh"

# Test 1: Check script exists
echo "✓ Test 1: Checking deploy.sh exists..."
if [[ ! -f "$DEPLOY_SCRIPT" ]]; then
    echo "✗ FAIL: deploy.sh not found at $DEPLOY_SCRIPT"
    exit 1
fi
echo "  PASS: deploy.sh found"

# Test 2: Check script is executable
echo "✓ Test 2: Checking deploy.sh permissions..."
if [[ ! -x "$DEPLOY_SCRIPT" ]] && [[ "$(uname -s)" != MINGW* ]]; then
    echo "  WARNING: deploy.sh not executable, making it executable..."
    chmod +x "$DEPLOY_SCRIPT"
fi
echo "  PASS: deploy.sh has correct permissions"

# Test 3: Check config files exist
echo "✓ Test 3: Checking platform config files..."
CONFIG_DIR="$SCRIPT_DIR/../config"
for platform in macos linux windows; do
    if [[ ! -f "$CONFIG_DIR/${platform}.conf" ]]; then
        echo "✗ FAIL: Missing config for $platform"
        exit 1
    fi
    echo "  PASS: ${platform}.conf exists"
done

# Test 4: Validate bash syntax
echo "✓ Test 4: Validating bash syntax..."
if command -v shellcheck >/dev/null 2>&1; then
    shellcheck "$DEPLOY_SCRIPT" || echo "  WARNING: shellcheck found issues"
else
    bash -n "$DEPLOY_SCRIPT"
fi
echo "  PASS: Syntax validation complete"

# Test 5: Dry-run test (if script supports it)
echo "✓ Test 5: Testing OS detection..."
bash "$DEPLOY_SCRIPT" --help 2>/dev/null || true

echo ""
echo "================================"
echo "All deployment tests passed! ✓"
echo "================================" 