#!/usr/bin/env bash
set -euo pipefail

# Fetch recent logs for a service, filtered for errors and warnings.
# Usage: ./fetch-logs.sh <service-name> [time-range] [max-lines]
# Examples:
#   ./fetch-logs.sh api-gateway 30m
#   ./fetch-logs.sh user-service 1h 500

SERVICE_NAME="${1:?Usage: $0 <service-name> [time-range] [max-lines]}"
TIME_RANGE="${2:-30m}"
MAX_LINES="${3:-200}"

echo "=== Fetching logs for '${SERVICE_NAME}' (last ${TIME_RANGE}, max ${MAX_LINES} lines) ==="
echo ""

# Try Docker logs first
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${SERVICE_NAME}$"; then
    echo "[source: docker]"
    docker logs --since "${TIME_RANGE}" --tail "${MAX_LINES}" "${SERVICE_NAME}" 2>&1 \
        | grep -iE "error|warn|crit|fatal|exception|panic|timeout|refused|503|500" \
        || echo "No error/warning lines found in Docker logs."
    exit 0
fi

# Try docker-compose service
if docker compose ps --services 2>/dev/null | grep -q "^${SERVICE_NAME}$"; then
    echo "[source: docker-compose]"
    docker compose logs --since "${TIME_RANGE}" --tail "${MAX_LINES}" "${SERVICE_NAME}" 2>&1 \
        | grep -iE "error|warn|crit|fatal|exception|panic|timeout|refused|503|500" \
        || echo "No error/warning lines found in docker-compose logs."
    exit 0
fi

# Try journalctl for systemd services
if systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
    echo "[source: journalctl]"
    journalctl -u "${SERVICE_NAME}" --since "-${TIME_RANGE}" --no-pager -n "${MAX_LINES}" \
        | grep -iE "error|warn|crit|fatal|exception|panic|timeout|refused|503|500" \
        || echo "No error/warning lines found in journalctl."
    exit 0
fi

# Try kubectl if available
if command -v kubectl &>/dev/null; then
    POD=$(kubectl get pods -l "app=${SERVICE_NAME}" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
    if [[ -n "${POD}" ]]; then
        echo "[source: kubectl]"
        kubectl logs "${POD}" --since="${TIME_RANGE}" --tail="${MAX_LINES}" 2>&1 \
            | grep -iE "error|warn|crit|fatal|exception|panic|timeout|refused|503|500" \
            || echo "No error/warning lines found in kubectl logs."
        exit 0
    fi
fi

echo "ERROR: Service '${SERVICE_NAME}' not found in Docker, docker-compose, systemd, or Kubernetes."
exit 1
