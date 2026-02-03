#!/usr/bin/env bash
# =============================================================================
# Migration Dry-Run Script
# Generates the SQL that would be executed by the next Alembic migration
# and checks for potentially destructive operations.
# =============================================================================
set -euo pipefail

echo "=== Migration Dry-Run ==="

# Generate the SQL for pending migrations without executing them
SQL_OUTPUT=$(alembic upgrade head --sql 2>&1) || {
    echo "ERROR: Alembic failed to generate migration SQL."
    echo "${SQL_OUTPUT}"
    exit 1
}

if [[ -z "${SQL_OUTPUT}" ]]; then
    echo "No pending migrations."
    exit 0
fi

echo "Generated SQL:"
echo "${SQL_OUTPUT}"
echo ""

# Check for destructive operations that require manual review
DESTRUCTIVE_PATTERNS="DROP TABLE|DROP COLUMN|TRUNCATE|DELETE FROM"
if echo "${SQL_OUTPUT}" | grep -iEq "${DESTRUCTIVE_PATTERNS}"; then
    echo "WARNING: Destructive operations detected in migration SQL!"
    echo "The following lines contain potentially dangerous statements:"
    echo "${SQL_OUTPUT}" | grep -iE "${DESTRUCTIVE_PATTERNS}" --color=always
    echo ""
    echo "Please review these changes carefully before proceeding."
    exit 1
fi

echo "Migration dry-run passed. No destructive operations detected."
