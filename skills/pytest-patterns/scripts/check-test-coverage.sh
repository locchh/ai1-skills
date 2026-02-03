#!/bin/bash
set -euo pipefail

# check-test-coverage.sh
# Run pytest with coverage analysis and enforce minimum coverage threshold.

COVERAGE_THRESHOLD="${COVERAGE_THRESHOLD:-80}"
SOURCE_DIR="${1:-src}"

echo "============================================"
echo "  Running Tests with Coverage Analysis"
echo "============================================"
echo "Source directory: ${SOURCE_DIR}"
echo "Coverage threshold: ${COVERAGE_THRESHOLD}%"
echo ""

if ! command -v pytest &>/dev/null; then
    echo "ERROR: pytest is not installed. Install it with: pip install pytest pytest-cov"
    exit 1
fi

EXIT_CODE=0
pytest --cov="${SOURCE_DIR}" \
       --cov-report=term-missing \
       --cov-fail-under="${COVERAGE_THRESHOLD}" \
       -v || EXIT_CODE=$?

echo ""
echo "============================================"
if [ "${EXIT_CODE}" -eq 0 ]; then
    echo "  PASS: All tests passed with >=${COVERAGE_THRESHOLD}% coverage"
else
    echo "  FAIL: Tests failed or coverage below ${COVERAGE_THRESHOLD}%"
fi
echo "============================================"

exit "${EXIT_CODE}"
