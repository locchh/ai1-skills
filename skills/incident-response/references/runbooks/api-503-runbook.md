# Runbook: API Returning 503 Service Unavailable

## Severity: P1/P2 depending on scope

---

## Symptoms

- API endpoints returning HTTP 503 (Service Unavailable) responses.
- Health check endpoints failing or timing out.
- Load balancer marking backends as unhealthy.
- Increased latency preceding the 503 errors.
- Alerts firing for elevated error rates or dropped availability.

## Likely Causes

| Cause | Indicators |
|---|---|
| **Server overload** | CPU/memory at capacity, request queue growing, thread pool exhausted |
| **Dependency down** | Upstream service or database unreachable, connection timeouts in logs |
| **Bad deployment** | Errors started immediately after a deploy, new pods crash-looping |
| **Connection pool exhaustion** | "Cannot acquire connection" errors, all connections in use |
| **Circuit breaker open** | Circuit breaker tripped for a downstream dependency |
| **Resource limits** | Container OOM-killed, disk full, file descriptor limit reached |

## Investigation Steps

### 1. Confirm the scope
```bash
# Check which endpoints are affected
curl -s -o /dev/null -w "%{http_code}" https://api.example.com/health
# Check from multiple regions if applicable
```

### 2. Check application logs
```bash
# Fetch recent error logs for the service
./scripts/fetch-logs.sh <service-name> 30m | grep -i "error\|503\|timeout\|refused"
```

### 3. Check service health and resource usage
```bash
# Container resource usage
docker stats --no-stream <container-name>
# Kubernetes pod status
kubectl get pods -l app=<service> -o wide
kubectl top pods -l app=<service>
```

### 4. Check dependencies
```bash
# Run health checks on all downstream services
./scripts/health-check-all-services.sh
# Check database connectivity
pg_isready -h <db-host> -p 5432
```

### 5. Check recent deployments
```bash
# List recent deployments
kubectl rollout history deployment/<service>
# Check deploy timestamps against error start time
git log --oneline --since="2 hours ago"
```

## Remediation Actions

### Immediate: Restart the service
```bash
kubectl rollout restart deployment/<service>
# or
docker-compose restart <service>
```

### Scale up if under load
```bash
kubectl scale deployment/<service> --replicas=<N>
```

### Rollback if caused by a bad deploy
```bash
kubectl rollout undo deployment/<service>
# or deploy the previous known-good version explicitly
```

### Failover if a dependency is down
- Enable fallback/cached responses if available.
- Switch traffic to a secondary region or replica.
- Activate circuit breaker manual override to return degraded responses.

### Connection pool exhaustion
- Restart to release connections.
- Increase pool size in configuration and redeploy.
- Identify and terminate long-running or leaked connections.

## Prevention Measures

- Implement and monitor health checks for all dependencies.
- Set up autoscaling policies based on CPU, memory, and request queue depth.
- Use circuit breakers for all external dependency calls.
- Load test before major releases to validate capacity.
- Maintain canary or blue-green deployment strategies to catch issues early.
- Set resource requests and limits on all containers.
- Add connection pool monitoring and alerting.
- Ensure graceful degradation paths exist for all critical dependencies.
