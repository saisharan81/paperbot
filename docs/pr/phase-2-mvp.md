Title: Phase-2 MVP: Decision Log + Structure (LLM scaffolding), tests & demo green

Summary
	•	Create a living Decision Log (ADRs) and link it in docs.
	•	Align repo to Phase-2 MVP structure; add LLM scaffolding (src/paperbot/llm, prompts/decision_v1.md).
	•	Preserve behavior; keep tests (37) and deterministic offline demo green.

Changes (high-level)
	•	ADRs: Signal schema, risk guardrails, metrics naming, offline determinism, branching.
	•	Structure: add llm/agent.py, metrics/llm.py, keep metrics/core.py (graceful bind warn).
	•	Docs: README project tree + Decision Log link; RUNBOOK adds ADR workflow.
	•	State: codex/STATE.json reminder to update decisions each phase.

Evidence
	•	Tests: PYTHONPATH=src pytest -q → 37 passed
	•	Demo: OFFLINE_DEMO=1 PYTHONPATH=src python -m paperbot.main → emits order submitted, fill, and execution demo complete; writes data/ledger.parquet, data/trades.parquet.
	•	Grafana: queries unchanged; labels (strat/side/symbol) already aligned.

Acceptance
	•	Tests pass
	•	Offline demo completes with expected logs
	•	Decision Log present & linked
	•	README + RUNBOOK updated
	•	Branch phase-2-mvp pushed

Risks
	•	Import path drift if more moves later
	•	Dashboard drift if metric names change

