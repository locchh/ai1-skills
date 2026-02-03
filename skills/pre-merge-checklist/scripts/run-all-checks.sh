#!/bin/bash
set -euo pipefail

# run-all-checks.sh
# Run all pre-merge quality checks sequentially and report a summary.

PASS=0
FAIL=0
declare -a RESULTS=()

# ---------------------------------------------------------------------------
# Helper: run a single check, record pass/fail
# ---------------------------------------------------------------------------
run_check() {
    local name="$1"
    shift
    echo ""
    echo "--------------------------------------------"
    echo "  Running: ${name}"
    echo "--------------------------------------------"
    if "$@"; then
        RESULTS+=("PASS  ${name}")
        PASS=$((PASS + 1))
    else
        RESULTS+=("FAIL  ${name}")
        FAIL=$((FAIL + 1))
    fi
}

# ---------------------------------------------------------------------------
# Check 1: Python linting with ruff
# ---------------------------------------------------------------------------
run_check "ruff (Python lint)" ruff check src/

# ---------------------------------------------------------------------------
# Check 2: Python type checking with mypy
# ---------------------------------------------------------------------------
run_check "mypy (Python types)" mypy src/ --strict

# ---------------------------------------------------------------------------
# Check 3: Python tests with coverage
# ---------------------------------------------------------------------------
run_check "pytest (Python tests + coverage)" pytest -x --cov=src --cov-fail-under=80

# ---------------------------------------------------------------------------
# Check 4: TypeScript type checking (skip if no tsconfig.json)
# ---------------------------------------------------------------------------
if [ -f "tsconfig.json" ]; then
    run_check "tsc (TypeScript types)" npx tsc --noEmit
else
    RESULTS+=("SKIP  tsc (TypeScript types) -- no tsconfig.json")
fi

# ---------------------------------------------------------------------------
# Check 5: Frontend tests (skip if no package.json)
# ---------------------------------------------------------------------------
if [ -f "package.json" ]; then
    run_check "npm test (Frontend tests)" npm test -- --coverage
else
    RESULTS+=("SKIP  npm test (Frontend tests) -- no package.json")
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "============================================"
echo "  Pre-Merge Check Summary"
echo "============================================"
for r in "${RESULTS[@]}"; do
    echo "  ${r}"
done
echo "--------------------------------------------"
echo "  Passed: ${PASS}  |  Failed: ${FAIL}"
echo "============================================"

if [ "${FAIL}" -gt 0 ]; then
    echo ""
    echo "One or more checks FAILED. Please fix the issues before merging."
    exit 1
fi

echo ""
echo "All checks passed!"
exit 0
