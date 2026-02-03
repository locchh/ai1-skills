#!/usr/bin/env bash
# quick-diagnosis.sh -- Rapid health check for common production issues.
#
# Checks backend health, database connections, Redis status,
# Docker containers, and recent error logs.
#
# Usage:
#   ./scripts/quick-diagnosis.sh
#   ./scripts/quick-diagnosis.sh --backend-url http://localhost:8000
#   ./scripts/quick-diagnosis.sh --db-host localhost --db-user app_user --db-name app_db

set -euo pipefail

# --- Configuration (override via environment or flags) ---
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-app_user}"
DB_NAME="${DB_NAME:-app_db}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-backend-app}"
LOG_SINCE="${LOG_SINCE:-15m}"

# --- Parse optional flags ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-url) BACKEND_URL="$2"; shift 2 ;;
    --db-host)     DB_HOST="$2"; shift 2 ;;
    --db-user)     DB_USER="$2"; shift 2 ;;
    --db-name)     DB_NAME="$2"; shift 2 ;;
    --redis-host)  REDIS_HOST="$2"; shift 2 ;;
    --container)   BACKEND_CONTAINER="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

divider() { echo ""; echo "======== $1 ========"; }

# --- 1. Backend Health Endpoint ---
divider "Backend Health"
if curl -sf --max-time 5 "${BACKEND_URL}/health" 2>/dev/null; then
  echo ""
  echo "[OK] Health endpoint responded."
else
  echo "[FAIL] Health endpoint unreachable or returned error."
fi

echo ""
echo "Readiness check:"
if curl -sf --max-time 5 "${BACKEND_URL}/ready" 2>/dev/null; then
  echo ""
  echo "[OK] Readiness endpoint responded."
else
  echo "[FAIL] Readiness endpoint unreachable or returned error."
fi

# --- 2. Database Connectivity and Slow Queries ---
divider "PostgreSQL"
if command -v psql &>/dev/null; then
  echo "Active connections by state:"
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
    "SELECT state, count(*) FROM pg_stat_activity WHERE datname = '$DB_NAME' GROUP BY state ORDER BY count DESC;" \
    2>&1 || echo "[FAIL] Could not query pg_stat_activity."

  echo ""
  echo "Queries running longer than 5 seconds:"
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
    "SELECT pid, now() - query_start AS duration, left(query, 80) AS query_preview
     FROM pg_stat_activity
     WHERE (now() - query_start) > interval '5 seconds' AND state != 'idle'
     ORDER BY duration DESC LIMIT 5;" \
    2>&1 || echo "[FAIL] Could not query slow queries."
else
  echo "[SKIP] psql not found. Install postgresql-client to enable database checks."
fi

# --- 3. Redis Connectivity and Memory ---
divider "Redis"
if command -v redis-cli &>/dev/null; then
  PONG=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>&1)
  if [ "$PONG" = "PONG" ]; then
    echo "[OK] Redis responded to PING."
  else
    echo "[FAIL] Redis did not respond. Output: $PONG"
  fi

  echo ""
  echo "Memory usage:"
  redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" info memory 2>/dev/null \
    | grep -E "used_memory_human|maxmemory_human|mem_fragmentation_ratio" \
    || echo "[FAIL] Could not retrieve Redis memory info."

  echo ""
  echo "Connected clients:"
  redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" info clients 2>/dev/null \
    | grep -E "connected_clients|blocked_clients" \
    || echo "[FAIL] Could not retrieve Redis client info."
else
  echo "[SKIP] redis-cli not found. Install redis-tools to enable Redis checks."
fi

# --- 4. Docker Container Status ---
divider "Docker Containers"
if command -v docker &>/dev/null; then
  echo "Running containers:"
  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>&1 \
    || echo "[FAIL] Could not list containers."

  echo ""
  echo "Resource usage:"
  docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>&1 \
    || echo "[FAIL] Could not retrieve container stats."

  echo ""
  echo "Recently exited containers:"
  docker ps -a --filter "status=exited" --format "table {{.Names}}\t{{.Status}}" 2>&1 \
    | head -6 || true
else
  echo "[SKIP] docker not found."
fi

# --- 5. Recent Error Logs ---
divider "Recent Error Logs (last ${LOG_SINCE})"
if command -v docker &>/dev/null && docker ps --format "{{.Names}}" | grep -q "^${BACKEND_CONTAINER}$"; then
  ERROR_COUNT=$(docker logs --since "$LOG_SINCE" "$BACKEND_CONTAINER" 2>&1 \
    | grep -ci "error\|exception\|critical\|traceback" || true)
  echo "Error/exception count in last ${LOG_SINCE}: ${ERROR_COUNT}"

  if [ "$ERROR_COUNT" -gt 0 ]; then
    echo ""
    echo "Last 10 error lines:"
    docker logs --since "$LOG_SINCE" "$BACKEND_CONTAINER" 2>&1 \
      | grep -i "error\|exception\|critical\|traceback" \
      | tail -10
  fi
else
  echo "[SKIP] Container '${BACKEND_CONTAINER}' not found or docker unavailable."
fi

divider "Diagnosis Complete"
echo "Review any [FAIL] items above for immediate attention."
