# Re-review — PlayerProfiler `player_season` pilot protocol v4

**Reviewer:** Codex · **Date:** 2026-08-07 · **Layer:** Layer 1 ingestion inventory

**Reviewed artifact:**
`docs/agent-ledger/evidence/2026-08-07/playerprofiler_player_season_pilot_protocol_claude_v4.md`
at SHA-256 `1da378064fcf84ea0951ac4f851c6d2ea870852df00969e870ed2bd9b6fbb4a8`.
The supplied pin reproduces exactly.

## Verdict

**NOT CLEAR — U1 HIGH, U2 LOW.** T1, T3, and T4 close. T2's intended rule is right but its concrete
schema identity cannot detect two conditions it promises to route to `incomparable`.

No code, David questions/export request, subscriber-data access, production ingest, provider call,
capture, catalog edit, checkbox movement, landing, commit, or push is authorized.

## Direct answers

- **§4.6 truncation disposition is correct.** There is no honest mitigation in the current evidence.
  Restricting `incomplete` to detectable failures, retaining counts/raw bytes, disclosing silent
  truncation as an unmitigated threat to every `changed`, and preserving the no-closure ceiling is
  the right contract. Do not invent a row-count classifier.
- **§4.1's ordering property is partly correct.** First-occurrence-wins is order-dependent within the
  `player_season` key domain and must be preserved for byte-identical extraction. But cross-stream
  ordering cannot change a `player_season` survivor because keys are namespaced with
  `player_season|...` versus `medical|...`.

## U1 — a set cannot detect duplicates or slug-colliding renames · **HIGH**

Section 4.5 defines schema identity as the sorted **set** of `_slug`-normalized column names, then
promises that duplicated or renamed columns make the interval `incomparable`. That representation
cannot enforce the promise:

- a duplicate header collapses in a set, so `['season']` and `['season', 'season']` have the same
  identity;
- distinct raw headers can collide under `_slug`—for example `target-share` and `target share` both
  become `target_share`—so a rename/collision can retain the same normalized set.

Use an order-insensitive identity over the exact raw header **multiset** (or sorted exact header
tuple), and separately fail schema validation when either raw headers duplicate or two distinct raw
headers map to the same slug. Then reorder-only is comparable, while add/remove/rename/raw-duplicate/
slug-collision is `incomparable` before semantic hashing. The manifest should record this canonical
identity and the validation outcome.

## U2 — narrow the dedup ordering statement to the causal domain · **LOW**

The single `seen` set does span both streams in the current loop, but the keys are stream-prefixed:
`player_season|...` and `medical|...`. Medical/player interleaving cannot collide. The shared pure
preparation helper must preserve input order and first-win behavior across `player_season` exports
and rows; it need not reproduce cross-stream interleaving to produce byte-identical N6 rows.

Keep the broader RED/GREEN requirements for identity resolution, normalization, dedup outcome, block
grouping, and digest identity. This correction removes surplus rationale; it does not shrink the
shared-normalization prerequisite.

## Repairs that pass

- The expanded shared pure preparation + digest prerequisite is complete, and the hard-stop framing
  makes clear that neither code change is authorized.
- Production isolation, provenance triple, interval aggregation, raw-only representation handling,
  retention/access, immutable record, and no-closure ceilings remain sound.
- Completeness is now limited to detectable conditions; silent truncation is honestly unmitigated.
- Current code citations are correct.

Return v5 after U1–U2 only. No new data or code is needed for the protocol repair.

**H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
