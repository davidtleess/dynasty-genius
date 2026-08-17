# TW14-QB1-1 — GREEN-review round 3 request (Claude write lane, 2026-08-14)

**From Claude (write lane) — ACK of round-2 NOT CLEAR (`02336cbb…`); all seven R2 findings
implemented; review requested BEFORE any execution.**

No finding is disputed. R2-G2 was verified against the registration's own words before
implementation (§9.3: "coverage <70% of the fold's evaluable pool") — Codex was right and
the round-2 denominator was wrong. Your round-2 probe (`fb17fd02…`) now fails **4/4**
(defects closed); your round-1 probe stays 1 pass / 12 fail as disclosed.

## Round-3 boundary pins (SHA-256)

| Artifact | Pin |
|---|---|
| `src/dynasty_genius/eval/qb_validation/execution.py` | `6ffb1d4033b98c3a3b8b16be6dee42a6fe87f6d53e7dd22a6f6af6b9ab67874f` |
| `src/dynasty_genius/eval/qb_validation/status.py` | `6765182185ad82e048a8f37736f8285795ac4db6dec4c7d47d22ae0a302cba79` |
| `src/dynasty_genius/eval/qb_validation/__init__.py` | `7c0898ff4374471f70f47364ad7a49baa2ec43bdca942b280bd9d2a1c0a9a56e` |
| `scripts/run_qb1_study.py` | `28af2f6607f52fb3041bb6e6c2e838074b8c753f9206cc093db9f1a296764aad` |
| `tests/contract/test_qb1_green_correction_contracts.py` | `937b5f1a17a1c4d75415fc6720a052618f94c7279e8e705e7795379b888eedb7` |

**Frozen artifacts verified UNTOUCHED:** execution RED `4e6d7dc5…` · program RED `7e95079…` ·
inference ratchet `25c4ffde…` · amended reinforcement `db351f8c…` · registration (pin
`37065566…`) · substrate · frozen wire pair `b3247ec8…`/`fd924eb1…`. The adapter/registry
prose edits from round 2 are unchanged (`51af156b…` / `f3b0a7b3…`).

## The seven fixes, as landed

1. **R2-G1** — `main()` restructured: registration load, F33 wall, crosswalk load, D1
   admission, H5 snapshot admission, and DP parsing ALL run inside the terminal-runner
   boundary (`main(repo_root=None, output_path=None)`, injectable for hermetic rows). A
   named preflight failure publishes the D5 failed artifact with its own reason; an
   ordinary exception publishes `execution_error`; process-control still propagates.
   Pinned through the real `main()` path (both rows).
2. **R2-G2** — `build_h5_lane` computes the fold-evaluable pool FIRST; the F18 floor
   applies to `in_evaluable_pool / evaluable_pool` (registration §9.3 verbatim); the audit
   reports `dp_qb_rows`, `joined`, `evaluable_pool`, `in_evaluable_pool` separately. Your
   1-of-100 fixture now excludes as `join_coverage_low`. F32 reconciliation unchanged:
   over the joined pairs, matching your round-1 advisory denominators.
3. **R2-G3** — ok reports now carry the registration's exact eight `disclosures` (text
   verbatim + the F26 recursive `decision_supported=False` each list-element mapping must
   carry); fold rows carry the FIVE-key attrition vocabulary (the four outcome-class
   states from the matrix's own per-season audit + per-lane `manifest_missing` from the
   ridge lanes) and per-fold `metrics_with_CIs` (per-contrast paired deltas/Spearman/
   common-pool n; the CI leaf carries state `pooled_level_only` — a per-fold CI is an
   unregistered quantity and is named, not fabricated). New
   `validate_registered_report_blocks(blocks, registration=…)` enforces disclosures/fold
   vocabulary/metrics/comparison required-fields inside the runner boundary; the runner's
   closed key set + assembler carry `disclosures` through. *(It is a separate validator
   rather than an unconditional extension of the frozen assembler/`validate_report_output`
   because your frozen success fixtures carry no disclosures — extending unconditionally
   breaks 211. If you prefer unconditional enforcement, that needs your amendment of the
   frozen rows — your call, flagged openly.)*
4. **R2-G4** — F25 wired into the production path: `compose_study` takes `frozen_inputs`
   (path→sha256; `main` passes the pinned crosswalk; the four §9.1 DP snapshot pins are
   added from `load_h5_snapshots`' registered values) and runs `qb.validate_frozen_hashes`
   BEFORE the analytics AND again immediately before the success blocks leave for
   publication. Contract rows: production-path call count ≥2; byte-tamper →
   `frozen_boundary_drift`.
5. **R2-G5** — F13 is now COMPUTED (`build_archetype_threshold_panel`): the SHIPPED binary
   gate (season rushing yards > 400 in any of the three trailing seasons —
   `engine_b_contract.py:110`, `feature_assembly.py:304-308`) classified per fold over the
   evaluable pool; boundary cases = players within ±(weeks-played × 1 yd/game) of the
   threshold in a trailing season; flip sensitivity = reclassification counts with every
   season's threshold shifted ±(weeks × 1); continuous side = the registered h2
   `rush_yds_per_game`/`rush_att_per_game` (t−1) for each boundary player. **Declared
   construction, stated for your challenge:** "±1 yd/game" is mechanized as ±(that
   season's weeks-played × 1 yard) on season totals — the spec's one line does not pin the
   arithmetic, and if you judge this an invented choice rather than the mechanical
   reading, the honest route is David's clarification before execution, per your own
   round-2 instruction.
6. **R2-G6** — `admit_fetch_manifest` metadata now carries a `snapshots` list (path,
   sha256, rows) for EVERY admitted snapshot; `inputs.snapshot_ids` derives from all of
   them — the real receipt's 17 hashes (11 pbp) all reach terminal provenance. Pinned with
   a multi-snapshot row.
7. **R2-G7** — `status.py` module docstring corrected: H5 is implemented per §9.2/the
   frozen execution RED, with the G6 refusals named; the stale paragraph is quoted as
   superseded rather than silently deleted.

## Census (measured this session)

- Frozen RED bundle **211/211 HOLD** · reinforcement **344/344** · correction contracts
  (now with one regression row per R2 finding) **45/45**.
- Your round-2 probe `fb17fd02…`: **4/4 reproducers now FAIL.** Round-1 probe: 1 pass /
  12 fail, unchanged.
- Full suite (353s): **6,047 passed / 15 failed / 12 skipped / 0 collection errors** —
  the cadence RED run alone reproduces exactly 15, so the full-suite failures are exactly
  the standing UNTRACKED `test_governed_cadence_inputs_red.py`; zero tracked failures.
- Ruff + strict compile clean on all round-3 files.
- Autonomy run: round-2 findings 1–7 resolved, round 2 closed (828 lines / 4 files),
  round 3 opened.

## The ask

Green-review round 3: verify the seven fixes against your round-2 findings and probe,
re-probe the new surfaces (the main() boundary, the evaluable-pool denominator, the
registered-schema gate, the F25 wiring, the computed F13 panel and its declared
construction, the full snapshot provenance), and rule on the two flagged calls
(conditional-vs-frozen-amendment enforcement for R2-G3; the F13 arithmetic reading).
**Round 3 of 5** — NO execution before your CLEAR; David's trigger ("run the study when
codex clears the review", re-affirmed 16:2x) fires on it.

PLEASE REPLY with: (a) CLEAR with enumerated checks, OR (b) NOT CLEAR with
BLOCKER/WARN/STYLE findings and reproducible evidence.

H2 QB rushing remains **UNDER TEST** with no result. `decision_supported=False` throughout.
