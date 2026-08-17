# QB-1 exclusion-row alignment Round 20 — open receipt

Date: 2026-08-16 (America/New_York)  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`  
Transition: revision 125 → revision 126  
Phase: ACTIVE `green-review`, Round 20 open  
Open snapshot: `cf5062ed249249b79b86d0b2a8134cab729518fed6ac86232ae644d9b1a7bd92`

Codex independently accepted diagnostic script `d83f5be1…` and output
`37d935dd…`, reproduced all 33 digest pins, and classified the measured seam
as **implementation, not amendment**, subject to the terminal-adapter-only
boundary in `qb1_exclusion_row_registration_read_codex_v1.md` (`0453ca80…`).

Exact scope:

- `scripts/run_qb1_study.py`
- `tests/contract/test_qb1_green_correction_contracts.py`

The round may canonicalize the exact internal reason `empty_common_pool` out
of terminal comparison exclusions only when `fold_starved` co-occurs. It must
preserve internal inference, the publication vocabulary, the registration,
all other reason words, entry metadata, metrics, uncertainty, statuses, and
claims. Missing `fold_starved`, duplicate `empty_common_pool`, malformed
shapes, and unrelated unknown words remain fail-closed.

RED-first coverage, the focused and five-file suites, static checks, synthetic
terminal publication, and one final metric-free real composition projection
are required. No registered runner or rerun is authorized during Round 20. A
fresh rerun remains held for Codex's explicit CLEAR after independent review.
No commit or push.

H2 QB rushing remains **UNDER TEST with no result**.
