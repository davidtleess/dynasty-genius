# Automatic market track record implementation plan

**Implementation disposition:** All scoped implementation, review and activation work completed September10eveningET. Dedicated tracker active. Root took final runner/CLI integration and outcome-helper ownership after DG224's initial handoff. First actual launch and natural scheduled retry succeeded. David subsequently approved source landing with “Go”; its receipt is maintained in `/Users/davidleess/dg-build/AUTOMATIC-TRACK-RECORD-HANDOFF-2026-09-10.md`. No builder assignment remains open; DG221's visual gate remains separate.

Landing preparation found an existing cached copy of the pinned Ruff0.15.12. Eight import-order/unused-import findings were corrected without changing behavior; complete production-source lint passes. The active release retains its original immutable bytes and evidence recipe. No dependency was installed or runtime restarted.

**Goal:** Start and maintain an honest prospective record of the saved Dynasty Genius forecast versus subsequent FantasyCalc movement, using the existing declared policy and collectors.

**Architecture:** Read the existing FC point-in-time store and its own capture receipt without writing to either. Preserve independently verified market captures in a new private immutable archive. Create a new research reading that explicitly pairs an unchanged forecast with newer market prices, enroll once per forecast/policy identity, and run the existing endpoint selector/grader only when due. A dedicated root-owned LaunchAgent executes this runner; existing jobs, production API, hosted data and model output are untouched.

**Tech stack:** Existing Python, SQLite read-only transactions, pytest, macOS launchd; no new dependencies or browser changes.

## Authorization and isolation

David approved the new automatic-recording milestone with “Go for it.” This covers building and activating the dedicated tracking behavior, after review and verification; it does not authorize model promotion, changing rankings, publication, shared store writes or unrelated job changes. DG221 remains independently blocked on locked-Mac visual inspection. DG222–225 start clean on `4f93a3807c479260b7c374dcae27ee441e4db1a4`. Read AGENTS/PRODUCT; never access frontend-studio. Existing tests: root baseline89 passed,1 skipped.

## Ownership

- Root DG222: contract; `src/dynasty_genius/ranking/market_ranks.py` narrow opt-in forward-date reader; new `src/dynasty_genius/capture/forward_market_reading.py`; `tests/ranking/test_forward_market_reading.py`; integration, private runtime packaging/config and a new dedicated LaunchAgent outside existing scanned `ops/launchd` directory; final source/real-runtime acceptance.
- Claude54281 DG223: new complete-capture adapter/store and focused tests, exact API frozen after source preflight. Preserve all raw/unresolved records and original capture times; no network collection or existing-store constructor.
- Claude54331 DG224: new automatic enrollment/due-evaluation runner and focused tests, using existing pure enrollment builder, immutable stores and market graders. No alternative policy or scoring engine.
- Claude54410 DG225: read-only independent scientific/source/runtime review and root acceptance challenge; no builder edits.

## Root tests and implementation

1. Add failing tests for a later dated market capture: original reader still refuses, explicit forward reader admits valid chronological sources without modifying forecast/report/ownership, rejects earlier/inconsistent dates and all original malformed inputs.
2. Add minimal opt-in forward reading entry point, preserving the original same-day default and all other validation.
3. Add failing tests for building a NEW SnapshotBundle from a verified template: original source bytes unchanged, new market/date/hash correctly bound, arbitrary or contradictory source evidence refused, comparison unchanged, whole unpriced population retained, old template untouched.
4. Implement the pure forward-reading factory and verified template loader. Keep capture evidence within the store's allowed artifact schema; do not relax original archive validation.
5. Exercise the existing immutable save/read and enrollment builders on that new bundle with absent football baseline/schedule. The new market study must not masquerade as a fresh preseason football freeze.

## Builder acceptance

Capture: readonly SQLite mode and consistent transaction; own FC receipt validates source/settings/date/time, all row hashes and whole capture count/store hash; no main-chain exit-code gate. Historical data without sufficient contemporaneous evidence remains unavailable. Missing differs from zero; reject duplicate IDs, mixed capture times, partial capture and wrong settings. Immutable own copies and exact duplicate reuse, source corruption refuses.

Runner: validate policy/source identities; never rewrite prior readings; first eligible forecast identity primary, repeated market dates not independent forecast samples. Freeze any legitimate historical comparator at enrollment; absent history yields descriptive-only association. Deterministic first compatible endpoint in declared30/90-day windows; no early grade, post-hoc baseline insertion, selective success reporting or future capture. One failed stream does not hide other valid work. Catch up after sleep/login with concurrency lock and idempotency; receipt per invocation, with next due time and distinct waiting/error states.

## Integration and activation

1. Review builder paths/hashes and findings before explicit integration; root independently recomputes one actual capture and complete paired ranks.
2. Run affected source/store/runner/CLI tests, Python static checks and existing contract compatibility. No repeat of passed historical model studies.
3. Rehearse real new capture/read/enrollment against private paths. Preserve original archive and shared FC rows. Verify all modeled values/forecasts and original dates survive, while market is fresh at actual enrollment time. Current Sleeper settings were fetched and agree exactly with the saved report's scoring/slots.
4. Package immutable reviewed runtime source and config, separate from worktrees and shared production stores. Retain source hashes and truthful dirty-code provenance. Install only a uniquely named tracker LaunchAgent, outside the existing guard's scanned template directory; 15-minute checks and login catch-up. Do not change existing schedules.
5. Observe one genuine launchd invocation through capture/enrollment/waiting receipt and a second idempotent or due-safe behavior check. Future30/90-day outcomes cannot be claimed tested live; synthetic controlled histories verify those paths.
6. Independently verify installed-job preservation and source/store/record hashes, then record tests, static analysis, real-surface (CLI/launchd; no UI changed), review and cleanup receipts. Explain ongoing collection and earliest evaluation dates to David, with no edge claim.

## Limits

No hosted UI change or new forecast pipeline is included. This tests market anticipation, not trade returns, lineup gains, or five-year dynasty value. Retrospective normalized data is not relabelled original HTTP evidence; collector publication time is not invented from retrieval time. If a source cannot satisfy declared evidence, record why and preserve the future evidence needed to proceed rather than weaken scientific rules.
