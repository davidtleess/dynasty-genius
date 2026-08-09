# B21 schedules RED v6 — independent CLEAR

Date: 2026-08-09 ET
Reviewer: Codex, independent source-integrity lane
Layer: 1 — ingestion
Cleared pin: `38fceec11f9a4d623b53dee986fb59efe96fbf12429e18a2950190c9eca9cb86`
Verdict: **CLEAR FOR GREEN**

## Checks run

- Recomputed SHA-256: exact match.
- File length: 1,062 lines.
- Focused pytest: **55 failed / 1 disclosed pass**, true exit 1, zero setup/collection errors.
  Every failure is the intended missing-module RED; D1 is the disclosed generic-stream guard.
- Ruff: clean.
- Full suite `--collect-only`: **5,050 collected**, zero collection errors, 25.05 seconds.
- Read Claude's complete v6 disposition and the full changed source-time contract region.
- Re-ran the immutable upstream measurement at `nfldata` commit
  `793d10a99154e8e21240ef03554a0366f98dbe21` against the v6 fixture.

## Why it is clear

The RED now contracts the actual source boundary rather than an inferred one:

- one exact global nflverse Parquet offering, with `(season, week)` only a derived projection;
- raw provider bytes retained before parsing;
- provider URL and served-URL identity, retrieval provenance and transport failures;
- independent value-losslessness oracle and recomputable ordered schema hash;
- strict duplicate/identifier/type/score/date/time validation with positive controls;
- measured non-null `gametime` domain (`HH:MM` only), with the prior ISO mistake now a refused
  mutant;
- provider-unpublished `gametime` accepted and retained verbatim in both physical forms the
  CSV-to-Parquet boundary may materialize;
- scores retained without invented completion/finality status;
- content-addressed vintages, idempotent replay, check/vintage distinction and last-good marker;
- atomic failure behavior, containment and backup-manifest coverage; and
- runnable injected-transport CLI without real network use in tests.

## Requested upstream measurements, completed

Against the immutable 2,175,368-byte CSV snapshot (SHA-256 `5486814f…`):

- **7,548 rows / 46 columns**.
- Fixture vs source schema: **46 / 46 names, exact ordered equality**; no missing or extra names and
  no first-order mismatch.
- `gameday`: **0 empty**, **7,548 / 7,548 valid ISO dates**, zero invalid forms.
- `gametime`: **259 empty**, **7,289 non-empty**, **7,289 / 7,289 strict `HH:MM`**, zero other
  non-empty forms.
- 2026 subset: 272 rows in that upstream revision; zero empty `gametime`.

The v6 module docstring still labels `gameday` nullability as unmeasured because the follow-up
arrived after the pin froze. That prose is stale but non-blocking: the contract's strict `gameday`
behavior is exactly supported by the completed measurement above. Do not mutate the cleared RED
pin merely to update historical prose; carry the measured facts into the GREEN evidence and final
catalog entry.

## GREEN handoff

Implement the dedicated route against this exact pin. Then return one GREEN review packet with the
changed-file pins, focused tests, Ruff and full-suite results. After behavioral CLEAR, perform the
first authorized live 2026 capture and provide the complete ticket acceptance packet: provider and
retrieval time; raw path/bytes/hash; canonical path/count/schema hash/vintage; marker and failed
attempt behavior; replay proof; catalog update; clean-tree test; explicit-path commit/push; and
terminal exact-SHA CI.

The current user instruction is the active authority for the first B21 capture and later configured
paid CFBD calls. Scheduler installation, provider contact and downstream use remain separate.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
