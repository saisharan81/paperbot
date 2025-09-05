# ADR-0005: Branching & Releases

Status: Accepted

## Context
We iterate in phases. Clear branching helps ship small changes with reviews.

## Decision
- Use phase branches: `phase-<N>` and sub-branches (e.g., `phase-2.1-cleanup`).
- Open PRs from phase branches into `main` with checklist (tests pass, runbook/docs/STATE updated).
- Tag releases after merging stable phases.

## Consequences
- Predictable workflow; easier rollbacks.

## References
- `codex/STATE.json` — living pointer to next_task and KPIs
