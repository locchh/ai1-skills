#!/bin/bash
set -euo pipefail

# run-e2e-with-report.sh
# Run Playwright E2E tests and generate an HTML report.

echo "============================================"
echo "  Running Playwright E2E Tests"
echo "============================================"
echo ""

EXIT_CODE=0
npx playwright test "$@" || EXIT_CODE=$?

echo ""
echo "Generating HTML report..."
npx playwright show-report --host 0.0.0.0 &>/dev/null &
REPORT_PID=$!

# In CI environments, skip opening the report in a browser.
if [ -z "${CI:-}" ]; then
    echo "Opening report in browser..."
    npx playwright show-report
else
    echo "CI detected -- skipping interactive report."
    echo "HTML report saved to playwright-report/index.html"
    kill "${REPORT_PID}" 2>/dev/null || true
fi

echo ""
if [ "${EXIT_CODE}" -eq 0 ]; then
    echo "PASS: All E2E tests passed."
else
    echo "FAIL: Some E2E tests failed. See the report for details."
fi

exit "${EXIT_CODE}"
