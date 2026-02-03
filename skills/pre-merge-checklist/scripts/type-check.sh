#!/bin/bash
set -euo pipefail

# type-check.sh
# Run static type checks for Python (mypy) and TypeScript (tsc).

FAIL=0

echo "============================================"
echo "  Static Type Checking"
echo "============================================"

# --- Python (mypy) --------------------------------------------------------
echo ""
echo "-- mypy (Python) --"
if command -v mypy &>/dev/null; then
    if mypy src/ --strict; then
        echo "PASS: mypy found no issues."
    else
        echo "FAIL: mypy reported type errors."
        FAIL=1
    fi
else
    echo "SKIP: mypy is not installed."
fi

# --- TypeScript (tsc) -----------------------------------------------------
echo ""
echo "-- tsc (TypeScript) --"
if [ -f "tsconfig.json" ]; then
    if npx tsc --noEmit; then
        echo "PASS: tsc found no issues."
    else
        echo "FAIL: tsc reported type errors."
        FAIL=1
    fi
else
    echo "SKIP: no tsconfig.json found."
fi

# --- Summary ---------------------------------------------------------------
echo ""
if [ "${FAIL}" -eq 0 ]; then
    echo "All type checks passed."
else
    echo "One or more type checks failed."
fi

exit "${FAIL}"
