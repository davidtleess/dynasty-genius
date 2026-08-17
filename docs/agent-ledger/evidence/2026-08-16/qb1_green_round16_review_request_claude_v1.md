From Claude (write lane) — QB-1 ROUND 16 REVIEW REQUEST: the ONE shared matrix-placeholder classifier, REAL-SURFACE PROVEN; explicit CLEAR or NOT CLEAR requested [w#qb1-exec-1]

## Artifact under review — exact pins (uncommitted, worktree)

Round 16 (run `f8f7551c…`, revision 95, open snapshot `a9c21242…`), four-file scope
exactly per your transition:

| File | Opening pin | Current pin |
| :-- | :-- | :-- |
| `src/dynasty_genius/eval/qb_validation/qb_ppg_labels.py` | `c00c60ab…` | `e5cb3955142b365a9dc929e18a7ceda33f647613fc8610442a2b39fa7ca73edf` |
| `src/dynasty_genius/eval/qb_validation/study_matrix.py` | `1d2a6296…` | `518e4b82c79d6a9637ae5bca5b6eb0aba7b82afc212ce1d01b7fe8a69d50e389` |
| `scripts/run_qb1_study.py` | `8d7d525c…` | `7de911cccdcb17ae0e37ca48b5816a50420dbcd0e61303f663553d381c97a798` |
| `tests/contract/test_qb1_green_correction_contracts.py` | `a75dbc64…` | `7407dc6c46237d7c3a23e3f3db044f56583db5d553c793fead9486684aab36c9` |

**Session continuity, disclosed:** the R16 GREEN was landed by this lane's prior
session (handoff order HND-7071a2dc, ledger 11:57 ET); this fresh session verified
run state + all four pins from durable state, then executed the parked proof
sequence. Frozen wire pair re-verified untouched (`b3247ec8…` / `fd924eb1…`).

## What is implemented (your R15 registration read, exactly)

- `exclude_provider_placeholder_rows` + `PLACEHOLDER_D2_COLUMNS` moved INTO
  `qb_ppg_labels.py` beside their single-source `_stat_decimal` — the ONE shared
  classifier for BOTH consumers. Strict conjunction: missing `player_id` AND
  missing `position` AND validated exact zero across all 17 D2 inputs; names
  audit-only; every near miss falls through to fail-closed guards.
- The runner imports/re-exports it (deliberate `noqa: F401`, contract-pinned).
- `study_matrix.build_study_matrix` applies the SAME function object on its
  defensive weekly records immediately before `_validated_weekly_row`; admitted
  pool and copied frame untouched through matrix entry and source/shape/manifest
  gates.
- RED-before-GREEN honored (3 net-new R16 contracts failed 3/3 pre-implementation):
  single-object identity + matrix-source proof · WHOLE-REPORT EQUALITY with/without
  injected placeholders (analytic blocks identical; `inputs.dataset_rows` honestly
  +2) · near-misses fail closed at the FIRST consumer reached, either registered
  name.

## MANDATORY REAL-SURFACE PROOF — the matrix seam on the REAL store

Probe `qb1_matrix_placeholder_real_surface_probe_claude_v3.py` (script SHA-256
`9a30c794275d4f071092d79403f4ae35e59622e2063930f2c14ba4228b3a4283`, recorded output
`qb1_matrix_placeholder_real_surface_probe_claude_v3_output.txt`, SHA-256
`4f9546a873fc6a7e2cf7a25dcb647fccfc321960397bb282f974d0b3a0f32689`), mirroring the
matrix's defensive path byte-for-byte (copy → shape gate → manifest-column gate →
`_records` → classifier). **PROBE VERDICT: PASS.**

1. **Exact classification: 192/192 REG** placeholders classify at the seam.
   **Disclosure, measured not smoothed:** the seam excludes **236 total** — the
   192 REG plus **44 non-REG rows of the IDENTICAL exact predicate shape**. The
   matrix classifier runs BEFORE the REG filter (your ruled placement:
   immediately before `_validated_weekly_row`, which also runs pre-REG-filter),
   so the non-REG placeholders classify too — had they not, the validator would
   have refused them and the wall would still stand. 236 reconciles exactly with
   the original full-pool missing-id census (236/199,868; 192 REG + 44 POST).
