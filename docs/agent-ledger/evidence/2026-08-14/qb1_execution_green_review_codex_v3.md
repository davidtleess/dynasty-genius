# QB-1 Execution GREEN Review — Codex v3

**Cycle:** TW14-QB1-1  
**Review round:** green-review round 3  
**Verdict:** **NOT CLEAR**  
**Reviewed at:** 2026-08-14 17:59 EDT

No registered study execution occurred. No provider call, result artifact publication, commit,
push, model change, or product-surface change was made by this review. QB rushing production
(H2) remains **UNDER TEST** with no result.

## Boundary and pins

The handed-off request independently hashes to
`e36b1e20fb3867b4cf5e1b8a97de206994e177e2c3ef7697b7662f77f9ae7497`.
All round-3 pins reproduce exactly:

- `execution.py` — `6ffb1d4033b98c3a3b8b16be6dee42a6fe87f6d53e7dd22a6f6af6b9ab67874f`
- `status.py` — `6765182185ad82e048a8f37736f8285795ac4db6dec4c7d47d22ae0a302cba79`
- `__init__.py` — `7c0898ff4374471f70f47364ad7a49baa2ec43bdca942b280bd9d2a1c0a9a56e`
- `scripts/run_qb1_study.py` —
  `28af2f6607f52fb3041bb6e6c2e838074b8c753f9206cc093db9f1a296764aad`
- round-3 correction contracts —
  `937b5f1a17a1c4d75415fc6720a052618f94c7279e8e705e7795379b888eedb7`

The frozen execution/program/inference RED pins (`4e6d7dc5…`, `7e950792…`, `25c4ffde…`)
and the amended reinforcement pin (`db351f8c…`) reproduce unchanged. The active autonomy goal
and scope match TW14-QB1-1; the run remains ACTIVE and its execution gate remains held.

This is Layer 3 validation/execution work. Its Layer 1 admission seam and complete 17-snapshot
receipt provenance are present. Its Layer 2 identity join computes fold-evaluable coverage. The
open findings are within the Layer 3 terminal/report boundary and its registered Layer 1/2 frozen
dependencies; they do not authorize a substrate or product change.

## Round-2 disposition

Four prior findings are completely corrected at the reviewed seams:

- R2-G1: all real CLI preflight work is now inside the terminal runner callback.
- R2-G2: H5 coverage now uses the fold-evaluable denominator.
- R2-G6: all admitted snapshot hashes reach success provenance.
- R2-G7: `status.py` now documents H5 accurately.

The carried round-2 adversarial probe now fails **4/4**, matching the disclosed correction. The
other three round-2 findings are only partially corrected: a schema helper exists but is not a
runner invariant; F25 runs twice but over the wrong set; and F13 is computed but uses the wrong
game population.

## Findings

### R3-G1 — BLOCKER — the public runner can publish an incomplete D5 report as `ok`

`validate_registered_report_blocks` is called only by the current composition
(`scripts/run_qb1_study.py:1035-1039`). The public terminal runner itself calls the optional
assembler and the No-Verdict scan, but not that validator
(`execution.py:925-941`). `assemble_terminal_report` also treats disclosures as optional
(`execution.py:643-722`). A direct hermetic runner invocation with empty five metric blocks and
no disclosures publishes successfully:

```text
run_status=ok
disclosures_present=False
terminal_artifact_exists=True
```

**Ruling on the flagged conditional-vs-frozen decision:** every D5 `ok` publication must pass the
registered schema at the runner boundary. Amend the frozen success fixtures to carry the complete
registered shape; preserving an under-specified green fixture is not grounds to keep an invalid
success path. Give the runner the registration (or an equivalently exact runner-owned schema
binding), then convert schema failure to the existing metric-free `report_schema_invalid`
artifact.

### R3-G2 — BLOCKER — the closed D5 fold-flag vocabulary is not enforced

The new validator checks only that `flags` is a list (`execution.py:842-846`). It accepts
`not_a_registered_fold_flag`. Production composition itself emits
`h5_fold_excluded:<reason>` (`scripts/run_qb1_study.py:948-953`), which is outside D5's exact
allowed set:

```text
{fold_starved, join_coverage_low, join_reconciliation_failed, degenerate_input}
```

Emit the registered reason itself and refuse every flag outside that set before publication.
Pin both arbitrary-flag refusal and each production H5 exclusion path.

### R3-G3 — BLOCKER — ridge `manifest_missing` attrition is always reported as zero

`fit_ridge_lane` returns `test_manifest_missing` as
`{"count": n, "keys": [...]}` (`ridge_lane.py:203`, `ridge_lane.py:332-335`). The composition
helper accepts only an integer or list/tuple and maps every mapping to zero
(`scripts/run_qb1_study.py:925-929`). A full hermetic composition with the real ridge result
wrapped to carry a known count of seven produces:

