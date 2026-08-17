From Claude (write lane) — QB-1 ROUND 17 REVIEW REQUEST: the PRIVATE season_summary aggregate classifier, REAL-SURFACE PROVEN (11/11 at index 1845; full stage-1b law passes); explicit CLEAR or NOT CLEAR requested [w#qb1-exec-1]

## Artifact under review — exact pins (uncommitted, worktree)

Round 17 (run `f8f7551c…`, revision 104, open snapshot `225761ee…`), exact
two-file scope per your transition:

| File | Opening pin | Current pin |
| :-- | :-- | :-- |
| `src/dynasty_genius/eval/qb_validation/study_matrix.py` | `518e4b82…` | `6c607badab90342e9f5508d09278614236be1095fd44702949910a5dca54a89d` |
| `tests/contract/test_qb1_green_correction_contracts.py` | `7407dc6c…` | `200c6deec425c0d2c2c57ffe7f0e904bee3a9925648df9bad589d205307eba22` |

Out-of-scope pins verified byte-identical: `qb_ppg_labels.py` `e5cb3955…` ·
`run_qb1_study.py` `7de911cc…` · frozen wire pair `b3247ec8…`/`fd924eb1…`.
`git diff --check` clean. Round diff = exactly the two scoped files
(study_matrix: +61/−3, the classifier pair + the stage-1b application + its
comment).

## What is implemented (your registration read, exactly)

`_is_provider_season_aggregate_row` + `_exclude_provider_season_aggregate_rows`
— **matrix-PRIVATE** (contract-pinned absent from `qb_ppg_labels`, the runner,
and the `qb` package; deliberately NOT shared with the weekly classifier —
different dataset, different consumed columns, different exact ruled
predicate). The exact five-clause conjunction: missing `player_id` AND valid
REGISTERED study season (`_valid_label_season` ∧ ∈ `_STUDY_SEASONS`) AND
missing `position` AND null `passing_cpoe` AND `games` an exact validated
integer (`_lossless_int` — bool-kind refused) >= 256. Names audit-only.
Applied ONLY to the defensive copied season_summary records after F1
admission, F14/F15, and exact season coverage, immediately before the
stage-1b identity/duplicate/CPOE law. Pool, frame, raw inputs, manifests, and
every other dataset untouched.

## RED-before-GREEN

5 net-new R17 contracts; **4/5 failed pre-implementation** (private-existence/
application · positive control incl. the documented `_lossless_int`
numeric-string fact · 16 one-field mutants · whole-report equality). The 5th
(`test_r17_summary_near_misses_still_refuse_composition`) was **green before
the implementation by construction** — without the classifier every missing-id
row refuses — and is the regression guard proving exclusion never widened;
disclosed, not smoothed. Post-GREEN: **149/149** (144 + 5 reconciles).

Mutant coverage (all KEPT → fall through to the fail-closed law): usable
player_id · position "QB" / " K " · passing_cpoe 0.0 / −2.25 (zero is
CONTENT here — a validated-zero CPOE is a consumed value, so it never
classifies; the weekly 17-zero analogy does not transfer and was not
imported) · season None / NaN / 1990 / 2026 · games None / NaN / 255 / 271.5 /
True / "gales" / column-absent.

## MANDATORY REAL-SURFACE PROOF — the real admitted store

Probe `qb1_summary_aggregate_real_surface_probe_claude_v1.py` (SHA-256
`7cd0cb8946611705389a93a0766a0cae68262666a324f215274397e62da9ca4c`; recorded
output `…_output.txt` `45c8e6655ef7595a3256468e995f82652cd13565a1ce1a13d03d6b5244e70c37`),
mirroring the matrix defensive path byte-for-byte. **PROBE VERDICT: PASS.**

1. **11/11**: exactly the census's 11 league-aggregate rows classify, at the
   exact census indices — **first excluded defensive index 1845**, the
   round-16 rerun's actual refusal point ("Team" 2015–2019 ×4, "R.Rodgers"
   2018 ×1, anonymous 2020–2025 ×6; games 256–272 enumerated per row).
2. **Zero residual** unusable-identity rows among the 21,366 kept.
3. **The FULL stage-1b law replayed over every kept record — identity,
   duplicate, AND CPOE validation — passes**, with 21,366 distinct
   `(player_id, season)` keys (zero duplicates measured). The third wall is
   closed on the real store at this stage.
4. **Admitted frame digest unchanged** before/after; the classifier copies,
   never mutates.
5. **No composition run** — stage-1b replay only; no fold, lane, inference,
   or report. **Identity-domain discipline retained: no claim that no
   non-identity wall remains beyond this stage.**

## Evidence census at the current pins

- Correction contracts **149/149**.
- Five-file bundle **704/704** in 57.46s (your 699 + 5 net-new = 704
  reconciles). Output `qb1_r17_five_file_bundle_claude_v1.txt`
  `612647817ddf6c7211fe2273c3a790e6838c8a9bd73d479c47724ad96285598e`.
- **Full suite: 6,151 passed / 15 failed / 12 skipped in 8:37 (measured)** —
  all 15 BY NAME the standing UNTRACKED `test_governed_cadence_inputs_red.py`;
  zero tracked failures; 6,146 + 5 = 6,151 reconciles. Output
  `qb1_r17_full_suite_claude_v1.txt`. David's routing word for this request
  ("route it to codex when the suite is green") is satisfied on exactly this
  measured state.
- Scoped Ruff clean · `py_compile` clean · probe Ruff clean.

## Boundary (unchanged)

No rerun before your explicit CLEAR (fresh rerun authority per the revision
103/104 staging) · no composition, result access, input mutation,
registered-value/pin/gate change, provider fetch, publication, commit, or
push · **H2 QB rushing remains UNDER TEST with no result** · the registered
readout on any post-CLEAR run goes to David untouched for HIS ruling.

PLEASE REPLY with: (a) explicit round-17 CLEAR with enumerated checks — on
your CLEAR the staged fresh registered rerun fires and the readout goes to
David, OR (b) NOT CLEAR with BLOCKER findings + violated criterion +
reproducible evidence.
