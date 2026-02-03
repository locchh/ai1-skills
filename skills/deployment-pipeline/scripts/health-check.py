#!/usr/bin/env python3
"""
Health Check Script

Verifies that the application and its dependencies (database, Redis) are healthy.
Exits with code 0 if all services are healthy, 1 if any service is unhealthy.

Usage:
    python health-check.py --url https://app.example.com
    python health-check.py --url https://app.example.com --retries 10 --delay 5
"""

import argparse
import sys
import time
import urllib.error
import urllib.request
import json


def check_http_health(base_url: str) -> dict:
    """Check the HTTP health endpoint of the application."""
    url = f"{base_url.rstrip('/')}/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            return {"service": "http", "healthy": True, "detail": body}
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        return {"service": "http", "healthy": False, "detail": str(e)}


def check_database(base_url: str) -> dict:
    """Check database connectivity via the application's health endpoint."""
    url = f"{base_url.rstrip('/')}/health/db"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            healthy = body.get("status") == "ok"
            return {"service": "database", "healthy": healthy, "detail": body}
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        return {"service": "database", "healthy": False, "detail": str(e)}


def check_redis(base_url: str) -> dict:
    """Check Redis connectivity via the application's health endpoint."""
    url = f"{base_url.rstrip('/')}/health/redis"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            healthy = body.get("status") == "ok"
            return {"service": "redis", "healthy": healthy, "detail": body}
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        return {"service": "redis", "healthy": False, "detail": str(e)}


def run_health_checks(base_url: str) -> list[dict]:
    """Run all health checks and return results."""
    checks = [
        check_http_health(base_url),
        check_database(base_url),
        check_redis(base_url),
    ]
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Application health checker")
    parser.add_argument("--url", required=True, help="Base URL of the application")
    parser.add_argument("--retries", type=int, default=1, help="Number of retry attempts")
    parser.add_argument("--delay", type=int, default=3, help="Seconds between retries")
    args = parser.parse_args()

    all_healthy = False

    for attempt in range(1, args.retries + 1):
        print(f"=== Health Check (attempt {attempt}/{args.retries}) ===")
        results = run_health_checks(args.url)

        for r in results:
            status = "HEALTHY" if r["healthy"] else "UNHEALTHY"
            print(f"  [{status}] {r['service']}: {r['detail']}")

        all_healthy = all(r["healthy"] for r in results)
        if all_healthy:
            break

        if attempt < args.retries:
            print(f"  Retrying in {args.delay}s...")
            time.sleep(args.delay)

    print()
    if all_healthy:
        print("All services are healthy.")
        sys.exit(0)
    else:
        print("ERROR: One or more services are unhealthy.")
        sys.exit(1)


if __name__ == "__main__":
    main()
