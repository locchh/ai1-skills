#!/usr/bin/env bash
# =============================================================================
# Deployment Script
# Usage: ./deploy.sh <environment>
#   environment: staging | production
# =============================================================================
set -euo pipefail

ENVIRONMENT="${1:?Usage: $0 <staging|production>}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
REGISTRY="${DOCKER_REGISTRY_URL:-registry.example.com}"
IMAGE_NAME="${REGISTRY}/app:${IMAGE_TAG}"

# Validate environment argument
if [[ "${ENVIRONMENT}" != "staging" && "${ENVIRONMENT}" != "production" ]]; then
    echo "ERROR: Environment must be 'staging' or 'production', got '${ENVIRONMENT}'"
    exit 1
fi

echo "=== Deploying to ${ENVIRONMENT} | Image: ${IMAGE_NAME} ==="

# --- Pre-deployment checks ---------------------------------------------------
echo "[1/6] Running pre-deployment checks..."

# Verify CI passed for this commit (skip in staging for speed)
if [[ "${ENVIRONMENT}" == "production" ]]; then
    echo "  Checking CI status for $(git rev-parse HEAD)..."
    gh run list --commit "$(git rev-parse HEAD)" --status completed --json conclusion -q '.[0].conclusion' | grep -q "success" \
        || { echo "ERROR: CI has not passed for this commit."; exit 1; }
fi

# Run migration dry-run to catch destructive operations
echo "  Running migration dry-run..."
bash "$(dirname "$0")/migration-dry-run.sh"

# --- Build and push Docker image ---------------------------------------------
echo "[2/6] Building Docker image..."
docker build -t "${IMAGE_NAME}" -t "${REGISTRY}/app:latest-${ENVIRONMENT}" .

echo "[3/6] Pushing Docker image to registry..."
docker push "${IMAGE_NAME}"
docker push "${REGISTRY}/app:latest-${ENVIRONMENT}"

# --- Deploy -------------------------------------------------------------------
echo "[4/6] Deploying to ${ENVIRONMENT}..."
if command -v kubectl &>/dev/null && [[ -f "k8s/overlays/${ENVIRONMENT}/kustomization.yaml" ]]; then
    # Kubernetes deployment
    kubectl set image "deployment/app" "app=${IMAGE_NAME}" -n "${ENVIRONMENT}"
    kubectl rollout status "deployment/app" -n "${ENVIRONMENT}" --timeout=300s
else
    # Docker Compose deployment (fallback for simpler setups)
    COMPOSE_FILE="docker-compose.${ENVIRONMENT}.yml"
    IMAGE_TAG="${IMAGE_TAG}" docker compose -f "${COMPOSE_FILE}" pull
    IMAGE_TAG="${IMAGE_TAG}" docker compose -f "${COMPOSE_FILE}" up -d --no-build
fi

# --- Health checks ------------------------------------------------------------
echo "[5/6] Running health checks..."
HEALTH_URL="${HEALTH_URL:-https://${ENVIRONMENT}.example.com}"
python "$(dirname "$0")/health-check.py" --url "${HEALTH_URL}" --retries 10 --delay 5

# --- Smoke tests --------------------------------------------------------------
echo "[6/6] Running smoke tests..."
bash "$(dirname "$0")/smoke-test.sh" "${HEALTH_URL}"

# --- Report -------------------------------------------------------------------
echo ""
echo "============================================="
echo "  Deployment to ${ENVIRONMENT} SUCCEEDED"
echo "  Image: ${IMAGE_NAME}"
echo "  URL:   ${HEALTH_URL}"
echo "============================================="
