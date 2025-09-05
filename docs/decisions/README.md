# Decision Log (ADRs)

This folder contains Architecture Decision Records (ADRs) documenting key decisions as the system evolves. Use the template to propose, discuss, and record changes.

- ADR-0000-template.md — use this to author new ADRs
- ADR-0001-signal-schema.md — normalized Signal dataclass for strategies
- ADR-0002-risk-engine-guardrails.md — risk sizing, daily loss cap, kill-switch
- ADR-0003-metrics-naming.md — metrics names and labels conventions
- ADR-0004-offline-determinism.md — deterministic offline demo acceptance
- ADR-0005-branching-and-releases.md — phase branches, PRs, tags

## How to add an ADR
1. Copy `ADR-0000-template.md` to the next number (e.g., `ADR-0006-<topic>.md`).
2. Fill in Context, Decision, Consequences, and References.
3. Submit a PR referencing the change and link the ADR.
4. After merge, update this README list.

Status keywords:
- Proposed — for review
- Accepted — merged and active
- Superseded — replaced by a newer ADR (link it)

