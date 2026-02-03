# Post-Mortem / Root Cause Analysis Report

---

## Incident Metadata

| Field | Value |
|---|---|
| **Incident ID** | INC-YYYY-NNNN |
| **Date** | YYYY-MM-DD |
| **Duration** | HH:MM (from detection to resolution) |
| **Severity** | P1 / P2 / P3 / P4 |
| **Services Affected** | [List affected services] |
| **User Impact** | [Describe user-facing impact, estimated affected users/requests] |
| **Incident Commander** | [Name] |
| **Responders** | [Names and roles] |
| **Status** | Draft / In Review / Final |

---

## Executive Summary

[2-3 sentence summary of what happened, the impact, and how it was resolved.]

---

## Timeline

All times in UTC.

| Time | Event |
|---|---|
| HH:MM | **Detection**: [How the incident was detected - alert, user report, etc.] |
| HH:MM | **Triage**: [Initial assessment and severity assignment] |
| HH:MM | **Escalation**: [Who was paged, what teams were engaged] |
| HH:MM | **Investigation**: [Key findings during investigation] |
| HH:MM | **Mitigation**: [Temporary fix applied to reduce impact] |
| HH:MM | **Resolution**: [Permanent fix deployed or root cause fully addressed] |
| HH:MM | **Monitoring**: [Confirmation that the issue is fully resolved] |

---

## Root Cause Analysis

### What happened

[Detailed technical description of what went wrong.]

### 5 Whys Analysis

1. **Why** did [the observed failure] happen?
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

[One clear statement of the root cause identified through the analysis above.]

---

## Contributing Factors

- [Factor 1: e.g., Missing monitoring for the affected component]
- [Factor 2: e.g., Deploy pipeline did not include canary step]
- [Factor 3: e.g., Documentation was outdated for the recovery procedure]
- [Factor 4: e.g., On-call responder was unfamiliar with the service]

---

## Impact Assessment

| Metric | Value |
|---|---|
| **Total downtime** | [Duration] |
| **Requests affected** | [Count or percentage] |
| **Users affected** | [Count or percentage] |
| **Revenue impact** | [Estimated, if applicable] |
| **SLA impact** | [SLA budget consumed, remaining budget] |
| **Data loss** | [Yes/No, details if applicable] |

---

## What Went Well

- [Thing 1: e.g., Alerting fired within 2 minutes of the issue starting]
- [Thing 2: e.g., Runbook was accurate and helped speed up mitigation]
- [Thing 3: e.g., Cross-team communication was clear and timely]
- [Thing 4: e.g., Rollback procedure worked as expected]

---

## What Could Be Improved

- [Thing 1: e.g., Detection took too long because monitoring was missing for this path]
- [Thing 2: e.g., Escalation was delayed because the on-call rotation was unclear]
- [Thing 3: e.g., The mitigation steps were not documented]
- [Thing 4: e.g., There was no automated rollback for this deploy type]

---

## Action Items

| ID | Action | Owner | Priority | Deadline | Status |
|---|---|---|---|---|---|
| AI-1 | [Add monitoring for the affected component] | [Name] | High | YYYY-MM-DD | Open |
| AI-2 | [Add canary deployment for this service] | [Name] | High | YYYY-MM-DD | Open |
| AI-3 | [Update runbook with new recovery steps] | [Name] | Medium | YYYY-MM-DD | Open |
| AI-4 | [Add integration test for the failure scenario] | [Name] | Medium | YYYY-MM-DD | Open |
| AI-5 | [Conduct training on incident response for new team members] | [Name] | Low | YYYY-MM-DD | Open |

---

## Lessons Learned

- [Lesson 1: e.g., Canary deployments would have caught this before full rollout]
- [Lesson 2: e.g., We need health checks that cover downstream dependencies]
- [Lesson 3: e.g., Runbooks should be reviewed quarterly to stay current]

---

## Appendix

### Relevant Logs

```
[Paste key log excerpts here]
```

### Relevant Metrics / Graphs

[Link to or embed relevant dashboards or screenshots]

### Related Incidents

- [Link to similar past incidents, if any]

---

*This post-mortem follows a blameless culture. The goal is to understand systemic issues and improve, not to assign blame to individuals.*
