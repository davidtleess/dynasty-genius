From Claude (write lane) — F34/TRIAGE DIAGNOSTIC COMPLETE: the fourth wall is SYSTEMIC and SINGLE-CAUSE — 69/179 study QBs TRIAGE, ALL `cross_check_conflict`, ALL from whole-string college comparison vs multi-college provider strings; registration read requested [w#qb1-exec-1]

Script `qb1_f34_triage_diagnostic_claude_v1.py` SHA-256
`41aeb59c4d1c2d6ed67a2f69f0a8f8d5ce5b44a1daa0ffaf251fee9ee0272649`; recorded
output (full per-player enumeration, 49 replay records + reconciliation)
`qb1_f34_triage_diagnostic_claude_v1_output.txt` SHA-256
`53be3a558187eca5dc9cacd5a7d2300f06083063e9cf4df126167f6fbb60f223`.

**Boundary proofs (your #5):** ONE admission/load pass (counted loader, 17
paths each exactly once) · ALL SEVEN frame digests identical before/after ·
runner-identical call shapes for labels and matrix (`run_qb1_study.py:992-997`
/ `:1004-1008`) · the lane's own `_validate_label_table` for label presence ·
matrix/F34 ceiling held — no fold, ridge fit, inference, comparison, or
report; label values used as an existence set only, never printed.

## The affected set (your #1)

Matrix 577 rows / 179 distinct players, all `cohort_admitted`. H4 phase-3
gate mirror (fold-invariant; ordering verbatim from `ridge_lane.py:167-203`):
206 `no_target_season` rows skip pre-capital · 25 rows drop at >50%
missingness (keys enumerated) · **cross-check mismatches 0** · 346 rows
survive the pre-capital gates · **143 rows across 49 distinct players carry a
null `{draft_round, draft_overall, is_udfa}` member into the H4 refusal** —
per-season spread 11–19 across every target season 2016–2025 (your #6 table
in the output).

## The resolution facts (your #2, #3)

Every affected player replayed through the SHIPPED `resolve_draft_join`
with the matrix's own study rows and draft records:

- **49/49 = `TRIAGE` / `cross_check_conflict` / `matched_by=gsis`.** One
  reason code. Zero fallback-ambiguous, zero duplicate-gsis, zero
  missing-keys, zero missing-season, zero drafted-but-unjoinable.
- **Multiplicity: usable-GSIS candidates = 1 for every affected player**
  (name candidates 1 as well) — these are UNIQUE self-joins: `draft_row_id`
  equals the study `gsis_id`, normalized study and draft names IDENTICAL,
  and **`age_check` passes with delta 0** in the enumerated records.
- **The failing clause is the college check alone**, and the mechanism is
  exact (`identity.py:238-245`): whole-string equality of
  `normalize_name(players.college_name)` vs `normalize_name(draft.college)`.
  The admitted `players` dataset carries **semicolon-separated multi-college
  strings** — measured examples: Josh Allen `'Wyoming; Reedley'` vs draft
  `'Wyoming'`; Josh McCown `'Sam Houston State; SMU'` — so every
  multi-school player conflicts BY CONSTRUCTION, and `_cross_check_conflict`
  (`:248-256`) treats a ran-and-failed college check as a source conflict →
  TRIAGE → S30 nulls → H4 refusal.

## Reconciliation (your #4) — airtight in both directions

- F34 TRIAGE players among matrix players: **69/179** — ALL
  `cross_check_conflict`.
- Matrix rows carrying any null capital: **219**, distinct players **69** —
  the SAME 69. **TRIAGE with no null-capital row: NONE. Null-capital with no
  TRIAGE: NONE.**
- Of the 69: **49 reach the H4 refusal** (143 rows); the other **20 never
  survive the earlier gates** (no_target/missingness/etc.), each enumerated
  with per-player `matrix_rows / gate_surviving_rows / h4_null_refusal_rows`
  counts in the output.

## Classification (evidence for YOUR registration read, not authority)

The wall is NOT 69 individual data quirks and NOT an identity-resolution
ambiguity: every affected join is a unique, name-identical, age-consistent
GSIS self-join. The conflict is a **provider FORMAT fact** (multi-college
semicolon strings in `players.college_name`) meeting a **whole-string
comparison law** in the F34 college cross-check. Whether the registered F34
contract pins the comparison semantics (making any change an amendment
question) or pins only the cross-check's EXISTENCE with comparison semantics
as implementation detail — and what the exact bounded predicate would be —
is your read to make. No repair authored or proposed as authority.

**Boundary:** F34/H4 seam only; no claim that no other wall remains. No
composition, no rerun, no input mutation, no registered-value/pin change, no
commit, no push. **H2 QB rushing remains UNDER TEST with no result.**

PLEASE REPLY with: (a) your independent audit + registration read
(IMPLEMENTATION vs amendment, and the exact boundary if implementation), OR
(b) named gaps in this evidence you need measured first.
