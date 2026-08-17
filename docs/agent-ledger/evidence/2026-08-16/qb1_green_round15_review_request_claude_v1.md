# QB-1 GREEN round-15 review request — Claude (write lane)

Date: 2026-08-16 ET
Authority: David's bounded word (pbp parse seam per your registration read +
the read-only wall census), persisted in the round-15 transition (revision
89, open snapshot `bae7112c…`). Fresh rerun held on your explicit CLEAR.
Layer: 2 curation at the raw-to-parsed admission seam.
Study execution: NOT run. H2 QB rushing remains UNDER TEST with no result.

## Round-15 pins (stable, submitted for review)

- `src/dynasty_genius/adapters/nflreadpy_qb_adapter.py`
  `021be2073d6d9609d2b0c2cf376c82d792df2c287e13cf0e262a67cdde3dbe44`
- `src/dynasty_genius/eval/qb_validation/execution.py`
  `12df03a0258c62f375675cfa7b068ba4564db83e2474da29959ef1537831e3e8`
- `tests/contract/test_qb1_green_correction_contracts.py`
  `a75dbc64b1d90a5d2d505963ad8a8a50990c7834259cbfc30e497c9f14f74d17`

Diff vs the round-15 open snapshot: exactly the three authorized files. Your
numstat governs churn.

## Implementation — the registration-read boundary, exactly, at the RULED ordering

1. **One parser:** the adapter's ingestion `_parse` closure refactored into
   the public `parse_validation_pbp` — REG filter + the pinned
   `VALIDATION_PARSED_RENAMES["pbp"]` rename, the adapter's own table; the
   ingestion path now passes `parse=parse_validation_pbp` (single source,
   contract-pinned by source inspection). Named `manifest_column_missing`
   refusal when the parse's own source columns are absent — so re-parsing an
   already-parsed frame REFUSES (normalize-once enforced by refusal, not by
   convention), and the REG filter's `source_unavailable` guard is preserved.
2. **The seam:** `admit_and_load_validation_pool` applies the shared parse to
   the read-back copy after receipt admission and **BEFORE the F1 source
   gate** — your provisional ordering finding `[w#8rrmbv1d-1]` accepted and
   implemented mid-round, zero dispute (my first ordering parsed after the
   gate; it was fixture-driven and wrong against the pinned boundary). The
   parse is unconditional; the only skip is an absent pbp entry, which the
   gate itself refuses by name — no conditional-bypass predicate. A named
   ingest refusal crosses the F33 wall as the same-named study failure.
   Hash-before-parse preserved; raw bytes contract-verified untouched.
3. **Seven R15 contracts:** seam-parses-readback + touches-nothing-else (raw
   bytes byte-identical, other datasets' frames untouched, provenance
   preserved) · single-source-parser · shape + non-REG exclusion + input
   non-mutation · reparse-refuses-named · missing-source-columns refuse
   named THROUGH the seam · zero-REG-rows refuse named · **the gate-spy
   ordering contract you requested** (`test_r15_source_gate_receives_parsed_
   pbp`: the F1 gate receives offense_team / no posteam / REG-only).
   Launder-test fixture updated to a parseable pbp fake so it still tests
   completeness-laundering (stated openly).

## Census at the pins above

- Correction contracts **141/141** · five-file bundle **695** ·
  Ruff/compile/diff-check clean · full-suite tally in the ADDENDUM.

## THE AUTHORIZED WALL CENSUS — results (durable:
`qb1_composition_wall_census_claude_v1.py` + its recorded output)

- **Per-dataset pinned-column census: ZERO walls across all seven datasets**
  — pbp parses to 508,914 REG rows with `offense_team` satisfying the gate;
  weekly/season_summary/players/rosters/ff_playerids/draft_picks all OK.
  **The pbp wall is closed on the real store.**
- **Composition probe: ONE remaining wall found** —
  `stat_value_invalid: weekly row [1026]: unusable identity player_id=nan
  season=2015`. This is the MATRIX's own weekly row validator
  (`study_matrix._validated_weekly_row`, study_matrix.py:117-137, called at
  :242) — a SECOND consumer of the same 192 provider placeholder rows the
  R14 ruling excluded from the LABEL input only ("the full pool continues
  unchanged to build_study_matrix"). The matrix's §5 all-position validation
  refuses unusable identity itself. `study_matrix.py` is OUTSIDE round-15
  scope — nothing was touched; this needs your registration read (does the
  §5 aggregation's row validation admit the ruled placeholder entity class
  by the same 17-zero predicate, or something else?) and a David word.
- Probe-timing disclosure: the census launched minutes before the ordering
  reorder; frame CONTENT is identical under both orderings (the delta is
  refusal precedence only), so the wall findings transfer — stated rather
  than assumed silently.
- No registered metric, statistic, or readout was computed to completion,
  read, or persisted (the probe discards any completed result unread; this
  run refused before completion regardless).

## Boundary

No rerun (held on your CLEAR — a rerun today fails closed at the matrix
wall), no input mutation, no registration/pin/gate change, no commit, no
push.

## ADDENDUM — full-suite tally

Full suite at the pins above (pinned 3.14.4; exit captured unpiped):
**6,143 passed / 15 failed / 12 skipped in 11:29.** All 15 verified BY NAME
in the standing UNTRACKED `test_governed_cadence_inputs_red.py` — zero
tracked failures, zero collection errors. Arithmetic reconciles: 6,136 (R14)
+ 7 R15 contracts = 6,143.
