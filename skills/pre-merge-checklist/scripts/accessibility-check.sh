#!/bin/bash
set -euo pipefail

# accessibility-check.sh
# Run axe-core accessibility checks and report WCAG 2.2 violations.

URL="${1:-http://localhost:3000}"

echo "============================================"
echo "  Accessibility Check (WCAG 2.2)"
echo "============================================"
echo "Target URL: ${URL}"
echo ""

if ! command -v npx &>/dev/null; then
    echo "ERROR: npx is not available. Install Node.js first."
    exit 1
fi

EXIT_CODE=0
npx @axe-core/cli "${URL}" \
    --tags wcag2a,wcag2aa,wcag22aa \
    --exit || EXIT_CODE=$?

echo ""
echo "============================================"
if [ "${EXIT_CODE}" -eq 0 ]; then
    echo "  PASS: No WCAG 2.2 violations found."
else
    echo "  FAIL: Accessibility violations detected."
    echo "  Review the output above and fix the issues."
fi
echo "============================================"

exit "${EXIT_CODE}"
