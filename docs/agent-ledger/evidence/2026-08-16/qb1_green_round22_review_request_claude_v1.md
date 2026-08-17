From Claude (write lane) — Round-22 GREEN complete at stable final pins: adapter derivation-free, two validator messages fixed-wording, all corrections incorporated; real-surface projection PASSED (12/12 conforming); request independent review of BOTH carried findings [w#qb1-exec-1]

# QB-1 Round-22 review request — Claude v1

Date: 2026-08-16/17 (America/New_York)
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`, revision 130, green-review Round 22
Authority: registration read `063f8453…` + your mid-round corrections
`[w#5hbt8yxh-1]` (no type-naming; fixed wording only; hostile-metaclass RED)
and `[w#6wxdinst-1]` (docstring truth; built-in construction only) and
`[w#cw9yvjwk-1]` (zero-leakage proof on both surfaces) — ALL incorporated.

## Final pins (stable; review at exactly these)

- `scripts/run_qb1_study.py`
  **`dd23f639378e42f69e2c551f56be1556e0647fd8f761c4cfab3f03022b8012fb`**
- `src/dynasty_genius/eval/qb_validation/execution.py`
  **`7367bee7a5e3688bb9aa28c34233246aead84c152007ae62884e31be4c6bf2d4`**
- `tests/contract/test_qb1_green_correction_contracts.py`
  **`c3443751aee0eafe99a83fff2d839cdc7f45e80349835f411984248a862d58df`**

Out-of-scope pins byte-identical: identity `7cf41737…`, study_matrix
`6c607bad…`, qb_ppg_labels `e5cb3955…`, status `67651821…`, adapter
`021be207…`, errors `864b63f7…`, comparisons `7d50a0a7…`.

## What changed (exactly the ruled boundary)

**Adapter (`_canonical_excluded_folds`):** ALL repr/stringification removed;
exact-token inspection ONLY in structurally readable shapes (Mapping entry +
list/tuple reasons); unreadable shapes pass through UNCHANGED (docstring now
states this truth); reprojection via BUILT-IN `tuple(...)`/`list(...)` only —
never a payload-supplied subclass constructor; R20 token/`fold_starved`
implication, refusals (no-implication, duplicate), unknown-word/None/empty/
metadata preservation, and input non-mutation unchanged.

**Validator (ONLY the two exclusion-clause refusal details):** both messages
are now FIXED structural wording with ZERO derivation from the refused
value — no access, formatting, repr, str, hashing, or type naming. The
already-validated registered row id interpolation retained as reasoned.
Predicates, `_refuse`, machine reason, vocabulary, registration, sibling
clauses, inference, metrics, statuses, claims untouched.

## RED-before-GREEN (all observed failing first)

Round-21/22 REDs: pass-through re-specification · adapter hostile-`__repr__`
· e2e hostile entry (the Round-21 STOP measurement) · e2e hostile CONTAINER
`__repr__` · CLI execute-phase hostile entry (both catch phases covered:
publication_gate via public runner, execute via composed-payload gate call) ·
hostile-METACLASS `__name__` (armable hostility so pytest's own reporter
survives — disclosed) · hostile list/tuple SUBCLASS constructor (never
invoked; order + ordinary form preserved). Disclosed green-pre-impl
regression guards: plain-string unreadable shapes refuse at the gate e2e;
unrelated-metadata token; sentinel-reason artifact row.

## Zero-leakage proof, both surfaces

The CLI execute-phase test plants a sentinel INSIDE the refused entry and
asserts it absent from BOTH captured stdout (summary + failure_origin
diagnostic) AND the terminal artifact; the artifact-only row is renamed to
claim exactly what it asserts.

## Census at the final pins

- Correction contracts **184/184** (183 + 1 subclass row reconciles).
- Five-file bundle **739/739** (738 + 1 reconciles).
- **Full suite 6,186P / 15F / 12S in 8:56, run ALONE** — all 15 BY NAME the
  standing untracked `test_governed_cadence_inputs_red.py`; zero tracked
  failures (6,185 + 1 reconciles).
- **Disclosed, not cited:** an earlier suite run executed CONCURRENTLY with
  the ~28-min projection replay showed a 16th failure —
  `test_verify_closeout.py::test_script_is_executable_end_to_end`,
  `subprocess.TimeoutExpired` at its 120s limit under CPU contention from my
  own parallel scheduling. Root-caused, reproduced solo-PASS on the idle
  machine in the clean run above; no semantic contact with this round's diff.
- Scoped Ruff + strict `py_compile` clean.
- **Real-surface projection at the final pins: PASSED** — one composition
  replay, intercepted + aborted before the validator returned; the REAL
  composed payload now shows 14 comparison rows, 12/12 exclusion entries
  satisfying the exclusion-row clause, ZERO reason words outside the
  unchanged vocabulary; before/after digests identical (script `c043279e…`,
  output `de36bef7…`).

## Boundary compliance

No registered runner or rerun, no provider fetch, no input mutation, no
commit, no push. Neither carried finding (R20-G1, finding-green-review-21-1)
is resolved by me — both are yours to judge at these pins. The fresh
registered rerun remains HELD on your explicit CLEAR. H2 QB rushing remains
**UNDER TEST with no result**.

PLEASE REPLY with: (a) explicit CLEAR with enumerated checks (resolving the carried findings and releasing the one fresh registered rerun), OR (b) findings at the exact pins above.
