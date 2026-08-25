# Consultant brief — CODEX CONSULTANT · the false-statement sweep

From Claude (write lane, DG cockpit) · `[w#r1-r2-group]` · 2026-08-19
**Read-only engagement. Findings deliverable. No product code, no tests, no artifacts, no commits.**

You are outside the DG cockpit. Your output is **advisory input** — it is not a CLEAR and it does not
authorize work. The binding reviewer for this thread is the in-cockpit Codex seat (`02`
§Falsification #4). You are a second, independent pass — not a substitute for it.

## Bootstrap

Run the DG bootstrap reading order: `docs/governance/02-agent-operating-loop.md`,
`00-product-constitution.md`, `05-layer-doctrine.md` in full, `01-north-star-architecture.md`,
`03-code-hygiene-policy.md`, then `AGENT_SYNC.md` from line 1 to `⏹ END CURRENT BOARD`.
Repo: `/Users/davidleess/dynasty-genius-product`.

## The seed — two verified instances of one defect class

Both reproduced this session against
`app/data/valuation_runtime/universe_pvo_runtime.json` (`captured_at 2026-08-18T13:30:03Z`, 12,222 rows):

**Instance 1 — a false provenance marker and a false caveat.**
`src/dynasty_genius/pvo_assembler.py:458-465`. When neither an Engine A prior nor an Engine B score is
available, the code sets `dynasty_value_score = None`, then sets `dvs_engine = "A"` as a "provenance
marker" and appends *"Insufficient professional season data — Engine A prospect score used as prior."*
Measured: **114 rows carry that caveat and 0 of them have an `nfl_draft_round`.** No prior existed.
The row asserts a mechanism that did not run.

**Instance 2 — a status computed from the wrong variable.**
`app/api/routes/players.py:40,249,283-291`. `modeled` is derived from `engine_path` alone, never from
whether a score exists. A row with `engine_path = ENGINE_B` and a null score is served as
`model_status = "modeled"`, `degradation = None`, inside a `PlayerModelLane` whose
`dynasty_value_score` is `None`.

**The class:** *the code states something it has not verified, and a downstream reader — human or
machine — cannot tell.* A related instance was already found on 2026-08-18 in a different subsystem:
`feature_refresh` graded itself `fresh` on `embedded_timestamp_fresh` while its own
`stream_provenance` recorded participation as `loaded_empty`.

## Your question

**Where else in this codebase does a field, status, flag, or caveat assert something the code has not
established?**

Sweep at minimum: the valuation assembler and its engine-routing branches; every API route that
derives a status, grade, freshness, or availability field; provenance and lineage writers; capture and
scorer status markers; health and degradation reporting; and any `*_status` / `*_grade` / `*_engine` /
`*_verified` / `*_fresh` field on a served contract.

For each finding return: the exact `file:line`, the claim the code makes, what is actually true, a
**reproduced count** of affected rows or runs, the cost to David in one sentence, and a severity
(`BLOCKER` / `WARN` / `STYLE` per `02` §Loop-control budget).

## Explicitly out of scope — do not propose these

- Any feature-store rebuild. That diagnosis was raised on 2026-08-18 and **refuted**; do not revive it.
- Any model change, re-run, promotion, or retraining. `decision_supported=false` stands.
- Market-superiority work, the decision-grade gate, frontend bundle freshness, the grounding build, or
  any large unvalidated model push. David has ruled all of these **not before Week 1**.
- Any new governance layer, registry, or review protocol.

## Constraints

- Read-only. Probes and measurement only.
- Every claim carries `file:line`, a query, or a reproduced count. `02` §Falsification #2 — uncited is
  speculation and cannot support a finding.
- Rank findings most severe first. Name explicitly anything you could **not** verify rather than
  filling the gap.
- Do not read, write, or touch `/Users/davidleess/frontend-studio` (standing wall TW29-WALL-35).
- The worktree is dirty with other lanes' parked work. Preserve it; read nothing you were not pointed at.
