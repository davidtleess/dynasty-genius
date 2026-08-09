# B21 schedules RED review — Codex v1

Date: 2026-08-08
Layer: Layer 1 ingestion
Reviewed artifact: `tests/contract/test_b21_schedules_capture_red.py`
Reviewed SHA-256: `057194a7967575ddbc219fb0669af715b288adb6d01d7ad34fa8426ed0fe748d`

Verdict: **NOT CLEAR**.

## Findings

1. **Finality is not sourced.** The fixtures encode a non-null score as `final`, but B21 exposes no
   authoritative terminal-status or game-end field. During the source's frequent in-season
   publication cycle, a populated score can be an interim score. B21 may retain score/result
   observations, but it cannot emit a verified week-completion fact from score presence alone.
   Until separate governed terminal evidence is injected, the honest state is
   `result_observed_unverified` / completion `undetermined`.

2. **The raw source boundary is absent.** The proposed module accepts already-parsed `rows`. The RED
   does not pin exact provider bytes, a raw content hash, a fetch/CLI intake boundary, a canonical
   disk path, or raw-before-parse behavior. That repeats the central defect in the withdrawn RED and
   would allow B21 to close as pipeline tooling without capturing B21.

3. **The expected baseline has no provenance.** `freeze_expected_baseline` accepts an arbitrary
   tuple of IDs and records no source vintage ID, content hash, or freeze time. Independence means
   independence from the *current evaluation offering*, not independence from the schedule source.
   Freeze expected membership from an earlier accepted schedule vintage and bind the baseline to
   that exact vintage/hash. Reject deriving it from the offering being evaluated.

4. **Atomicity is only modeled in memory.** `ScheduleStore.in_memory()` plus a production
   `fail_at` argument does not exercise a filesystem/metadata/marker transaction and introduces a
   test-only control into the production signature. Use injected failing storage collaborators and
   assert canonical on-disk outcomes. Reconcile the route-level outcome too: a failed offering/check
   audit must survive rollback while no successful vintage, index, or ready marker is published.

5. **The source-neutral schema is under-specified.** Six schedule fields are insufficient for the
   accepted B21 scope. Pin game type, kickoff date/time, teams, scores/result, raw hash, capture
   identity, exact content-vintage identity, and provenance—without Realized Outcome vocabulary.

6. **An executable dedicated route is not pinned.** A descriptor does not prove that the source can
   run. Require a real dedicated CLI/entrypoint and dedicated ready marker/metadata ledger while
   keeping B21 out of generic `build_streams()`.

## C6 ruling

Do not union partial vintages. The entire expected game membership must occur in one exact content
vintage. But that vintage does not prove games are terminal from scores alone. C6 becomes a valid
completion rule only when the exact vintage is joined to independently governed terminal evidence.
If such evidence never exists, completion remains honestly undetermined.

## Source-first close condition

The B21 ticket closes only after RED/GREEN **and the first actual 2026 NFL schedule capture** in the
same slice, with measured row/schema counts, raw/content hashes, canonical paths, marker truth, and
idempotent replay evidence. Code alone is not a B21 landing.
