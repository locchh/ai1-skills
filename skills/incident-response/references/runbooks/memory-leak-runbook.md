# Runbook: Memory Leak

## Severity: P2/P3 depending on rate of growth and proximity to OOM

---

## Symptoms

- Gradual and continuous increase in memory usage over time (sawtooth pattern absent).
- Container or process memory approaching or hitting configured limits.
- OOM (Out of Memory) kills observed in system logs or container orchestrator events.
- Application becoming unresponsive or slow as memory pressure increases.
- Garbage collection pauses growing longer and more frequent.
- Swap usage increasing on the host.

## Likely Causes

| Cause | Indicators |
|---|---|
| **Unclosed resources** | File handles, database connections, HTTP clients not released |
| **Growing in-memory caches** | Cache size increases without eviction, no TTL configured |
| **Large payload accumulation** | Buffering large request/response bodies in memory |
| **Event listener leaks** | Listeners registered repeatedly without removal |
| **Global state accumulation** | Data appended to module-level or class-level collections |
| **Third-party library bug** | Memory growth in library code, not application code |

## Investigation Steps

### 1. Confirm memory growth pattern
```bash
# Container memory usage over time
docker stats --no-stream <container>
# Kubernetes memory metrics
kubectl top pod -l app=<service>
# Check for OOM events
kubectl get events --field-selector reason=OOMKilled -n <namespace>
dmesg | grep -i "oom\|killed process"
```

### 2. Profile memory usage
```bash
# Python: use tracemalloc or memory_profiler
python -c "import tracemalloc; tracemalloc.start(); ..."
# Python: take a snapshot comparison
# Add to application: tracemalloc.take_snapshot()

# Node.js: capture heap snapshot
kill -USR2 <pid>  # if --heapsnapshot-signal=SIGUSR2 is set
# Node.js: use --inspect and Chrome DevTools
```

### 3. Analyze heap dump
```bash
# Java: capture heap dump
jmap -dump:live,format=b,file=heap.hprof <pid>
# Analyze with Eclipse MAT or jhat
```

### 4. Check resource handle counts
```bash
# Open file descriptors for a process
ls -la /proc/<pid>/fd | wc -l
# Network connections
ss -tnp | grep <pid> | wc -l
```

### 5. Compare memory profiles over time
- Take a memory snapshot at startup, after 1 hour, and after several hours.
- Compare retained object counts and sizes to identify growing allocations.
- Look for objects that should have been garbage collected but persist.

## Remediation Actions

### Immediate: Restart the affected service
```bash
kubectl rollout restart deployment/<service>
# Schedule periodic restarts as a temporary measure if needed
```

### Set memory limits to prevent host impact
```yaml
# Kubernetes resource limits
resources:
  limits:
    memory: "512Mi"
  requests:
    memory: "256Mi"
```

### Fix the leak
- Close resources in `finally` blocks or use context managers (`with` statements).
- Add TTL and max-size eviction to in-memory caches.
- Use weak references for caches or observer patterns where appropriate.
- Stream large payloads instead of buffering them entirely in memory.
- Ensure event listeners are deregistered when no longer needed.

### Reduce impact while investigating
- Scale horizontally to distribute memory pressure across more instances.
- Implement a liveness probe that checks memory usage and restarts unhealthy pods.
- Reduce traffic to the affected service if possible.

## Prevention Measures

- Add memory usage metrics and alerts (e.g., alert when RSS exceeds 80% of limit).
- Use context managers and resource cleanup patterns consistently.
- Configure caches with max size and TTL eviction policies.
- Include memory profiling in load testing and soak testing.
- Set container memory limits on all deployments.
- Run periodic soak tests (extended load tests) to catch slow leaks.
- Review third-party dependencies for known memory issues.
- Add liveness probes that account for memory health.
