# QB-1 Execution GREEN Review — Codex v4

**Cycle:** TW14-QB1-1 continuation  
**Semantic review round:** 4 of 5  
**Verdict:** **NOT CLEAR**  
**Reviewed at:** 2026-08-14 19:09 EDT

No registered study execution occurred. No provider call, result artifact publication, commit,
push, model change, or product-surface change was made by this review. QB rushing production
(H2) remains **UNDER TEST** with no result.

## Authority, state, and pins

The handed-off request independently hashes to
`2369fa139b6bfaa62fd93f4983941af79103c3256bfad5860d105905790215a0`.
All round-4 pins reproduce exactly:

- `execution.py` — `45f9df8433f781d1b251a91da8c7b52d0b9e30ce367aee209dd5f2eedf23ee21`
- `status.py` — `6765182185ad82e048a8f37736f8285795ac4db6dec4c7d47d22ae0a302cba79`
- `__init__.py` — `d8876020f1fe3414d75612d5a4abfd26307ce9e9bfbdbfe6480ffcf8c81a9518`
- `scripts/run_qb1_study.py` —
  `48d27a5f83a7cda97327df4e3f08950fadccd6d0d50584f255ecf514f31387f4`
- correction contracts —
  `531ed5ee5068f7a294523322c33992b02650a9f71109441ba08b477ebc6f1259`
- amended execution RED —
  `5d3bc660aed3bbb63604ab1d8ac829bf4876213a53469d69ef7c71feffd77c5a`

The program RED (`7e950792…`), inference ratchet (`25c4ffde…`), and reinforcement
(`db351f8c…`) are unchanged. The five F25 files independently reproduce the newly pinned hashes.

David's continuation disposition is present in the current goal as his verbatim word `continue`.
The archived run exists at the disclosed location, has id `b71626b2…`, terminal state `BLOCKED`,
and preserves framing round 1 plus GREEN-review rounds 1–3. The live continuation has id
`f8f7551c…`, is ACTIVE, and explicitly holds execution until Codex CLEAR.

The RED amendment is exactly the authorized fixture change. Removing the four explanatory comment
lines and four `disclosures=` fixture lines from the amended file reconstructs the old full hash
`4e6d7dc5c090aacadc530fbb0292736a5ab745621bdcc2167400a66f210b3f2d`.

This is Layer 3 validation/execution work. The admitted source provenance remains complete, the H5
identity path uses the fold-evaluable denominator, and the exact product/model F25 boundary hashes
clean. The remaining implementation finding is at the Layer 3 publication gate, not an authorization
to alter Layers 1–2.

## Round-3 disposition

All six targeted R3 findings are materially corrected at their named seams:

1. The terminal runner now requires a canonical registration object for `ok`, the assembler
   requires disclosures, and registration-load failures remain visible artifacts.
2. Fold flags are checked against the closed D5 vocabulary and production emits the registered
   reason without a prefix.
3. `lane_manifest_missing` reads the ridge mapping's integer count and refuses unreadable shapes.
4. F25 is the exact five-file product/model boundary, checked before and after composition; the
   crosswalk and DP hashes are separately framed as input admission.
5. F13 now counts only the registered qualifying-game population in its ±1-yard/game arithmetic.
6. The package-level H5 description is corrected.

The carried round-3 probe now fails **5/5** and the carried round-2 probe fails **4/4**, matching the
disclosure. These local corrections do not close the findings below.

## Findings

### R4-G1 — BLOCKER — the runner still publishes semantically incomplete or impossible D5 reports as `ok`

The new runner invariant calls `validate_registered_report_blocks`, but that validator is shallow
(`execution.py:810-887`). It validates exact disclosures, attrition key names, a metrics mapping,
the flag vocabulary, and nine generic comparison fields. It does **not** validate:

- required `inputs` fields (`snapshot_ids`, `settings_hash`, `matrix_version`);
- the registration's exact eight fold seasons/cardinality or nonnegative census values;
- the exact 14 registered comparison ids, lanes, and directions;
- the disjoint model/H5 status vocabularies or H5-only `p_ni` / `ni_met` requirements;
- the registered case-panel identities/cardinality;
- the three required sensitivity panels and their registered contents.

The correction fixture itself calls a one-fold, one-comparison, dummy-sensitivity payload
`_complete_ok_payload` and pins it as a valid success (`test_qb1_green_correction_contracts.py:
204-255,309-320`). Four hermetic public-runner reproducers currently publish `ok`:

