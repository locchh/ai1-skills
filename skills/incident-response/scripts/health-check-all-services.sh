#!/usr/bin/env bash
set -euo pipefail

# Health check all configured services and report a status table.
# Exit code 1 if any service is unhealthy.
# Usage: ./health-check-all-services.sh [config-file]

CONFIG_FILE="${1:-}"
TIMEOUT_SECONDS=5
ANY_UNHEALTHY=0

# Default services to check if no config file is provided.
# Override by passing a config file with one "name url" pair per line.
DEFAULT_SERVICES=(
    "api-gateway http://localhost:8000/health"
    "user-service http://localhost:8001/health"
    "payment-service http://localhost:8002/health"
    "notification-service http://localhost:8003/health"
    "database http://localhost:5432"
    "redis http://localhost:6379"
)

# Load services from config file or use defaults
declare -a SERVICES
if [[ -n "${CONFIG_FILE}" && -f "${CONFIG_FILE}" ]]; then
    mapfile -t SERVICES < "${CONFIG_FILE}"
else
    SERVICES=("${DEFAULT_SERVICES[@]}")
fi

echo "============================================================"
echo " Service Health Check Report"
echo " Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"
printf "%-25s %-10s %-8s %s\n" "SERVICE" "STATUS" "CODE" "RESPONSE TIME"
echo "------------------------------------------------------------"

for entry in "${SERVICES[@]}"; do
    # Skip empty lines and comments
    [[ -z "${entry}" || "${entry}" =~ ^# ]] && continue

    SERVICE_NAME=$(echo "${entry}" | awk '{print $1}')
    SERVICE_URL=$(echo "${entry}" | awk '{print $2}')

    if [[ -z "${SERVICE_URL}" ]]; then
        printf "%-25s %-10s %-8s %s\n" "${SERVICE_NAME}" "UNKNOWN" "---" "No URL configured"
        continue
    fi

    START_TIME=$(date +%s%N)

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time "${TIMEOUT_SECONDS}" \
        --connect-timeout "${TIMEOUT_SECONDS}" \
        "${SERVICE_URL}" 2>/dev/null) || HTTP_CODE="000"

    END_TIME=$(date +%s%N)
    ELAPSED_MS=$(( (END_TIME - START_TIME) / 1000000 ))

    if [[ "${HTTP_CODE}" =~ ^2[0-9]{2}$ ]]; then
        STATUS="HEALTHY"
    elif [[ "${HTTP_CODE}" == "000" ]]; then
        STATUS="DOWN"
        ANY_UNHEALTHY=1
    else
        STATUS="UNHEALTHY"
        ANY_UNHEALTHY=1
    fi

    printf "%-25s %-10s %-8s %s\n" "${SERVICE_NAME}" "${STATUS}" "${HTTP_CODE}" "${ELAPSED_MS}ms"
done

echo "============================================================"

if [[ "${ANY_UNHEALTHY}" -eq 1 ]]; then
    echo "RESULT: One or more services are unhealthy."
    exit 1
else
    echo "RESULT: All services are healthy."
    exit 0
fi
