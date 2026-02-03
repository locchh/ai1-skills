# Architecture Decision Record: [ADR-NNN] [Title]

## Status

**[Proposed | Accepted | Deprecated | Superseded by ADR-NNN]**

## Date

[YYYY-MM-DD]

## Context

Describe the situation that led to this decision. Include:
- What problem or requirement triggered this decision?
- What constraints exist (technical, organizational, timeline)?
- What assumptions are we making?
- What is the current state (if changing existing architecture)?

## Decision

State the decision clearly in one or two sentences.

> We will [decision statement].

## Options Considered

### Option A: [Name]

**Description:** [How it works]

**Pros:**
- [advantage 1]
- [advantage 2]

**Cons:**
- [disadvantage 1]
- [disadvantage 2]

**Evaluation:**
| Criterion | Score (1-5) |
|-----------|------------|
| Maintainability | [N] |
| Testability | [N] |
| Performance | [N] |
| Team Familiarity | [N] |
| Ecosystem Maturity | [N] |
| **Total** | **[N]** |

### Option B: [Name]

[Same structure as Option A]

### Option C: [Name] (if applicable)

[Same structure as Option A]

## Consequences

### Positive
- [positive consequence 1]
- [positive consequence 2]

### Negative
- [negative consequence 1 — and how we'll mitigate]
- [negative consequence 2 — and how we'll mitigate]

### Neutral
- [neutral observation]

## Implementation Notes

- [Key implementation detail 1]
- [Key implementation detail 2]
- [Migration path if changing existing architecture]

## Related Decisions

- [ADR-NNN: Related decision title]
- [ADR-NNN: Related decision title]

## References

- [Link to relevant documentation]
- [Link to discussion or RFC]

---

## Template Usage Notes

1. **Number ADRs sequentially** — ADR-001, ADR-002, etc.
2. **Never delete ADRs** — mark as Deprecated or Superseded instead
3. **Keep decisions atomic** — one decision per ADR
4. **Evaluation criteria weights** — adjust based on project priorities
5. **Store ADRs in** `docs/architecture/decisions/` or equivalent
6. **Review ADRs quarterly** — are deprecated decisions causing tech debt?
