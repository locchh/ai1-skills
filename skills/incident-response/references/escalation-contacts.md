# Escalation Contact Matrix

---

## Severity-Based Escalation Matrix

| Severity | Response Time | Escalation Path | Communication Channel |
|---|---|---|---|
| **P1 - Critical** | 5 minutes | On-call engineer -> Team lead -> Engineering VP | #incident-critical (Slack), War Room (Zoom) |
| **P2 - High** | 15 minutes | On-call engineer -> Team lead | #incident-active (Slack) |
| **P3 - Medium** | 1 hour | On-call engineer | #incident-triage (Slack) |
| **P4 - Low** | Next business day | Team backlog | Team Slack channel |

---

## Service Ownership

| Service | Owning Team | Team Lead | Slack Channel |
|---|---|---|---|
| API Gateway | Platform | [Name] | #team-platform |
| User Service | Identity | [Name] | #team-identity |
| Payment Service | Payments | [Name] | #team-payments |
| Notification Service | Engagement | [Name] | #team-engagement |
| Database (PostgreSQL) | Data Platform | [Name] | #team-data-platform |
| Infrastructure / K8s | SRE | [Name] | #team-sre |
| CDN / Static Assets | Platform | [Name] | #team-platform |
| [Add your service] | [Team] | [Name] | [Channel] |

---

## On-Call Rotation Reference

| Team | Schedule Tool | Rotation Link |
|---|---|---|
| Platform | PagerDuty / Opsgenie | [Link to rotation schedule] |
| Identity | PagerDuty / Opsgenie | [Link to rotation schedule] |
| Payments | PagerDuty / Opsgenie | [Link to rotation schedule] |
| SRE | PagerDuty / Opsgenie | [Link to rotation schedule] |
| [Add your team] | [Tool] | [Link] |

**Current on-call lookup command:**
```bash
# PagerDuty
pd oncall list --schedule-ids <SCHEDULE_ID>
# Opsgenie
opsgenie-cli schedule who-is-on-call --name <schedule-name>
```

---

## Communication Templates

### P1 Incident Declaration
```
@here INCIDENT DECLARED - P1
Service: [service name]
Impact: [brief user impact description]
Status: Investigating
Incident Commander: [name]
War Room: [zoom/meet link]
Updates every: 15 minutes
```

### P2 Incident Notification
```
INCIDENT - P2
Service: [service name]
Impact: [brief user impact description]
Status: Investigating
Lead: [name]
Updates in: #incident-active
```

### Status Update
```
INCIDENT UPDATE - [service name]
Status: [Investigating / Mitigating / Resolved]
Summary: [what we know / what we did]
Next update: [time]
```

---

## External Escalation Contacts

| Provider | Support Portal | Escalation Contact | SLA |
|---|---|---|---|
| AWS | [Support console URL] | TAM: [name/email] | [Business/Enterprise] |
| Cloud Provider | [Support URL] | [Contact] | [Tier] |
| DNS Provider | [Support URL] | [Contact] | [Tier] |
| CDN Provider | [Support URL] | [Contact] | [Tier] |
| [Add provider] | [URL] | [Contact] | [Tier] |

---

*Keep this document updated. Review contacts and rotations at least monthly.*
