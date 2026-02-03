# Runbook: High Error Rate

## Severity: P1/P2 depending on error percentage and user impact

---

## Symptoms

- Error rate exceeds normal baseline (e.g., >1% of requests returning 5xx).
- Alerting systems firing for elevated error counts or error ratio.
- User-facing error pages or degraded functionality reported.
- Spike in error tracking system (Sentry, Bugsnag, etc.) event volume.
- Downstream services reporting failures from this service.

## Likely Causes

| Cause | Indicators |
|---|---|
| **Bad deployment** | Errors started at deploy time, new code paths failing |
| **External dependency failure** | Errors correlate with dependency health, timeout patterns |
| **Data corruption or schema mismatch** | Serialization errors, unexpected null values, type errors |
| **Configuration change** | Errors after config update, environment variable missing |
| **Infrastructure issue** | Errors across multiple services, DNS or network problems |
| **Traffic spike** | Rate limiting triggered, resource exhaustion under load |

## Investigation Steps

### 1. Identify the error pattern
```bash
# Fetch recent error logs
./scripts/fetch-logs.sh <service-name> 15m

# Group errors by type/message
./scripts/fetch-logs.sh <service-name> 15m | grep "ERROR" | \
  sort | uniq -c | sort -rn | head -20
```

### 2. Correlate with timeline
- When did the error rate start increasing?
- Was there a deployment, config change, or infrastructure event at that time?
- Are the errors affecting all endpoints or specific ones?

```bash
# Check recent deployments
kubectl rollout history deployment/<service>
# Check recent config changes
kubectl get configmap <service-config> -o yaml
```

### 3. Check error details
- Review stack traces in error tracking system (Sentry, etc.).
- Identify the specific exception types and code paths involved.
- Check if errors are uniform or varied (single root cause vs. cascading).

### 4. Check dependencies
```bash
./scripts/health-check-all-services.sh
# Check external API status pages
# Review dependency timeout and error metrics
```

### 5. Check for data issues
```sql
-- Look for unexpected data patterns
SELECT count(*), error_type FROM recent_errors
GROUP BY error_type ORDER BY count DESC;
-- Check for null or malformed records if data corruption suspected
```

## Remediation Actions

### Rollback if caused by a bad deploy
```bash
kubectl rollout undo deployment/<service>
# Verify error rate decreases after rollback
```

### Disable via feature flag
- If the error is in a specific feature, disable it via feature flag.
- This allows the rest of the service to continue operating normally.
```bash
# Example: toggle feature flag in configuration
curl -X POST https://config.internal/flags/<flag-name>/disable
```

### Fix forward (if rollback is not feasible)
- Apply a hotfix if the root cause is identified and the fix is small.
- Deploy through expedited pipeline with peer review.
- Monitor closely after deployment.

### Dependency failure mitigation
- Enable cached or fallback responses for the failing dependency.
- Activate circuit breaker if not already tripped.
- Contact the dependency team or check their status page.

### Data issue mitigation
- Identify and quarantine corrupted records.
- Run data validation and repair scripts.
- Add defensive checks to handle malformed data gracefully.

## Prevention Measures

- Deploy with canary or progressive rollout strategies.
- Implement automated rollback on error rate thresholds.
- Use feature flags for all new features to enable quick disabling.
- Add comprehensive error handling and fallback paths.
- Run integration tests against production-like data before deploying.
- Monitor error rate trends, not just absolute thresholds.
- Maintain up-to-date status pages for all dependencies.
- Add request validation at service boundaries to reject bad data early.
- Conduct regular chaos engineering exercises to test failure modes.
