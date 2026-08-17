# TW14-QB1-1 — CONTEXT HANDOFF (Claude write lane, 2026-08-14 ~13:0x ET)

**Why this exists:** David's word, verbatim: "you and codex are out of context." Both lanes
are near context exhaustion mid-cycle. This document is the complete resume anchor: a fresh
session reading THIS FILE plus the cited pins can continue without any conversation memory.
Everything below is on disk; nothing depends on either lane's session surviving.

## Where the cycle stands (exact)

- **Run state:** TW14-QB1-1 ACTIVE in this worktree; green-review round 1 OPEN with
  Codex's seven findings recorded (`finding-green-review-1-*`), review check FAILED.
- **David's held trigger, verbatim:** "run the study when codex clears the review" —
  execution fires on Codex's green-review CLEAR and NOT before. NO study has run.
  **H2 QB rushing remains UNDER TEST with no result.**
- **Frozen RED (Codex, all pins verified):** `test_qb1_execution_red.py` `4e6d7dc5…` ·
  `test_qb_validation_program_red.py` `7e95079…` · `test_qb_validation_inference_red.py`
  `25c4ffde…` · contract `qb1_execution_red_contract_codex_v1.md` `d15fab5c…`.
  Codex ALSO amended its three r12 reinforcement rows (QBGREEN-F1 accepted):
  `test_qb_validation_green_reinforcement_red.py` now `db351f8c…`, 344/344.
- **My GREEN so far (211/211 on the frozen RED; full suite 5,999P before the r12
  amendment):** `execution.py` `5e95cb58…` · `status.py` `5592b472…` · `__init__.py`
  `987b8ca5…` · `run_qb1_d1_fetch.py` `d781bddc…` · four §9.1 DP files byte-exact in
  `raw/dp_values/`.
- **Codex green-review round 1: NOT CLEAR — 6 BLOCKER / 1 WARN**
  (`qb1_execution_green_review_codex_v1.md` `740e3da1…`; adversarial probe
  `qb1_green_adversarial_probe_codex_v1.py` `de97c5ff…` reproduces 13/13).

## The seven findings and the fix designs (analyzed this session, NOT yet implemented)

1. **G1 admit→load composition broken** (the component-verified/whole-claimed class):
   `admit_fetch_manifest` emits `metadata.completeness="complete"` (pinned by the frozen
   RED) while `load_validation_sources` requires `"ok"` — ALL seven real states are
   rejected one stage downstream. FIX: a new pinned composition seam
   (`admit_and_load_validation_pool(raw_root, repo_root, frame_loader)`) that admits, maps
   the envelope into the F1 gate's exact shape (status ok / completeness ok / provenance
   fields), and calls `load_validation_sources` — with a hermetic row proving REAL-shape
   end-to-end admission AND that tampering still refuses.
2. **G2 receipt registration_pin never read:** admit must refuse a missing/wrong
   `registration_pin` BEFORE pass-1 hashing (canonical pin constant `37065566…` with
   citation; a 64-zero pin currently admits 7/7 — Codex's reproducer).
3. **G3 runner publishes unvalidated success + drops plain exceptions:** `run_qb1_study`
   must `validate_report_output` the success payload (schema-invalid → NAMED metric-free
   failed artifact), and convert ordinary exceptions (e.g. ValueError) into a named
   metric-free terminal failure (proposed reason `execution_error`) — every invocation
   emits an artifact.
4. **G4 no end-to-end composition existed at verdict:** `scripts/run_qb1_study.py` must be
   COMPLETE + pinned + carry a hermetic composition RED, entering green-review round 2
   BEFORE any execution ("run WHEN Codex clears" — never audit-after-run). Composition
   signatures gathered this session: `build_study_matrix(sources, registration=…,
   expected_registration_hash=…)` → `run_expanding_folds(matrix, train_start_season=…,
   test_seasons=…)` → per fold `fit_ridge_lane(fold, labels, lane=h1..h4)` + the
   registered naive lane (baseline_naive: most recent evaluable PPG in t−3..t−1; no prior
   row → excluded from naive pairs) → `build_primary_comparisons(lanes_by_fold,
   registration=…, expected_registration_hash=…)` (consumes `lanes_by_fold[fold][lane]`,
   base lanes must all be present per fold; h5 lane joins via `build_h5_static_join` +
   per-fold coverage/reconciliation gates) → `run_primary_inference(comparisons,
   registration=…, expected_registration_hash=…)` (pins scipy version) →
   `evaluate_power_and_status` per contrast → D5 panels (`require_case_panel`,
   `require_threshold_sensitivity`, `validate_sensitivity_panel`) →
   `assemble_terminal_report` → `write_terminal_report_atomic` under the frozen root.
   Labels: `qb_ppg_labels.build_label_table` (settings-hash gated, registered 12-key rule).
5. **G5 F33 wall too coarse:** the wall must ALSO catch imports/calls of the adapter's
   `load_validation_*` functions (the registered validation_* wall — synthetic app caller
   currently passes), and the allowlist must be OCCURRENCE-SPECIFIC (path → allowed
   marker CLASSES), not whole-file substrings: adapter allowed {validation-defs,
   raw-root-path}, registry/daily_control allowed {raw-root-path prose} only,
   eval/qb_validation allowed all.
6. **G6 H5 status labels impossible evidence:** refuse named BEFORE ordering: folds >
   registered h5_lane_total (4) · p values outside [0,1] · reversed CI (low > high) ·
   pooled_delta outside its own CI (sign-contradiction class: positive delta with
   all-negative CI currently emits model_superior).
7. **G7 WARN:** `require_case_panel` must reject duplicate rows (len check vs id-set);
   `validate_join_coverage` must pin `0 ≤ joined ≤ evaluable` (101/100 currently admits).

## Resume sequence for the fresh session (after bootstrap reads)

1. Read this file + Codex's `740e3da1…` review + probe `de97c5ff…` (reproduce 13/13 first).
2. Implement G1–G7 exactly as designed above (product: `execution.py`, `status.py`;
   composition: `scripts/run_qb1_study.py` NEW; focused hermetic rows for the composition
   + each fix in a new Claude-authored contract file offered to Codex).
3. Census: frozen RED 211/211 must HOLD + new rows + amended reinforcement 344/344 +
   full suite (expect: standing cadence RED only).
4. Wire Codex (fresh session) for green-review round 2 with all pins. NO EXECUTION until
   its CLEAR; then David's held trigger fires the deterministic run (seed 20260716).
5. Gates unchanged: no push (scorer `17cfc1e` push = David's separate standing keystroke) ·
   no provider calls (substrate is complete on disk) · registered values immutable.

## Uncommitted session record (disk-durable, commit is gate-path)

Everything after scorer commit `17cfc1e` is on disk UNCOMMITTED: today's post-commit ledger
entries, all QB-1 evidence (framings v3–v5 + CLEARs, fetch script/audit, RED set, GREEN,
reviews, this handoff), the fetched substrate (gitignored by design), and the GREEN product
edits. A fresh clone loses the tracked-file EDITS only if the tree is discarded — do not
discard; the next gate commit carries the cycle.
