# B21 schedules RED v4 — independent review (Codex)

Date: 2026-08-08
Layer: Layer 1 — ingestion
Artifact: `tests/contract/test_b21_schedules_capture_red.py`
Reviewed SHA-256: `abf9ff5f58ab50e8a307a1c9a737f32a99d7674bd33d18c63ad902c08a1bf474`

## Verdict

**NOT CLEAR — one residual coverage class.** F1–F3, provider identity, retrieval provenance and the
authority/document-boundary defect are repaired. F4's symmetric required-field/source-time rule is
still proved only by special cases.

## Independent gates

- Pin recomputed exactly.
- Read all 939 lines and Claude's complete v4 disposition.
- Focused pytest: **47 failed / 1 disclosed pass**, true exit 1, zero setup/collection errors.
- Ruff: **All checks passed**.
- Independent helper probe: 3 rows × 46 columns, 46 ordered dtype pairs, 64-character schema hash,
  and all three lazy required-field mutants construct without collection-time evaluation.

## Residual finding — one side of each symmetric rule can pass as the whole rule

The required source subset contains `game_id`, `gameday`, `gametime`, `away_team` and `home_team`
(lines 163–168). G8's negative cases cover only `away_team` among the two team fields and never cover
an empty/null `game_id` (lines 651–679). G9 mutates only `gameday`; it never mutates `gametime`
(lines 682–693), even though `gametime` is a required source field and the module docstring says the
cadence consumer needs kickoff.

A special-case GREEN can therefore validate `away_team` but accept an empty `home_team`, validate
`gameday` but accept arbitrary `gametime`, and rely on later identifier parsing rather than the
required-field rule for an empty `game_id`; all 48 tests still pass. This is the same “special case
proved as a rule” failure class the current board records from earlier review rounds.

Required repair: extend the existing lazy tables, not the architecture. Prove the rule for both
team fields and `game_id`, and prove source kickoff validation over both required components
(`gameday` and `gametime`, or one combined normalized kickoff parser that necessarily consumes and
rejects invalid values in each). Preserve stable codes and positive controls. Then return one new
pin with focused pytest/Ruff results. No new design surface is requested.

## Checks cleared on this pin

- Independent full-value losslessness and replay equivalence.
- Full ordered dtype map and independently recomputable schema hash with dtype-change counterexample.
- Identical and conflicting duplicate IDs.
- `season`/`week` type/null checks and cause-before-symptom ordering.
- Naive/malformed retrieval timestamps.
- Store-side and transport-side provider identity.
- Global offering, raw bytes, no-change vintages, last-good atomicity, finality ceiling, canonical
  layout and backup-manifest coverage.

The RED correctly contains no authority argument. For execution, the current user instruction is
the active authority source: GREEN and the first B21 capture proceed after RED CLEAR; scheduler,
provider contact and downstream use remain separate.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
