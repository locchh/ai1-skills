# Environment Configuration Guide

## Environment Differences Overview

| Setting | Development | Staging | Production |
|---------|------------|---------|------------|
| **Debug mode** | Enabled | Enabled | Disabled |
| **Log level** | DEBUG | INFO | WARNING |
| **Database** | Local PostgreSQL | Cloud PostgreSQL (small) | Cloud PostgreSQL (HA cluster) |
| **Redis** | Local Redis | Cloud Redis (single node) | Cloud Redis (cluster, replicas) |
| **CORS origins** | `localhost:*` | `staging.example.com` | `app.example.com` |
| **SSL/TLS** | Self-signed / None | Managed cert | Managed cert |
| **Replicas** | 1 | 1-2 | 3+ (auto-scaling) |
| **Secrets source** | `.env` file | CI/CD secrets | Vault / cloud secret manager |
| **Email sending** | Console backend | Sandbox / Mailtrap | Production SMTP / SES |
| **Feature flags** | All enabled | Selective | Controlled rollout |
| **Error tracking** | Console output | Sentry (staging project) | Sentry (production project) |
| **Rate limiting** | Disabled | Relaxed | Strict |
| **Backups** | None | Daily | Continuous + daily snapshots |

---

## Environment Variable Management Strategy

### Naming Convention

Use a consistent prefix and uppercase with underscores:

```
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<generated>
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
```

### Variable Categories

1. **Application config** (`APP_*`): Runtime behavior settings.
2. **Database config** (`DATABASE_*`): Connection strings, pool sizes.
3. **External services** (`SENTRY_DSN`, `SMTP_*`, `AWS_*`): Third-party integrations.
4. **Feature flags** (`FF_*`): Feature toggles per environment.

### Loading Order (highest priority first)

1. Process environment variables (set by orchestrator / CI/CD)
2. `.env.<environment>` file (e.g., `.env.staging`)
3. `.env` file (local development defaults)
4. Application code defaults (hardcoded fallbacks for non-sensitive values only)

---

## Secrets Management

### Core Principles

- **Never commit secrets to version control.** Not even in "private" repos.
- **Never log secrets.** Redact them in application logs and error reports.
- **Rotate secrets regularly.** At minimum quarterly, immediately if compromised.
- **Use short-lived credentials** where possible (e.g., IAM roles, OIDC tokens).

### Per-Environment Strategy

| Environment | Method |
|-------------|--------|
| Development | `.env` file (gitignored), dummy/local credentials only |
| Staging | GitHub Actions secrets or CI/CD platform secret store |
| Production | Cloud secret manager (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault) |

### Secrets Rotation Procedure

1. Generate the new secret value.
2. Update the secret in the secret manager.
3. Deploy the application (it reads the new secret on startup).
4. Verify the application functions correctly with the new secret.
5. Revoke the old secret value.

---

## Database Configuration Per Environment

```yaml
# Development
DATABASE_URL: "postgresql://dev:dev@localhost:5432/app_dev"
DATABASE_POOL_SIZE: 5
DATABASE_ECHO_SQL: true   # Log all SQL queries for debugging

# Staging
DATABASE_URL: "postgresql://app:${DB_PASSWORD}@staging-db.internal:5432/app_staging"
DATABASE_POOL_SIZE: 10
DATABASE_ECHO_SQL: false

# Production
DATABASE_URL: "postgresql://app:${DB_PASSWORD}@prod-db.internal:5432/app_prod"
DATABASE_POOL_SIZE: 20
DATABASE_POOL_OVERFLOW: 10
DATABASE_ECHO_SQL: false
DATABASE_SSL_MODE: require
```

---

## Feature Flags Per Environment

Feature flags allow decoupling deployment from release. Configure defaults per
environment so that new features can be tested in staging before production.

```python
FEATURE_FLAGS = {
    "new_checkout_flow": {
        "development": True,    # Always on for local development
        "staging": True,        # Enabled for QA testing
        "production": False,    # Disabled until rollout approved
    },
    "v2_search_api": {
        "development": True,
        "staging": True,
        "production": "10%",    # Gradual percentage-based rollout
    },
}
```

---

## Logging Configuration Per Environment

```python
LOGGING = {
    "development": {
        "level": "DEBUG",
        "format": "text",       # Human-readable for terminal output
        "output": "stdout",
    },
    "staging": {
        "level": "INFO",
        "format": "json",       # Structured for log aggregation
        "output": "stdout",     # Collected by container runtime
    },
    "production": {
        "level": "WARNING",
        "format": "json",
        "output": "stdout",
        "sample_debug": 0.01,   # Sample 1% of requests at DEBUG level
    },
}
```

Structured (JSON) logging is required in staging and production so that log
aggregation tools (e.g., Datadog, ELK, CloudWatch) can parse and index fields
for searching and alerting.
