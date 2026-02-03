#!/usr/bin/env bash
# =============================================================================
# Post-Deployment Smoke Tests
# Usage: ./smoke-test.sh <base_url>
# Verifies that critical endpoints are responding correctly after a deployment.
# =============================================================================
set -euo pipefail

BASE_URL="${1:?Usage: $0 <base_url>}"
PASS=0
FAIL=0

check_endpoint() {
    local method="$1" path="$2" expected_status="$3" description="$4"
    local url="${BASE_URL}${path}"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" -X "${method}" "${url}" --max-time 10) || status="000"
    if [[ "${status}" == "${expected_status}" ]]; then
        echo "  PASS  ${method} ${path} -> ${status} (${description})"
        ((PASS++))
    else
        echo "  FAIL  ${method} ${path} -> ${status}, expected ${expected_status} (${description})"
        ((FAIL++))
    fi
}

echo "=== Smoke Tests: ${BASE_URL} ==="

check_endpoint GET  "/health"        200 "Health endpoint"
check_endpoint GET  "/api/v1/status"  200 "API status endpoint"
check_endpoint GET  "/api/v1/users/me" 401 "Auth-protected endpoint returns 401 without token"
check_endpoint GET  "/"              200 "Root page loads"

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"

if [[ "${FAIL}" -gt 0 ]]; then
    echo "ERROR: Smoke tests failed. Investigate immediately."
    exit 1
fi

echo "All smoke tests passed."