```text
folds=1 (registered=8), comparisons=1 (registered=14)
inputs={'snapshot_ids': ['only-one']}  # settings_hash/matrix_version absent
n_evaluable=-1; no_target_season=-4; manifest_missing.h1=-7
model support_status='market_superior'
H5 row without p_ni or ni_met
case_panel=['not_a_registered_case']
sensitivity_panels=['not_a_registered_panel']
```

This contradicts the runner's own claim that the returned payload is never trusted and that the D5
registered schema is a publication invariant (`execution.py:898-922,963-990`). An invalid terminal
artifact can therefore be atomically blessed even though the production composer happens to build
more complete blocks.

Extend the publication validator over the entire registered D5 shape: exact input fields; exact fold
season set and nonnegative integer census/manifest counts; exact 14 contrast identities with
registration-bound lane/direction and lane-specific fields/status vocabulary; `require_case_panel`;
and the exact required sensitivity panels through their existing validators. Amend the current
"valid success" fixture to be genuinely registration-complete and pin every survivor above as a
named metric-free `report_schema_invalid` publication.

### R4-G2 — BLOCKER — the continuation resets the mechanical five-round cap

David's `continue` word validly authorizes continuation, and the prose goal says the current round
counts as semantic round 4. The structured state does not implement that count:

```text
archived: framing/1, green-review/1, green-review/2, green-review/3
current:  green-review/1
```

The installed loop-control implementation explicitly states that it is a pure function of the
current run object and does not infer rounds from history (`loop-control.mjs:1-6`). `openRound`
checks only `rounds(run).length` / `phaseRounds(run, phase).length` and sets the next index to that
current-run length plus one (`loop-control.mjs:173-200`). It does not parse the continuation goal or
the archive reference.

Consequently, after this BLOCKER the next structured round will be GREEN-review **2**, not cap round
5, and the ratified phase cap will not fire at semantic round 5. The request's statement that the
cap keeps counting is presently true only in prose. That makes the active safety hook malformed for
this continuation.

Before opening the correction round, preserve the three prior GREEN rounds in cap-bearing current
state or use a validated continuation-offset mechanism that the loop-control code actually consumes.
Do not rely on a goal-string convention the quantifiable loop explicitly does not parse.

### R4-G3 — STYLE — the registered-validator docstring describes the now-removed fixture exception

`execution.py:818-823` still says the schema check is separate rather than unconditional because
the frozen execution fixtures carry no disclosures. Round 4 amended that fixture to carry the exact
disclosures and made the runner gate unconditional. Remove or correct the stale explanation.

## Verification evidence

- Frozen execution/program/inference bundle + reinforcement + correction contracts:
  **606 passed** = 211 + 344 + 51, with 14 disclosed numerical warnings.
- Carried Codex probes: round 3 **5/5 failed**; round 2 **4/4 failed**, as expected after correction.
- New round-4 adversarial probe:
  `qb1_green_round4_adversarial_probe_codex_v1.py`, SHA-256
  `acb4f8190cafbc0f6a4ddaea21b0991029bd7099378e987d941d71a1768dc83a` —
  **4/4 defect reproducers pass**; Ruff clean.
- Ruff and strict Python compilation are clean on all round-4 implementation/test files.
- `git diff --check` is clean.
- The exact five F25 artifact hashes match their pins; the output root is gitignored and its raw
  directory is covered by the backup manifest.
- No secret-like credential assignments were found in the reviewed implementation/test boundary.
- The registered terminal report is absent; no study result exists.
- The worktree remains broadly dirty and shared. This review modified only its evidence, ledger,
  and structured review records; it did not edit Claude's implementation or test contracts.

Claude's full-suite claim was not rerun merely to smooth over an open publication blocker. Its
disclosed result remains 6,053 passed / 15 standing untracked cadence RED / zero tracked failures /
zero collection errors.

## Review-process disclosure

One overly broad read-only search command unintentionally traversed the sibling cockpit's protected
`frontend-studio/` subtree, contrary to TW29-WALL-35. Those results were discarded and not used; no
Studio path was written, copied, moved, routed, or acted on. Subsequent loop-control inspection was
narrowed to the exact non-Studio autonomy source path. The violation is recorded here and in the
daily ledger rather than hidden.

## Gate disposition

**NOT CLEAR.** David's held execution trigger does not fire. Correct R4-G1, repair the continuation's
mechanical cap state before opening semantic round 5, address R4-G3, and return the complete terminal
publication boundary at the cap round. No study execution is authorized by this review.
