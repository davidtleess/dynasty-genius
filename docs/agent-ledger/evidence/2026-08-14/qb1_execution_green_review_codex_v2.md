# QB-1 Execution GREEN Review — Codex v2

**Cycle:** TW14-QB1-1  
**Review round:** green-review round 2  
**Verdict:** **NOT CLEAR**  
**Reviewed at:** 2026-08-14 16:54 EDT

No registered study execution occurred. No provider call, output publication, commit, push,
model change, or product-surface change was made by this review. QB rushing production (H2)
remains **UNDER TEST** with no result.

## Boundary and pins

The handed-off request independently hashes to
`a0bd4980ae83f5c2371a1c3277db3eea444b4b9ab71230a49c152d4bb1569f3e`.
All round-2 pins reproduce exactly:

- `execution.py` — `ed1252e6b6ab432c48323f467bfc9d46a83b9d9b2cac2b0f0de0c05a4c41a2a2`
- `status.py` — `1b7771f46bda0d80841e503f6daf17fd5bc3469123fa21ca0fe9887a58b6efdb`
- `__init__.py` — `96ec38ccfc0ec3fe9721fa046869ca57c57ed77711434bd49f86abbe04bb7ca3`
- `scripts/run_qb1_study.py` —
  `31e753f95a8a3dfc3bd3dd2366d46809b7f7e966bb808cb79857b2fd2e07802f`
- round-2 contracts —
  `f38e3bb81b90c4f76a21e467f6c386e5a61a263c6ec34e5dd6ab117f41593328`

The frozen execution/program/inference RED pins and the amended reinforcement pin also reproduce
unchanged. The active autonomy goal and scope match TW14-QB1-1; the run remains ACTIVE and the
execution gate remains held.

This is Layer 3 validation/execution work. Its Layer 1 substrate check was the hash-before-parse
7/7 admission seam plus the 17-snapshot completion receipt; its Layer 2 check was the static
FantasyPros-to-GSIS crosswalk and per-fold reconciliation path. Those dependencies are present,
but the Layer 2-to-3 H5 coverage computation is wrong as described in R2-G2.

## Round-1 disposition

The seven prior findings are materially addressed at their local seams:

- G1: the sanctioned `admit_and_load_validation_pool` translation composes receipt admission
  with F1.
- G2: missing/wrong registration pins refuse before snapshot parsing.
- G3: the callback runner rejects malformed success payloads and converts ordinary callback
  exceptions to metric-free failed artifacts.
- G4: an end-to-end composition script and hermetic composition contract now exist.
- G5: F33 scans occurrence-specific package/raw-root/loader marker classes.
- G6: impossible H5 numeric evidence refuses named.
- G7: duplicate case rows and impossible join cardinality refuse named.

The carried Codex probe now produces the disclosed **1 pass / 12 failures**: only the intentionally
unsanctioned raw two-stage pipe still passes. These positive corrections do not close the new
composition findings below.

## Findings

### R2-G1 — BLOCKER — CLI preflight failures still emit silence

`scripts/run_qb1_study.py:819-836` performs registration loading, F33 enforcement, D1 admission,
crosswalk loading, H5 snapshot admission, and DP parsing **before** entering
`qb.run_qb1_study` at line 839. Any ordinary or named failure in those operations escapes without
the D5 terminal artifact. A hermetic patch making `load_registration` raise
`QBValidationFailure("registration_pin_mismatch", "fixture")` produces:

```text
escaped_exception= QBValidationFailure registration_pin_mismatch: fixture
terminal_artifact_exists= False
```

The round-2 correction protects only failures raised by the later `execute` callback. Move all
fallible invocation work inside the terminal runner boundary (or add an outer terminal-artifact
boundary that preserves process-control behavior) and pin at least registration, F33, D1,
crosswalk, H5 snapshot, and parse failures through the real `main()` path.

### R2-G2 — BLOCKER — F18 uses the wrong H5 coverage denominator

`build_h5_lane` calls `validate_join_coverage(len(joined_rows), len(dp_rows), ...)` at
`scripts/run_qb1_study.py:256-259`; the fold-evaluable keys are not computed until lines 283-287.
F18 and registration §9.3 require coverage over the **fold's evaluable pool**, not over rows in
the market snapshot.

The adversarial fixture has 100 fold-evaluable player-seasons and one DP row that joins and scores.
The registered floor is 0.70. Current behavior is:

```text
fold_evaluable_pool= 100
h5_predictions= 1
true_evaluable_coverage= 0.01
reported_coverage= 1.0
excluded= False
```

This can admit a nearly empty market lane and let it enter H5 inference. Compute the exact common
fold-evaluable pool first, report its denominator separately, and apply the registered floor to
that population.

### R2-G3 — BLOCKER — an incomplete success report is accepted and published as `ok`

