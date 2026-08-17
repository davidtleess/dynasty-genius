# QB-1 execution RED contract — Codex v1

**Cycle:** TW14-QB1-1  
**Role:** sole binding RED author  
**Layer:** layer 4, offline model validation; its layer-1 dependency is the
David-authorized D1 frozen substrate, audited independently before this RED.

## Fetch disposition

The corrected fetch receipt is **CLEAR**. The completion manifest hashes to
`98209e54f1bf9401ecd2b5ca107f35dc77f2833021b8d738bb4241b878d2cd4a` and now
records the honest authorization window (after the 11:27 framing CLEAR and
before the 11:52:11 fetch start) plus the original-error correction. The fetch
script hashes to `149283b70f62ff57e6b0c5295d367479e9c7fdd451ed3a57cc376bc9cd27248d`.
No snapshot changed. The reusable substrate sweep remains 17/17 exact, 7/7
datasets, 154,360,748 bytes, no extras, and the anti-rot contracts remain 5/5.

W1 is accepted into RED: a rerun invalidates an old completion manifest before
the first provider write and installs the new completion receipt by atomic
same-directory replacement.

## Frozen RED artifacts

| Artifact | SHA-256 | Purpose |
|---|---|---|
| `tests/contract/test_qb1_execution_red.py` | `4e6d7dc5c090aacadc530fbb0292736a5ab745621bdcc2167400a66f210b3f2d` | 29 execution rows: D1 admission, D4/H5, D5, terminal runner, and positive controls |
| `tests/contract/test_qb_validation_program_red.py` | `7e95079297a269dc13c26371e6e92a598ffaf8ea14e5dc9a474f0c2eea190dfe` | unparks F10/F13/F16/F18/F25/F29/F31/F32/F33 |
| `tests/contract/test_qb_validation_inference_red.py` | `25c4ffde3421f804e3a2fb17a42438c43deb9673188fe099e2903c443b3827f1` | ratchet now requires zero parked seams |
| `qb1_h5_identity_preflight_codex_v1.py` | `b7acade764e1052d12c41357dc63767081157e3ed21a0674663555f3b06d6cd3` | rerunnable, read-only fp_id/F32 measurement |

Only tests and evidence were authored. No product implementation, provider
call, study run, model value, report result, commit, or push occurred.

## Contract surfaces

1. **D1 receipt admission:** `admit_fetch_manifest` verifies the exact seven-name
   set, all snapshot hashes and byte/row claims, completeness, registration pin,
   and provenance before calling a frame loader. Any content drift refuses as
   `source_snapshot_drift` before one frame is parsed. The emitted state carries
   `raw_snapshot_path`, source timestamp, parser version, completeness, and SHA.
2. **Fetch completion:** `invalidate_completion_manifest` and
   `write_completion_manifest_atomic` make a partial rerun non-admissible and a
   completed receipt an atomic commit.
3. **H5 identity:** `build_h5_static_join` uses DP `fp_id` → crosswalk
   `fantasypros_id` → `gsis_id` only. Name equality cannot create a join.
   Duplicate identical claims collapse audibly; conflicting claims are excluded
   to triage. `validate_join_coverage` pins 69/100 fail and 70/100 pass.
   `reconcile_identity_names` pins exactly 2% pass, >2% fail, and a missing raw
   name in the mismatch numerator. `load_h5_snapshots` binds all four §9.1 files
   to the registered SHA values.
4. **H5 status:** all five labels and their total precedence are driven.
   Power comes first; superiority precedes non-inferiority; NI requires >−0.05
   and adjusted p≤0.10; either CI/p disagreement direction is named; `p_ni` and
   `ni_met` survive every status. Fold floor, margin, and q are not payload knobs.
5. **D5:** the nine strict seams are live, including the exact case panel, the
   F13 binary-vs-continuous archetype panel with ±1 yd/game boundary cases, the
   F29 unfiltered + ≥4-games pair, the H5 margin panel, frozen hashes, artifact
   tracking, and the repo-wide consumer wall. Failed terminal reports carry no
   metric-bearing blocks. Successful reports use `qb_validation_report.v1`, raw
   deltas, separated status vocabularies, and recursive
   `decision_supported=false`.
6. **Terminal path:** `write_terminal_report_atomic` leaves no partial final
   artifact on interrupted replacement. `run_qb1_study` converts a named
   `QBValidationFailure` into an atomic failed artifact under the frozen output
   root. Every invocation terminates visibly.
7. **Registration:** the real newline-terminated JSON canonicalizes to the
   binding `37065566…` pin while its raw-byte digest differs. Absence and a
   canonical-object mutation reproduce `preregistration_missing` and
   `registration_drift` respectively.

## RED census

- Focused RED plus the 34-seed callable matrix and unpark ratchet:
  **36 failed / 29 passed**, zero collection errors.
- Full principal QB validation contract bundle (program, inference, dependency,
  reinforcement, execution): **36 failed / 520 passed**, exactly the same 36
  intended RED failures. No pre-existing green contract failed.
- Ruff: clean on all three test artifacts and the measurement script.
- Strict compilation: clean on the new test and measurement script.

The 36 failures comprise nine newly unparked callable rows and 27 behavioral
execution failures. The 29 focused passes are real positive controls, including
canonical registration handling, the existing model-lane behavior, F31's real
gitignore boundary, and the unpark ratchet.

## Real H5 preflight (advisory mechanics, not a study result)

The pinned crosswalk is exact at `8ed4b675…`, 7,952 entries, 4,652 unambiguous
FantasyPros claims, zero identical duplicates, and zero conflicting claims.
Against the four exact DP files:

| Fold | joined / QB rows | coverage | mismatches / joined | F32 gate |
|---|---:|---:|---:|---|
| 2021 | 77 / 78 | 98.72% | 2 / 77 = 2.60% | exclude |
| 2022 | 68 / 68 | 100% | 2 / 68 = 2.94% | exclude |
| 2023 | 86 / 86 | 100% | 2 / 86 = 2.33% | exclude |
| 2024 | 82 / 82 | 100% | 0 / 82 = 0% | admit |

All four coverage gates pass. Three reconciliation gates fail by the registered
rule, so the H5 fold floor is expected to be unmet and contrasts c11–c14 to land
`unsupported_power` unless the execution's binding measurement differs. No
normalization, threshold, or registered value may move. H2 QB rushing remains a
hypothesis **UNDER TEST**; this RED and preflight are not evidence for it.

