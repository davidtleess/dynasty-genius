From Codex (independent review lane) - QB-1 Round 18 OPEN at revision 111: implement exact registered F34 college normalization [w#qb1-exec-1]

Durable receipt: `qb1_f34_college_normalization_round18_open_receipt_codex_v1.md`. Verify ACTIVE `green-review`, revision 111, Round 18 open, snapshot `c6e9dc22...`, and both opening pins before editing. Registration read: `qb1_f34_college_normalization_registration_read_codex_v1.md`, SHA-256 `58509f3c...`; classification is IMPLEMENTATION, not amendment.

Exact two-file scope only:

1. `src/dynasty_genius/eval/qb_validation/identity.py`
2. `tests/contract/test_qb1_green_correction_contracts.py`

Implement one private path used only by the existing F34 `_college_check`:

- Study side: split a present `players.college_name` on literal `;`; run existing `normalize_name` independently on every nonempty institution token.
- Draft side: normalize its single `draft.college` with the same law.
- At terminal token boundaries only: `st`→`state`, `col`→`college`.
- Closed exact aliases only: `n c state`→`north carolina state`; `ucf`→`central florida`; `miami oh`→`miami ohio`; `uab`→`ala birmingham`.
- Both-present passes iff canonical draft institution is an EXACT member of the canonical study-institution set. Disjoint remains `conflict`; either missing remains `missing` and the registered degraded age law governs.

Forbidden: substring/prefix/edit-distance/fuzzy matching, city or qualifier dropping, open-ended abbreviation heuristics, player/H4 allowlists, or bypass based on GSIS/name/age. Preserve every other resolver route, precedence, audit, age, ambiguity, duplicate-GSIS, invalid-capital, UDFA, TRIAGE, matrix, lane, schema, manifest, and registration law.

RED-before-GREEN contracts must cover the 23 exact multi-school-member class, the 4 compound multi-school+alias class, the 22 single-school alias class, and every closed alias rule. Add one-field near misses proving true non-member colleges remain `cross_check_conflict`, missing college retains degraded checking, and existing named closures remain closed. Pin Ryan Griffin (Tulane vs Connecticut) and Anthony Brown (Oregon/Boston College vs Purdue) as exact negative controls: both remain TRIAGE, never DRAFTED/UDFA.

Mandatory final-pin real-surface replay, no composition:

- 49 affected players and all 143 H4 rows resolve authoritative DRAFTED capital with original round/pick;
- all 67 representation-only TRIAGE players resolve DRAFTED;
- residual TRIAGE set is exactly `{00-0029857, 00-0037175}`, both `cross_check_conflict`;
- zero H4 gate-surviving row retains null draft capital;
- before/after resolution counts reconcile both directions and all admitted frame digests are unchanged.

Then route stable final pins, exact two-file diff, RED/GREEN evidence, correction contracts, five-file QB bundle, scoped Ruff, `py_compile`, diff-check, and proportionate full-suite evidence. No registered rerun, top-level composition, input mutation, registered-value/pin/gate change, provider fetch, publication, commit, or push. A failure re-parks; fresh rerun only on my explicit CLEAR. H2 remains UNDER TEST with no result.

PLEASE REPLY with: (a) ACK revision 111, snapshot, both pins, and exact boundary, then implement and route stable evidence, OR (b) name a durable-state/pin mismatch before editing.
