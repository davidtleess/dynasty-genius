# QB-1 green-review Round 22 — Codex v1

Date: 2026-08-16/17 (America/New_York)  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`  
Round: 22, revision 130  
Verdict: **CLEAR / READY_FOR_GATE**

## Review result

No blocking correctness, safety, scope, or evidence finding remains at the
submitted pins. Round 22 completes the bounded terminal-adapter correction and
hardens exactly the two measured exclusion-clause refusal details against
payload-controlled representation or type-name execution.

This verdict resolves `finding-green-review-20-1` and
`finding-green-review-21-1`. It releases exactly the one fresh registered
rerun authorized by David's words, "ok lets get it fixed and keep going," and
the revision-130 boundary. It does not itself execute the runner, publish or
interpret a result, commit, push, or rule on a registered comparison.

## Scope and final pins

The reviewed change is confined to the three authorized files:

- `scripts/run_qb1_study.py` —
  `dd23f639378e42f69e2c551f56be1556e0647fd8f761c4cfab3f03022b8012fb`
- `src/dynasty_genius/eval/qb_validation/execution.py` —
  `7367bee7a5e3688bb9aa28c34233246aead84c152007ae62884e31be4c6bf2d4`
- `tests/contract/test_qb1_green_correction_contracts.py` —
  `c3443751aee0eafe99a83fff2d839cdc7f45e80349835f411984248a862d58df`

The registered vocabulary, validation predicates, registration, inference,
metrics, statuses, comparison producer, identity/input machinery, and sibling
validator clauses remain unchanged. The existing terminal artifact remains
`0c0cd6308a14dc44a177335ddafc2876f65e2010d3ae1748e8e912e197540956`;
the Round-19 stdout receipt remains
`ceb2fba7a8c18b9b48380de5037e0e8b00c09f80681bc297a23e02700109bb7f`.

## Correctness and boundary review

- `_canonical_excluded_folds` performs no `repr`, `str`, type-name, hashing,
  or other derivation on unreadable shapes. It inspects the exact internal
  token only for a Mapping entry whose `reasons` is a list or tuple; all other
  shapes pass unchanged to the registered validator.
- The adapter removes only one `empty_common_pool` when `fold_starved`
  co-occurs. It refuses duplicate or implication-breaking instances by the
  established `report_schema_invalid` machine reason, preserves other words,
  order, metadata, `None`/empty values, and never mutates the inference record.
- Reprojection uses built-in list/tuple construction only, so payload-supplied
  sequence-subclass constructors cannot execute.
- The non-list `excluded_folds` refusal and malformed exclusion-entry refusal
  now use fixed structural wording. Neither detail accesses, formats,
  represents, hashes, stringifies, or type-names the refused payload.
- Both public catch phases publish the atomic six-key metric-free
  `report_schema_invalid` artifact; hostile representations cannot become
  `execution_error` or escape without an artifact. The already-validated
  registered row id is the only retained interpolation.
- Sentinel-bearing refused content reaches neither the terminal artifact nor
  captured CLI stdout/failure-origin diagnostics. Successful surfaces remain
  unchanged.

## Independent verification

- Round-20/21/22 focused contracts: **18 passed** at the final pins.
- Five-file QB-1 regression bundle: **739 passed** in 53.89 seconds, exit 0.
- Scoped Ruff, strict `py_compile`, and `git diff --check`: **clean**.
- Claude correction contracts: **184/184**.
- Claude uncontended full-suite census: **6,186 passed / 15 standing cadence
  RED failures / 12 skipped** in 8:56. The final three named failures and the
  summary were read directly from the task receipt; the failure count matches
  the standing untracked `test_governed_cadence_inputs_red.py` set, with zero
  tracked regression.
- An earlier suite attempt overlapped the CPU-heavy projection and added one
  `test_verify_closeout.py::test_script_is_executable_end_to_end` 120-second
  timeout. It is disclosed and excluded from evidence. The same closeout path
  completed within its limit in the uncontended final suite.

## Real-surface and mutation proof

The required final projection ran once at the final pins outside the
registered runner and aborted at the defense-in-depth validator seam before
the validator returned. Evidence:

- script `qb1_exclusion_row_postgreen_projection_claude_v2.py` —
  `c043279e8324897585c34f6ed4359f4aa56b841852c25ee92e29565a2d00aa58`
- output `qb1_exclusion_row_postgreen_projection_output_claude_v2.json` —
  `de36bef716ec001db83369067861338f1dccf2e14606d11390ac82cbaabb1ef0`

Independent checks confirmed `passed=true`, the intercept fired, the replay
aborted before validator return, all 14 comparison rows were present, all
12 exclusion entries satisfied the unchanged clause, and zero reason words
fell outside the registered vocabulary. Every recorded before/after digest
was independently recomputed with **zero mismatches**, including all frozen
inputs, scope files, terminal artifact, and prior receipt.

Two earlier final-evidence attempts were deliberately stopped after subsequent
test-only pin changes and emitted no final projection output. They are not
cited. The contended suite is likewise not cited as final evidence. No
registered runner, provider fetch, input mutation, terminal write, receipt
mutation, commit, or push occurred during Round 22 or review.

## Layer and registered-study disposition

Layer served voluntarily pending ratification: Layer 3 registered-study
publication integrity. The Layer-1/2 dependency set was checked through the
frozen-input and code digests above and remained byte-identical; this round
grants no authority to alter ingestion, identity, curation, registration, or
study design.

H2 QB rushing remains **UNDER TEST with no result**. The released rerun is one
registered execution only. Any completed readout must go untouched to David
for his separate ruling; a named failure consumes the grant and re-parks the
loop fail-closed.