The canonical registration says every report carries its exact eight `disclosures`. D5 requires
each fold's five-category attrition block and `metrics_with_CIs`. Current composition returns no
`disclosures`; each fold carries only `target_evaluable` and `no_target_season`; and no fold carries
`metrics_with_CIs` (`scripts/run_qb1_study.py:739-814`). The terminal assembler's closed success
shape also has no disclosures input (`execution.py:632-700`), while `validate_report_output` checks
No-Verdict language rather than the D5 nested schema.

The full hermetic composition returns `run_status=ok` with:

```text
top_level_disclosures_present= False
fold_metrics_with_CIs_present= False
fold_attrition_keys= ['no_target_season', 'target_evaluable']
missing_required_attrition=
  ['cohort_ineligible_prior', 'cohort_ineligible_unobserved',
   'manifest_missing', 'rookie_no_priors']
```

Extend the success assembler and structural validator to enforce the registered disclosures,
exact fold census vocabulary/semantics, per-fold metrics and CIs, flag vocabulary, and required
comparison fields before atomic publication. A fixture that merely supplies the five top-level
metric blocks is not a complete D5 schema test.

### R2-G4 — BLOCKER — F25 is implemented but never wired into the runner

F25 requires before/after byte hashes of the real frozen set, asserted by the runner. Production
search finds `validate_frozen_hashes` only at its definition/export; the composition script never
calls it. Patching that function to increment a counter and raise, then running the full hermetic
composition, still returns `run_status=ok` with `f25_gate_calls=0`.

Pin the real frozen set, validate it before the analytical work and again immediately before
terminal success publication, and convert any drift to the named metric-free
`frozen_boundary_drift` artifact. The check must exercise the production invocation, not only the
standalone helper.

### R2-G5 — BLOCKER — F13 is a declaration, not the required sensitivity panel

The design's F13 contract explicitly puts the existing binary `is_dual_threat` flag in scope and
requires a binary-gate versus continuous-rushing-moderator panel with ±1 yard/game boundary cases.
`build_sensitivity_panels` instead emits constants and prose:

```text
binary_dual_threat_gate=False
continuous_rushing_moderator=True
boundary_cases_yards_per_game=[-1, 1]
```

There are no binary results, continuous results, deltas, or metrics; `require_threshold_sensitivity`
only checks key presence and the boundary literals. This does not measure the comparison named by
F13. If the frozen registration genuinely leaves the calculation under-specified, do not invent a
choice inside the run: obtain the required human ruling or registered clarification before
execution. In either case, the current descriptive placeholder is not execution-clear.

### R2-G6 — WARN — success provenance drops ten admitted D1 snapshot hashes

The real completion receipt has 17 D1 snapshots: six single-file datasets and 11 PBP snapshots.
`admit_fetch_manifest` retains only each dataset's first path/SHA in metadata
(`execution.py:162-188`), and `compose_study` derives `inputs.snapshot_ids` only from those seven
values (`scripts/run_qb1_study.py:781-798`). All 17 are verified before parsing, but ten PBP hashes
are absent from the terminal provenance. Preserve and emit every admitted snapshot identifier so
the report identifies the complete source set it used.

### R2-G7 — STYLE — `status.py` still documents H5 as unimplemented

`status.py:11-15` says H5 is a later slice whose RED is not authored and that the module refuses
H5, while the module now implements and accepts the H5 decision function. Update the stale module
contract so future reviewers do not inherit the opposite of current behavior.

## Verification evidence

- Frozen execution/program/inference bundle: **211 passed**, 12 numeric-boundary warnings.
- Revised reinforcement file: **344 passed**.
- Claude-authored round-2 contracts: **37 passed**, one expected synthetic Ridge warning.
- Carried Codex probe: **1 passed / 12 failed**, matching the disclosed correction pattern.
- New round-2 adversarial probe:
  `qb1_green_round2_adversarial_probe_codex_v1.py`, SHA-256
  `fb17fd029b0a024778d3de9914737b933cea404899d4a1c6e9c14ea2c2f07fb2` —
  **4/4 defect reproducers pass**; Ruff clean.
- Ruff is clean on the five round-2 pinned implementation/test files.
- No secret-like credential strings were found in the reviewed implementation/test boundary.
- The worktree is broadly dirty and shared; this review added only its evidence artifacts and
  ledger/run-state records and did not alter Claude's implementation.
- The registered terminal report is absent at review close; no study result exists.

The claimed full-suite result was not rerun to smooth over open execution blockers. Its disclosed
15 failures remain the standing untracked cadence RED, with zero collection failures.

## Gate disposition

**NOT CLEAR.** David's held trigger does not fire. Correct R2-G1 through R2-G5, pin regression
contracts that fail on each reproduced defect, address R2-G6, and return a new complete composition
boundary for review. No study execution is authorized by this review.

