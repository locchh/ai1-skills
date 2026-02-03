# Runbook: Database Slowness

## Severity: P2/P3 depending on user impact

---

## Symptoms

- API response times significantly elevated.
- Database query durations exceeding normal thresholds.
- Application timeout errors referencing database operations.
- Connection pool wait times increasing.
- Queued requests building up in the application layer.
- Dashboards showing degraded database performance metrics.

## Likely Causes

| Cause | Indicators |
|---|---|
| **Missing index** | Sequential scans on large tables, specific queries slow while others are fine |
| **Lock contention** | Queries waiting on locks, `pg_stat_activity` shows `Lock` wait events |
| **Connection pool exhaustion** | "Cannot acquire connection" errors, all pool slots in use |
| **Large or unoptimized query** | Single query consuming excessive CPU or I/O, temp files on disk |
| **Replication lag** | Read replicas behind, stale data reported by users |
| **Vacuum/analyze not running** | Table bloat, outdated statistics leading to bad query plans |
| **Disk I/O saturation** | High iowait, slow disk throughput metrics |

## Investigation Steps

### 1. Check active queries and locks
```sql
-- Active queries sorted by duration
SELECT pid, now() - pg_stat_activity.query_start AS duration,
       query, state, wait_event_type, wait_event
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC
LIMIT 20;

-- Check for blocking locks
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_query,
       blocking_activity.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_locks blocking_locks
  ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.relation = blocked_locks.relation
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

### 2. Check slow query log
```bash
# PostgreSQL slow query log (if log_min_duration_statement is set)
tail -200 /var/log/postgresql/postgresql-slow.log

# Or query pg_stat_statements for top offenders
```
```sql
SELECT query, calls, total_exec_time / calls AS avg_time_ms,
       rows / calls AS avg_rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

### 3. Check connection count
```sql
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
SELECT max_conn, used, max_conn - used AS available
FROM (SELECT count(*) AS used FROM pg_stat_activity) t,
     (SELECT setting::int AS max_conn FROM pg_settings WHERE name = 'max_connections') s;
```

### 4. Check table and index health
```sql
-- Tables with high sequential scan ratio (missing index candidates)
SELECT relname, seq_scan, idx_scan,
       CASE WHEN seq_scan + idx_scan > 0
            THEN round(100.0 * seq_scan / (seq_scan + idx_scan), 1)
            ELSE 0 END AS seq_scan_pct
FROM pg_stat_user_tables
WHERE seq_scan + idx_scan > 100
ORDER BY seq_scan_pct DESC
LIMIT 10;
```

## Remediation Actions

### Kill a blocking query
```sql
-- Cancel the query gracefully
SELECT pg_cancel_backend(<blocking_pid>);
-- Force terminate if cancel does not work
SELECT pg_terminate_backend(<blocking_pid>);
```

### Add a missing index
```sql
-- Create index concurrently to avoid locking the table
CREATE INDEX CONCURRENTLY idx_<table>_<column> ON <table> (<column>);
```

### Increase connection pool size
- Update pool configuration (e.g., PgBouncer `max_client_conn`, application `pool_size`).
- Restart the pooler or application to apply changes.
- Monitor to confirm pool wait times decrease.

### Optimize an expensive query
- Run `EXPLAIN (ANALYZE, BUFFERS)` on the slow query to identify bottlenecks.
- Rewrite the query to avoid sequential scans, unnecessary joins, or large sorts.
- Consider materializing frequently accessed aggregations.

### Emergency: reduce load
- Enable read replica routing for read-heavy queries.
- Temporarily disable non-critical background jobs hitting the database.
- Add query timeouts to prevent runaway queries: `SET statement_timeout = '30s';`

## Prevention Measures

- Enable `pg_stat_statements` and review top queries weekly.
- Set `log_min_duration_statement` to capture slow queries (e.g., 500ms).
- Run `ANALYZE` on tables after bulk data changes.
- Configure autovacuum aggressively for high-churn tables.
- Use connection pooling (PgBouncer) in front of the database.
- Set application-level query timeouts on all database calls.
- Add index coverage checks to the CI pipeline for new migrations.
- Monitor connection counts, replication lag, and disk I/O in dashboards.
- Load test database-heavy features before releasing to production.
