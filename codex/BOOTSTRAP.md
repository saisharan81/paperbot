# Codex Bootstrap

Start every session with these steps to retain context and progress.

1) Read MASTER_PROMPT.md
   - Understand the role, ideology, end goal, definition of done, and output schema.

2) Read STATE.json
   - Treat it as the single source of truth for phase status, KPIs, and next_task.
   - If `updated_at_utc` is stale, prefer the repository’s latest tests and logs, then update STATE.json.

3) If `next_task` exists, execute it
   - Follow its `plan` and modify the listed `files` only as needed.
   - Keep diffs minimal and focused.
   - On completion, run tests (`pytest -q`) and a short demo if relevant.

4) Update STATE.json
   - Refresh `updated_at_utc`, `phases`, `kpis.last_summary`, and move the pointer:
     - If success, set `next_task` to the next backlog item.
     - Otherwise, refine `next_task` with a smaller, testable scope.

5) Update README Phase Log
   - Insert a new entry between `<!-- PHASE-LOG-START -->` and `<!-- PHASE-LOG-END -->` with:
     - Achievements, hurdles/fixes, and evidence (commands, key logs, metrics curl).

6) Prepare PR
   - Ensure tests pass, acceptance criteria met, and no secrets.
   - Use the PR template checklist to confirm repo memory is updated.

