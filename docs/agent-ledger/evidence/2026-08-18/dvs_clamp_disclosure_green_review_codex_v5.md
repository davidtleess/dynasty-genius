# DVS clamp-disclosure GREEN re-review — Codex v5

Date: 2026-08-18  
Thread: `w#dvs-disclosure-1`  
Verdict: **NOT CLEAR — F5 is closed; one stale contract statement contradicts the ruled blend semantics**

## F5 closed independently

The Round-5 parameterization supplies the missing positive controls at both Engine A
consumer sites:

- The normal Engine A consumer preserves both `dvs_clamped=True` and the derived
  `xvar_ceiling_bound=True`.
- The same true value survives through `build_universe_pvo_batch` to the serialized
  valuation row.
- The `games_t == 0` Engine-A-only fallback has its own path witness and preserves both
  true fields.

Independent hostile replay reproduced Claude's claimed sensitivity:

| Isolated mutation | Result |
| :-- | :-- |
| Primary consumer `pvo_assembler.py:364` forced to `False` | **2 failed, 11 passed** — the primary true control and serialized true control failed on their intended value assertions |
| Dead-window consumer `pvo_assembler.py:453` forced to `False` | **1 failed, 12 passed** — the path-witnessed dead-window true control failed on its intended value assertion |

Each mutation was applied alone and reverted before the next. After both reverts,
`pvo_assembler.py` returned to SHA-256 `8baf25c73f014af2edb255558dd13b00b32524fd7ae5b5ec57bd8216ce102898`,
and `rg -n "MUTATION" src/ app/ tests/` returned no matches.

## Finding F6 — the truth-contract docstring still states the rejected blend rule

`tests/contract/test_dvs_clamp_truth_red.py:11-17` says a blend is disclosed as
clamped when **either input component** was clamped. That is the superseded rule rejected
in Round 2. It directly contradicts all three current sources of truth:

- `tests/contract/test_dvs_clamp_connected_red.py:7-11`: the field describes what
  happened to the final score, so a blend is not clamped.
- `src/dynasty_genius/pvo_assembler.py:431-439`: the weighted average cannot exceed
  100 and therefore does not truncate; component truncation would require a separately
  named field.
- `test_blend_score_is_not_clamped_even_when_a_component_was`: the executable contract
  asserts `dvs_clamped=False` and `xvar_ceiling_bound=False` on that exact case.

This is not runtime breakage, but it is contract-of-record breakage inside a new test file:
the prose tells a future maintainer to implement the opposite public meaning from the code
and executable test. It also shows the required post-fix semantic sweep did not reach the
whole clamp contract bundle.

**Smallest remediation:** replace only the stale blend paragraph with the current ruled
semantics: the final blend score is not clamped; component truncation is a distinct,
currently unexposed fact. No test or production behavior needs to change. Then rerun the
22-test clamp bundle and scoped Ruff/diff/hash checks and reroute.

## Other independent checks

- Submitted pins exact: connected tests `7feecf0492762403…`; assembler `8baf25c73f014af2…`;
  Engine A `77a48c513b2c5155…`; batch serializer `188307a5f6fd42d7…`.
- Unmutated clamp bundle: **22 passed**.
- Clamp bundle plus Surface-3 preservation: **23 passed**.
- Repository collection: **6,235 tests collected**, zero collection errors.
- Ruff on `src`, `app`, and all four clamp/Surface-3 test files: **pass**.
- Scoped `git diff --check`: **pass**.
- Round 5 changed no production pin. The API/generated-client increment remains out of
  scope, so Studio R1 remains backend-half closed only.

No implementation, generated contract, product artifact, store, scheduler, commit, push,
or unrelated parked path was changed by this review.