```text
source_lane_drop_count=7
reported_h1_manifest_missing=0
```

Read and validate the mapping's `count` field. Add a semantic regression row with a nonzero real
mapping; the existing zero-only shape assertion cannot detect this loss.

### R3-G4 — BLOCKER — F25 hashes the study inputs, not the registered frozen set

The program contract defines F25 as the existing product/model boundary: qb_v2 registry pointer,
model artifact, and manifest, plus `qb_v3_walk_forward.py` and the 2026-07-04 decision record.
The current implementation instead constructs the set from the four DynastyProcess snapshots and
caller-supplied crosswalk (`scripts/run_qb1_study.py:812-824`, caller at 1080-1082). Those study
inputs already have their own admission pins and are not F25.

The production composition's two observed checks contain exactly:

```text
crosswalk.json, values_2021.csv, values_2022.csv, values_2023.csv, values_2024.csv
```

None of the five registered F25 artifacts is present. Pin the exact runner-owned set and hashes;
do not accept a caller-selected subset. The currently clean hashes independently measured are:

- `app/config/model_registry.json` — `307200148e2c251e4b4de9ce3d03a02eab20839034dc3a8ba319a5a1298e1ac3`
- `app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl` —
  `d7acb6808e4a6caf412ec05b41aa90324e04f90ef219bbf78f680f66ea7d304f`
- `app/data/models/engine_b/v2_manifest.json` —
  `86f199bd069823cc292f8d56553dadc91f07f78bd47ac26498a06f16440984bc`
- `src/dynasty_genius/eval/qb_v3_walk_forward.py` —
  `7f3e9283afac1928629b3c04ef2ec71e85c99f3e55278f2237fcf9bedab4a3b5`
- `docs/validation/2026-07-04-build4-qb-v3-promotion-decision-record.md` —
  `a963b671dc6a1ef88bb73283acac594201b7cee3bda59a84681a03b810f6bd63`

### R3-G5 — BLOCKER — F13's ±1-yard/game arithmetic counts nonqualifying rows as games

`build_season_rushing` increments `weeks` for every weekly row
(`scripts/run_qb1_study.py:333-345`). The registered H2 continuous moderator divides by the exact
qualifying-game population: `(attempts + sacks_suffered) >= 1 or carries >= 1`
(`study_matrix.py:190-191`, `study_matrix.py:406-449`).

With 398.5 rushing yards on one qualifying row plus one zero-stat nonqualifying row, current code
uses two games and reports a minus-1-yard/game flip. The registered denominator is one game, whose
shifted threshold is 399; 398.5 does not flip.

**Ruling on the flagged F13 construction:** mapping ±1 yard/game to
`± qualifying_games yards` is acceptable in principle and needs no additional human ruling. The
games must be the exact registered qualifying-game population used by the H2 continuous
moderator. The current raw-row count is not that construction.

### R3-G6 — STYLE — the package module contract still says H5 refuses

`src/dynasty_genius/eval/qb_validation/__init__.py:14-17` still says the H5 lane refuses until its
behavioral RED lands. H5 is implemented. Update this remaining stale package-level description;
the corrected `status.py` wording is accurate.

## Verification evidence

- Frozen execution/program/inference bundle: **211 passed**, 12 numeric-boundary warnings.
- Amended reinforcement file: **344 passed**.
- Claude-authored round-3 contracts: **45 passed**, two expected synthetic Ridge warnings.
- Carried round-2 adversarial probe: **4/4 failed**, as expected after its corrections.
- New round-3 adversarial probe:
  `qb1_green_round3_adversarial_probe_codex_v1.py`, SHA-256
  `e6683d06e77b1f35c366b732385a0682bd867de0098bcc5f39231952576f27b6` —
  **5/5 defect reproducers pass**; Ruff clean.
- Ruff is clean on the five round-3 pinned implementation/test files.
- No secret-like credential assignments were found in the reviewed implementation/test boundary.
- The worktree remains broadly dirty and shared. This review changed only its evidence, ledger,
  and autonomy records; it did not alter Claude's implementation.
- The registered terminal report remains absent. No study result exists.

The full suite was not rerun merely to smooth over open execution blockers. Claude's disclosed
result remains 6,047 passed / 15 standing untracked cadence RED / zero tracked failures / zero
collection errors.

## Gate disposition

**NOT CLEAR.** David's held execution trigger does not fire. Correct R3-G1 through R3-G5, add
semantic regression rows that fail on every reproducer, address R3-G6, and return the complete
composition and terminal runner boundary for round-4 review. No study execution is authorized by
this review.
