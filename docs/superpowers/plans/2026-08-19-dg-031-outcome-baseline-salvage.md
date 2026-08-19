# DG-031 — Outcome Baseline Salvage Plan

## Goal and boundary

Rebuild only the two useful contracts identified in frozen branch `0b5b22c`: the league/roster-year
target resolver and the realized-outcome Coverage response. Do not copy commits wholesale and do not
touch health, scoreboard, ledger tooling, rehearsal, shared data, historical closeouts, or Studio.

## Task 1 — RED: league-year target resolution

Edit `tests/contract/test_run_realized_outcome_scoring.py` first.

1. Add a preseason rollover case: roster year 2026, played season 2025, live week 22 resolves to
   `(2026, 1)`.
2. Add an active-season case: roster year and played season both 2026, live week 5 resolves to
   `(2026, 5)`.
3. Add provider-failure cases: a live-week failure falls back to week 1; a required season-provider
   failure remains loud rather than silently grading the wrong year.
4. Add injected-provider isolation: when all providers are supplied, importing or calling
   `nflreadpy` is forbidden.
5. Run only these contracts and observe expected failures against `main`.

## Task 2 — GREEN: minimal resolver

Edit only `scripts/run_realized_outcome_scoring.py`.

1. Keep all time providers injectable.
2. Use `nflreadpy.get_current_season(roster=True)` for the roster/league year and the ordinary
   current-season provider only to detect preseason rollover.
3. Resolve preseason to week 1; otherwise use the live week; retain the existing week-provider
   fail-safe.
4. Run the targeted resolver tests and the complete scorer wiring/contract group.

## Task 3 — RED: Coverage API plus generated-client contract

Edit `tests/contract/test_realized_outcome_scorecard_route.py` first.

1. Add Coverage to the valid artifact fixture and assert all denominators survive the route.
2. Assert the inactive response has a stable Coverage object with nullable counts and empty reason
   maps.
3. Assert malformed Coverage types and unknown fields fail closed with 503.
4. Add a generated-client drift assertion that the OpenAPI schema, `types.gen.ts`, `zod.gen.ts`, and
   `index.ts` all expose Coverage and that the generated Zod response schema parses an honest
   Coverage payload.
5. Run the focused route/client contracts and observe expected failures against `main`.

## Task 4 — GREEN: schema and generated artifacts

1. Add strict `Coverage` to `app/api/routes/realized_outcome_scorecard_models.py` and include it in
   `RealizedOutcomeScorecardResponse` with a stable default.
2. Run `npm --prefix frontend run openapi-gen`; do not hand-edit generated files.
3. Run the focused Python route/drift contracts and a Node/Vitest or TypeScript-backed Zod parse.

## Task 5 — verification and review

1. Run the relevant realized-outcome Python suite, OpenAPI drift contract, Ruff, frontend typecheck,
   lint, banned-language and build.
2. Exercise `/api/realized-outcome/scorecard` against temporary inactive, valid Coverage, and invalid
   Coverage artifacts; never touch the live scorecard.
3. Review `main...HEAD` for scope and `git diff --check`; verify no blocked branch files entered the
   diff and no shared paths were written.
4. Obtain an independent fresh-agent review of the final worktree.
5. Record all autonomy receipts and stop at the human gate; do not commit, push, merge, release, or
   publish.
