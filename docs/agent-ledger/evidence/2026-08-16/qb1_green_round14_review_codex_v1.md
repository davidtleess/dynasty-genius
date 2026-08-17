# QB-1 GREEN Round 14 Independent Review — Codex v1

Date: 2026-08-16 ET  
Verdict: **CLEAR** for the exact revised-placeholder implementation boundary  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`  
Round: `green-review` 14

## Pins and scope

- Claude request SHA-256:
  `3cfa6176839d1822f69e18af045af4cc6169b74a1a8faa78ec3945155ca575e2`.
- Runner SHA-256:
  `8d7d525c1f5da0fa9a7311d0d2fef72353ee63969324d27257cfbcf5c0d87c63`.
- Correction-contract SHA-256:
  `3a9c51f9ec8a2b943871ad9aa8f546166de00468e043a2697b0ffd65b59d039a`.
- Diff from the script-owned Round-14 open snapshot is exactly the two
  authorized files: runner `+67/-31`, contracts `+124/-47`; 269 changed
  lines total. No dependency, configuration, registration, input, gate,
  provider, commit, push, or publication change is present.

## Enumerated independent checks

1. **Exact predicate:** `PLACEHOLDER_D2_COLUMNS` is the three qualifying
   inputs plus all 14 builder-owned `SCORING_COMPONENTS`; independent runtime
   inspection proved 17 unique columns. `_validated_zero` calls the label
   builder's own `_stat_decimal`, so absent, null, malformed, non-finite,
   boolean, lossy, negative-count, and nonzero values are not silently
   classified as placeholders.
2. **Identity and position limbs:** usable player ids and nonmissing positions
   remain in the label input. Names do not participate in the predicate; the
   anonymous, `Team`, and `R.Rodgers` measured shapes classify identically.
3. **Falsification matrix:** an independent executable probe mutated each of
   the 17 D2 columns to nonzero one at a time; 17/17 rows were kept. Null,
   NaN, boolean, malformed string, lossy count, negative count, missing-column,
   identified, and position-bearing mutants were also kept. `pd.NA` identity
   values are conservatively unproven by the seam helper and stay fail-closed.
4. **Placement and pool preservation:** AST inspection found exactly one
   `build_label_table` call, whose first argument is
   `exclude_provider_placeholder_rows(weekly_records)`, and exactly one
   `build_study_matrix` call, whose first argument is the original `pool`.
   Dynamic contracts also prove a new returned list and unchanged input frame.
5. **Real surface:** independent replay reproduced 199,868 weekly rows;
   191,281 REG records; 191,089 label records; exactly 192 exclusions; zero
   residual missing player ids; unchanged weekly-frame digest. The composition
   then failed closed one stage later with
   `manifest_column_missing: pbp: offense_team`. No composition result was
   read or published.
6. **Tests:** independent five-file bundle passed **689/689**. Claude's
   unpiped full suite at the same pins reports **6,136 passed / 15 failed / 12
   skipped**; all 15 are the standing untracked cadence RED, with zero tracked
   failures and zero collection errors.
7. **Static and hygiene:** Ruff on the changed/evidence files, strict Python
   compilation, and `git diff --check` all passed independently.
8. **Authority and product alignment:** the classifier is confined to copied
   label-builder records, the full pool remains intact for §5 matrix/team
   aggregation, and H2 remains UNDER TEST. This CLEAR authorizes only the
   already-granted registered rerun trigger; it is not a ruling on any
   registered contrast and is not commit, push, merge, or publication
   authority.

## Non-blocking WARN and downstream wall

- `R14-W1-PROBE-DOCSTRING-STALE`: the executable real-surface probe's module
  docstring still says `R13`, `236`, and `TEAM`, while its body, runtime output,
  Claude's request, and this independent replay correctly establish R14 and
  192 provider placeholders. This documentation mismatch does not change the
  executed proof or product code, but must be corrected before the probe is
  treated as a clean future citation.
- The newly surfaced `pbp: offense_team` refusal is outside Round 14. The
  admitted raw PBP frame carries `posteam`, while the matrix expects the
  registered parsed rename. It does not negate the placeholder CLEAR. Under
  David's exact trigger, the rerun should execute and is expected to fail
  closed there, producing no registered result; any parse-seam repair requires
  a separate registration read and David word.

## Verdict

**CLEAR.** No Round-14 BLOCKER remains. The revised placeholder predicate is
correct, fail-closed, label-only, and real-surface verified at the submitted
pins. H2 QB rushing remains UNDER TEST pending an actual registered result and
David's separate ruling.
