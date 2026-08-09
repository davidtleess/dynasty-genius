# B21 schedules RED v3 — independent review (Codex)

Date: 2026-08-08
Layer: Layer 1 — ingestion
Artifact: `tests/contract/test_b21_schedules_capture_red.py`
Reviewed SHA-256: `c2a6181088ec864dced57a3d4736edde51b54426785d8e143700524c3a0166ea`
Implementer disposition: `docs/agent-ledger/evidence/2026-08-08/b21_schedules_red_v3_disposition_claude_v1.md`

## Verdict

**NOT CLEAR.** The global-Parquet offering model, raw-byte boundary, derived week projection,
revision-aware checks/vintages, last-good behavior, finality ceiling, executable route, canonical
layout and backup requirement are materially repaired. Five bounded contract defects remain. GREEN
does not open on this pin.

## Independent gates

- Recomputed pin: `c2a6181088ec864dced57a3d4736edde51b54426785d8e143700524c3a0166ea`.
- Focused pytest: **36 failed / 1 disclosed pass**, true exit 1, zero setup/collection errors. The
  pass is D1, the explicit generic-stream regression guard.
- Ruff: **All checks passed**.
- Fixture probe independent of `_mod()`: `_parquet([])` produced a valid 135-byte empty Parquet
  payload, so G1's empty fixture itself is satisfiable.
- Read all 752 lines and the full 192-line implementing-lane disposition.

## Consolidated findings

### F1 — “Lossless” can pass while every retained value is corrupted

At lines 371–384, F1 compares only the set of column names. S4 at lines 263–270 compares the
store's parser to the same store's persisted parser output. A GREEN can retain every key while
replacing `result`, venue, weather, cross-ids, rest values, or any other non-asserted value, and both
tests pass. G7 checks only scores and absence of derived vocabulary.

Required repair: compare the parsed record values against an independent `pl.read_parquet(...)`
projection for the complete wide fixture (with an explicit JSON-safe normalization for datetimes or
other non-JSON scalars if needed). Include at least one extra-field sentinel whose corruption fails.
Raw-byte retention remains necessary but does not make the canonical parsed record lossless.

### F2 — schema evidence is self-confirming and incomplete

At lines 387–400, `schema_hash` is compared only to another value returned by the same GREEN, and
the dtype map is checked for only `home_score`. A constant schema hash plus a partly fabricated dtype
map passes. This cannot support the acceptance packet's measured schema hash.

Required repair: derive the expected ordered `{column: dtype}` map independently from the fixture,
assert the full map, and pin a deterministic hash of that exact canonical representation. Add a
schema-change counterexample proving a dtype change changes the hash. Do not pin the external field
count; the dynamic full-schema assertion is the right choice.

### F3 — the duplicate guard covers conflicts, not duplicates

G3 at lines 461–473 uses two rows with different scores. A GREEN that rejects only conflicting
duplicates but accepts two byte-identical rows with the same `game_id` passes, inflating week and
vintage row counts. The earlier review explicitly required duplicate/conflicting-ID handling.

Required repair: state the source-boundary rule and test it. The simplest fail-closed contract is
that any repeated `game_id`, identical or conflicting, raises `duplicate_game_id`; a different
lossless rule is acceptable only if it preserves both observations explicitly and cannot inflate a
week slice silently.

### F4 — required-field types and source/retrieval timestamps can still be invalid

The semantic matrix tests score dtypes and `observed_at`, but not the other required source fields.
Lines 403–428 require only column presence; lines 476–489 exercise only one home/away inconsistency;
lines 515–523 validate only `observed_at`. S6 at lines 288–295 accepts one valid collaborator
`retrieved_at` but never rejects a naive or malformed one. A GREEN can therefore accept string/null
`season` or `week`, malformed `gameday`/`gametime`, and a naive/unparseable transport timestamp while
still satisfying this suite. Those fields directly drive the week projection and future cadence
input.

Required repair: add positive-controlled fail-closed cases for the required non-score fields' core
types/ranges (at minimum integer `season`/`week`, non-empty teams/game id, parseable source date/time)
and for malformed/naive `retrieved_at`. Stable error codes should distinguish schema/type, source
schedule-time, and retrieval-provenance failures.

### F5 — provider identity and capture authority remain unresolved in the contract text

The current user instruction says to treat the supplied plan as the source of user intent, and that
plan explicitly states: “David’s prior authority covers sanctioned ingestion at determined cadence,
including paid CFBD calls under the existing subscription.” Lines 82–87 instead preserve a lane
disagreement and flag the free B21 capture back to David. The current prompt resolves this for the
work requested; retaining the stale gate would block the ticket's mandatory first capture.

Separately, direct `record_offering(...)` calls all pass `source_url=EXPECTED_URL`, but no negative
test proves another URL/provider identity is refused. A route-specific store that accepts an
arbitrary caller-supplied source URL permits silent substitution, forbidden by the north-star source
adapter rules.

Required repair: replace the authority paragraph with the current scoped authority (actual B21
capture authorized; scheduler installation, provider contact, and downstream use remain separate),
and add a negative provider-identity test requiring the exact B21 asset URL or an explicitly
governed equivalent identity.

## Falsification matrix delta

| Input / invariant | Probe on this pin | Result |
|---|---|---|
| Valid nominal global Parquet | `_scored()` + S/D/A positive controls | Covered |
| Empty / malformed | G1/G2; empty-fixture construction probed independently | Covered |
| Missing required column | F3 positive + negative | Covered |
| Full value preservation | Mutant keeps all keys but corrupts extra values | **Not caught** |
| Full schema/dtype evidence | Mutant returns constant hash and partial dtype map | **Not caught** |
| Duplicate/conflict | Conflicting duplicate caught; identical duplicate mutant | **Not caught** |
| Wrong required-field type / malformed source time | Only scores and one ID mismatch covered | **Not caught** |
| Malformed retrieval provenance | Only valid `retrieved_at` covered | **Not caught** |
| Wrong provider identity | All fixtures pass the expected URL | **Not caught** |
| No-change / replay / prior-vintage survival | A1–A5, E1 | Covered by contract |
| Finality overclaim | D2/G7 | Covered by contract |
| Traversal / backup manifest | P1/P2 | Covered by contract |

## Accept condition

Return one revised immutable RED pin that repairs F1–F5, with a per-finding disposition, true focused
pytest exit/count, Ruff result, and zero collection errors. No GREEN before the independent CLEAR.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
