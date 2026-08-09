# Contracts windowed-capture RED outline review — Codex v1

Date: 2026-08-08 07:56 EDT  
Artifact reviewed: Claude wire packet `[w#2zqnmzzo-1]`  
Result: **NOT CLEAR — nine contract holes; scope ruling (c) is accepted and no longer disputed**

## Checks performed

- Re-read the accepted scope/cadence ruling and Claude’s W/X/Y/Z outline.
- Re-read the current runner, `build_streams()`, guarded snapshot entrypoint, export commit-point implementation, daily-control manifest, and the untracked candidate plist.
- Reproduced the current spec topology and the private-data boundary.
- Checked the two stored contracts vintages and their current run-derived IDs.

## Findings

### F1 — X1 contradicts Y1

X1 says default execution runs only inside the current window and is `not_due` outside it. Y1 says the first invocation after a missed window captures late. Both cannot be true without an explicit state machine.

Pin: before window = `not_due`; open unsatisfied window = `due_on_time`; closed unsatisfied window = `due_late` with immutable compliance `missed`; successfully captured target = `satisfied` and no-op thereafter. `due_late` executes exactly once. `--only` continues to narrow and never bypasses these states.

### F2 — W2’s source-literal grep is another proxy test

A scan for `2026-03-15` proves only that one spelling is absent. A hardcoded date can appear through a mapping, constructor default, or different literal.

Pin behaviorally: production resolution requires an injected/versioned anchor registry; missing season/anchor refuses; no production fallback synthesizes a date; adding the next season’s anchor changes data only, not Python. Fixtures may legitimately contain dates and must not be banned by source text.

### F3 — idempotence begins after durable target satisfaction, not invocation

X2 says the second invocation is a no-op but does not distinguish a successful first run from a failed one. A failed fetch/DB/export must remain retryable. A DB commit followed by export/marker failure must not create a second vintage on retry.

Pin a deterministic target identity or equivalent durable target ledger, with fault injection at raw-write, DB-commit, export-write, and ready-marker boundaries. The target becomes satisfied only when the consumer commit point is durable. Retry must recover the first accepted bytes where they exist, not silently refetch different bytes under the same target identity.

### F4 — “full payload” needs a behavioral evidence contract, not a predicate grep

The raw payload and normalized table have different legitimate semantics: raw preserves every upstream row/byte; normalized contracts already collapse exact duplicates under a governed rule. A source scan for `year_signed`/`is_active` would be brittle and could ban valid schema declarations or tests.

Pin: injected old, unknown-term, and current rows all survive in the raw artifact; normalized output differs only under the already-governed exact-duplicate collapse; raw hash/count reconcile to the fetched records; no scope/status predicate changes inclusion.

### F5 — Y2 conflates historical compliance with current acquisition status

One March target may remain historically `missed` while a later catch-up is a valid current acquisition and the September target later succeeds on time. “Can never be current” is too broad.

Pin per-target immutable compliance (`on_time` or `missed`) separately from acquisition transport/freshness and from the aggregate next-obligation state. A late capture may make source data currently available; it may never rewrite that target’s historical compliance.

### F6 — Z1’s literal count will rot; Z2’s “only path” is overbroad

“Exactly 12” becomes false when a new seasonal spec lands. And lower-level guarded helpers (`run_usage_capture(specs=(CONTRACTS,))`, `capture_snapshot_stream`) are legitimate paths even if one CLI owns production execution.

Pin the axis partition: every `build_streams()` spec maps exactly once to seasonal or snapshot execution based on `capture_axis`; the current measured count is 12+1 as an anti-rot assertion, not the eternal topology contract. The dedicated contracts CLI is the only controller/scheduler-facing production entrypoint, not the only callable helper.

### F7 — Z4 asks one manifest to both omit and retain contracts

With a separate contracts consumer commit point, the seasonal ready manifest should intentionally stop claiming contracts. “Must not drop contracts from the next ready manifest” contradicts Z3.

Pin artifact ownership explicitly: the seasonal ready marker names seasonal exports only; a contracts-specific ready marker remains independently readable and points to the latest immutable per-vintage normalized artifact. Historical raw/store vintages remain forever. Do not republish the entire accumulated contracts table into every seasonal run or every contracts run.

### F8 — the two real vintages cannot be CI fixtures and are not anchor-satisfied by inference

The stored DB/raw files are private/gitignored machine state. A committed RED that requires them recreates the clean-runner failure just repaired. Their run-derived snapshot IDs carry no `(season, anchor_id)` declaration, so silently assigning either to a 2026 target would infer provenance.

Pin synthetic no-delete/migration behavior in CI. Use a private local acceptance check for the two real IDs/hashes. Classify both existing vintages as `legacy_unassigned` (retained forever, satisfying no annual target) unless David separately authorizes an explicit mapping.

### F9 — Z6 is a closeout boundary, not a runtime RED

No repository test can prove `launchctl` was not invoked, and the untracked plist is excluded user work. A test that scans for plist text would be another proxy.

Keep “no plist edit/install” as explicit path-scope and post-action machine-state verification. The RED may prove the code is callable and never self-installs; installation remains a separate David-gated act.

## Required response

Return a revised RED outline that disposes F1–F9. No RED or GREEN until the outline is CLEAR. Gemini telemetry may add operational facts but does not adjudicate this technical contract.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result. Nothing here bears on it.
