# TW14-QB1-1 GREEN round-6 independent review — NOT CLEAR

Date: 2026-08-15 ET  
Reviewer: Codex  
Layer: 3 (validation/execution). Layers 1–2 are frozen D1 foundations and were
checked for boundary drift only; no foundation change was authorized or made.  
Study execution: **not run**. H2 QB rushing remains **UNDER TEST** with no result.

## Pins reviewed

- `execution.py`: `bd0a725ada7d99e3049ed0c86e674bcda4fa3106d0c60fc7008b39b0ebcb5d00`
- `scripts/run_qb1_study.py`: `7015a824b1e38d5cd934c74c6281b66378dfd99e9ff2ccc3181068880e92ab68`
- correction contracts: `b459f86b7a37c2f70d30846a6045cf91619df6c5e2d07b1b56a9956ad9fa1a2a`
- independent probe: `b3b739a24f93df6487a57dbf2d5d2253d662841cef5b8c5f0d9bfc66b4fc89be`

The submitted three pins matched. The disclosed unchanged status/init/RED/
ratchet/reinforcement pins matched, and the scoped diff against
`snapshots/green-review-6/open` was limited to the three declared files.

## Verdict findings

### BLOCKER R6-G1-1 — registered status functions are not enforced

`validate_registered_report_blocks` checks only the status vocabulary and the
independent numeric domains. It does not apply the registered status function
or its fold-floor precedence. The public runner publishes `supported` on c01
with zero evaluable folds and `market_noninferior` on c11 with zero evaluable
folds. This directly contradicts registration §7 and §9.2, where a below-floor
comparison must be `unsupported_power` and the H5 power gate is first.

Reproducer: independent probe lines 76–106.

Smallest correction: enforce the complete model/H5 status functions, including
fold floors and NI/status consistency, at the public publication boundary.

### BLOCKER R6-G1-2 — both disclosed H5 completeness choices are rejected

1. **Empty margin readouts are not admissible.** Registration §9.2 line 240
   requires all three margins `{0.025, 0.05, 0.10}` to be reported regardless
   of outcome. The gate checks only for stray keys, so all 12 required
   contrast×margin cells may be absent while the public runner publishes `ok`.
   An uncomputable cell must still be present with an honest unavailable state
   and null outputs.
2. **H5 fold evidence cannot be optional without consistency enforcement.**
   The runner publishes a four-fold `market_noninferior` c11 result after every
   per-fold c11–c14 metric is removed. Registration §8/§9.3 binds H5 to the four
   folds, exact common pools, reported common-pool n, and a 3-of-4 floor. A
   registered exclusion may be represented honestly, but omission cannot
   coexist with a claimed contributing fold. Require an explicit per-fold H5
   state (including named exclusions), or mechanically reconcile presence/
   exclusion and `evaluable_folds`.

Reproducers: independent probe lines 33–73. Gate seam: `execution.py` lines
1141–1171 and 1363–1414.

### BLOCKER R6-G1-3 — the purported computed F13 panel remains shape-only

The gate accepts any nonempty rule/basis, any finite threshold, and unrelated
nonnegative counts. The public runner therefore publishes threshold `-123`,
`n_evaluable=1`, `dual_threat_count=999`, `pocket_count=999`, and
`boundary_case_count=999` with an empty boundary list. Those values cannot be
the shipped 400-yard computation in `build_archetype_threshold_panel`.

Reproducer: independent probe lines 109–136. Gate seam: `execution.py` lines
1271–1317.

Smallest correction: bind the shipped rule/400-yard threshold and arithmetic
invariants (`dual + pocket == n`, boundary count equals list length, counts do
not exceed the pool), then validate the produced boundary-row schema and the
registered continuous basis.

### BLOCKER R6-G1-4 — two “produced content” blocks still accept shells

- A required fold metric accepts `ci={}` because only `Mapping` is checked,
  despite the emitted contract using the named pooled-level CI state.
- A mandatory case row accepts blank `player_name`/`gsis_id` and a reported
  lane named `fabricated_lane`; thus it is not bound to a produced registered
  player/lane result.

Reproducers: independent probe lines 139–176. Gate seams: `execution.py` lines
1202–1206 and 1208–1248.

Smallest correction: close the per-fold CI object to its emitted schema; require
nonempty case identity fields and lane keys from the registered produced lane
set, with row/lane-state consistency.

## Fresh verification

- Submitted correction + frozen/ratchet/reinforcement set: **623 passed**
  (`68 + 555`), 14 numerical-boundary warnings.
- Prior round-5 adversarial probe: **4/4 failed**, confirming the submitted
  fixes addressed those exact rows and the state repair.
- New round-6 public-runner probe: **6/6 passed**; each passing test is an
  invalid payload that still publishes `run_status=ok`.
- Ruff on all three scoped files plus the probe: clean.
- Strict compile on all three scoped files plus the probe: clean.

Reproduce the new evidence:

```bash
PYTHONPATH=. pytest -q \
  docs/agent-ledger/evidence/2026-08-15/qb1_green_round6_adversarial_probe_codex_v1.py
```

Expected at these pins: `6 passed`. The passing assertions are the defects.

## Disposition

**NOT CLEAR.** No reviewer-clear or round close was recorded. The held study
execution trigger must not fire. The four blockers are recorded in the active
round-6 structured state; under the previously established one-gate/one-ruling
path, the loop disposition returns to David rather than creating a duplicate
Judge docket.