2. **Zero residual:** kept rows with missing `player_id` = **0**.
3. **The exact R15 wall is gone:** `_validated_weekly_row` (whose
   `stat_value_invalid` at weekly row 1026 was R15-G1) passes over ALL 199,632
   kept defensive records; REG validated rows **191,089** (= 191,281 − 192).
4. **All-position team-rushing totals unchanged (S27):** `(team, season)`
   rushing-TD sums, raw REG records WITH placeholders vs validated kept REG rows
   (matrix law), zero-default over the key union: **352 keys, 0 mismatches, 0
   unparseable rows**.
5. **Input/frame digests unchanged:** admitted weekly frame digest identical
   before/after; the classifier copies, never mutates.

**Boundary held: NO composition run occurred** (your round-16 "no second
composition run" boundary). The probe exercises matrix stage (4) only — no
season-coverage gate, no fold, no ridge lane, no inference, no report; nothing
registered was computed, printed, or persisted.

**Wall status, mandated R15-G2 wording:** the census established **ONE OBSERVED
NEXT WALL** (the matrix weekly validator); this round closes THAT wall on the
real store. Later composition stages are not exercised here and **no claim is
made that no wall exists beyond it** — the granted rerun after your CLEAR is the
registered path that answers it, failing closed by name if a further wall exists.

## Evidence census at the current pins

- Correction contracts: **144/144** (141 R15 + 3 net-new R16 reconciles).
- Five-file bundle (correction + program + inference + reinforcement + execution
  RED): **699/699** in 48.48s (your R15 count 696 + 3 net-new = 699 reconciles).
  Recorded output `qb1_r16_five_file_bundle_claude_v1.txt`, SHA-256
  `7232dd37cbad154eee0c32e832ee07b4f3ca60a89b07449805ac00625803b5cf`.
- **Full suite: 6,146 passed / 15 failed / 12 skipped in 7:34 (measured)** — all
  15 verified BY NAME as the standing UNTRACKED
  `test_governed_cadence_inputs_red.py` (git-status-confirmed untracked; zero
  tracked failures); 6,143 at R15 pins + 3 net-new R16 = 6,146 reconciles.
  Recorded output `qb1_r16_full_suite_claude_v1.txt`.
- Scoped Ruff clean · `py_compile` clean · scoped diff = exactly the four pinned
  files (labels/matrix tracked-modified; runner/contracts untracked-by-history,
  as all round).

## Disclosures (beyond the 236/192 split above)

- **Runner pin advanced AFTER the GREEN landing, this session:** `7f1a8dbc…` →
  `7de911cc…` — removal of a 3-line stale comment (runner lines 48–51) that
  described the superseded direct `_stat_decimal` import; comment-only, zero
  semantic change, flagged in the handoff as "clean before routing". The live
  import block at the classifier re-export carries its own accurate comment.
- **Probe hygiene:** the probe script as first written carried Ruff `I001` — the
  same class as your R15-W1 WARN. Fixed with the safe import-sort BEFORE routing;
  probe re-run at the final script content; results identical (both runs PASS,
  recorded output is from the post-fix run).
- **Structured state:** `finding-green-review-15-1` resolved via the sanctioned
  verb in round 16 AFTER the real-surface proof (your mandated ordering);
  round-16 `real-surface-qa` receipt recorded passed with the probe evidence.

## Boundary (unchanged)

No rerun before your explicit CLEAR (the fresh rerun grant is held and
unconsumed) · no execution, publication, input mutation, registered-value/pin/
gate change, provider fetch, commit, or push · **H2 QB rushing remains UNDER
TEST with no result** · scorer `17cfc1e` push stays David's separate keystroke.

**David's standing instruction for this round, verbatim: "if this turn doest
clear . send it to the judge"** — a round-16 NOT CLEAR routes to the Judge on his
word (charter nuance, disclosed to him: the Judge rules on loop-control gates and
never overrides verification failures; a NOT CLEAR resting on a reproducible
defect may be declined by the Judge and return to David).

PLEASE REPLY with: (a) explicit round-16 CLEAR with enumerated checks — on your
CLEAR the already-granted fresh registered rerun fires and the registered readout
goes to David for HIS ruling, OR (b) NOT CLEAR with BLOCKER findings + violated
criterion + reproducible evidence — which this lane then routes to the Judge per
David's standing instruction above.
