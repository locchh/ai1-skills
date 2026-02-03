#!/usr/bin/env python3
"""
Generate an incident report from the post-mortem template.

Usage:
    python generate-incident-report.py --severity P1 --service api-gateway --summary "API returning 503 errors"
    python generate-incident-report.py -s P2 -svc user-service -m "Authentication failures" --output-dir ./reports
"""

import argparse
import os
import sys
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an incident report from the post-mortem template."
    )
    parser.add_argument(
        "--severity", "-s",
        required=True,
        choices=["P1", "P2", "P3", "P4"],
        help="Incident severity level.",
    )
    parser.add_argument(
        "--service", "-svc",
        required=True,
        help="Name of the affected service.",
    )
    parser.add_argument(
        "--summary", "-m",
        required=True,
        help="Brief summary of the incident.",
    )
    parser.add_argument(
        "--responder",
        default=os.environ.get("USER", "unknown"),
        help="Name of the initial responder (default: $USER).",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory to write the report file (default: current directory).",
    )
    return parser.parse_args()


def generate_report(severity: str, service: str, summary: str, responder: str) -> str:
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M UTC")
    incident_id = now.strftime("INC-%Y-%m%d%H%M")

    report = f"""# Post-Mortem / Root Cause Analysis Report

## Incident Metadata

| Field | Value |
|---|---|
| **Incident ID** | {incident_id} |
| **Date** | {date_str} |
| **Duration** | [To be filled after resolution] |
| **Severity** | {severity} |
| **Services Affected** | {service} |
| **User Impact** | [Describe user-facing impact] |
| **Incident Commander** | {responder} |
| **Responders** | {responder} |
| **Status** | Draft |

## Executive Summary

{summary}

[Expand with full details after resolution.]

## Timeline

All times in UTC.

| Time | Event |
|---|---|
| {time_str} | **Detection**: [How the incident was detected] |
| {time_str} | **Triage**: Initial assessment - {severity} severity for {service} |
| | **Escalation**: [Who was paged] |
| | **Investigation**: [Key findings] |
| | **Mitigation**: [Temporary fix applied] |
| | **Resolution**: [Permanent fix deployed] |
| | **Monitoring**: [Confirmation of resolution] |

## Root Cause Analysis

### What happened

[Detailed technical description of what went wrong.]

### 5 Whys Analysis

1. **Why** did the failure occur?
   - Because [direct cause].
2. **Why** did [direct cause] happen?
   - Because [deeper cause].
3. **Why** did [deeper cause] happen?
   - Because [even deeper cause].
4. **Why** did [even deeper cause] happen?
   - Because [systemic cause].
5. **Why** did [systemic cause] happen?
   - Because [root cause].

### Root Cause

[One clear statement of the root cause.]

## Contributing Factors

- [Factor 1]
- [Factor 2]
- [Factor 3]

## Impact Assessment

| Metric | Value |
|---|---|
| **Total downtime** | [Duration] |
| **Requests affected** | [Count or percentage] |
| **Users affected** | [Count or percentage] |
| **Revenue impact** | [Estimated] |
| **SLA impact** | [Budget consumed] |
| **Data loss** | [Yes/No] |

## What Went Well

- [Item 1]
- [Item 2]

## What Could Be Improved

- [Item 1]
- [Item 2]

## Action Items

| ID | Action | Owner | Priority | Deadline | Status |
|---|---|---|---|---|---|
| AI-1 | [Action item] | [Owner] | High | [Date] | Open |
| AI-2 | [Action item] | [Owner] | Medium | [Date] | Open |

## Lessons Learned

- [Lesson 1]
- [Lesson 2]

---

*Generated on {date_str} at {time_str}. This post-mortem follows a blameless culture.*
"""
    return report


def main() -> None:
    args = parse_args()

    report_content = generate_report(
        severity=args.severity,
        service=args.service,
        summary=args.summary,
        responder=args.responder,
    )

    now = datetime.now(timezone.utc)
    filename = now.strftime(f"incident-report-{args.service}-%Y%m%d-%H%M.md")
    output_path = os.path.join(args.output_dir, filename)

    os.makedirs(args.output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Incident report generated: {output_path}")
    print(f"  Severity: {args.severity}")
    print(f"  Service:  {args.service}")
    print(f"  Summary:  {args.summary}")
    print(f"\nRemember to fill in the timeline and root cause analysis after resolution.")


if __name__ == "__main__":
    main()
