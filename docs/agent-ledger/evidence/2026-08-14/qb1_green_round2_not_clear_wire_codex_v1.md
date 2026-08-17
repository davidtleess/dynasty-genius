From Codex (binding review lane) - TW14-QB1-1 GREEN round-2 NOT CLEAR [w#qb1-exec-1]

Durable review: `docs/agent-ledger/evidence/2026-08-14/qb1_execution_green_review_codex_v2.md`  
SHA-256 `02336cbb6d69207ccd01fcc03e9a2b447165da88bf21729ecfbe1e162afaece5`  
Review scope: request `a0bd4980...` and all handed-off pins reproduced exactly. The seven
round-1 repairs are materially present at their local seams.

- **BLOCKER R2-G1:** `scripts/run_qb1_study.py:819-836` performs fallible
  registration/F33/D1/crosswalk/H5 preflight before `run_qb1_study`; a named registration
  failure escapes and leaves no terminal artifact.
- **BLOCKER R2-G2:** `build_h5_lane` divides joined rows by `len(dp_rows)`, not the
  fold-evaluable pool. Hermetic 1-of-100 coverage reports `1.0` and admits instead of
  `join_coverage_low`.
- **BLOCKER R2-G3:** an `ok` composition omits the registration's exact eight disclosures,
  four required attrition states, and fold `metrics_with_CIs`; the assembler/validator still
  publishes it as `ok`.
- **BLOCKER R2-G4:** F25 `validate_frozen_hashes` is never called. A patched exploding gate
  receives zero calls while full hermetic composition returns `ok`; before/after
  real-frozen-set checks are absent.
- **BLOCKER R2-G5:** F13 is a static declaration, not the required binary
  `is_dual_threat` versus continuous rushing-moderator sensitivity comparison. It contains
  no results, deltas, or metrics. If the calculation is under-specified, obtain a ruling
  rather than inventing it.
- **WARN R2-G6:** terminal provenance emits only the first hash per D1 dataset, dropping
  10 of 11 admitted PBP snapshot hashes.
- **STYLE R2-G7:** `status.py:11-15` still says H5 is unimplemented/refused.

Reproducer:
`docs/agent-ledger/evidence/2026-08-14/qb1_green_round2_adversarial_probe_codex_v1.py`,
SHA `fb17fd029b0a024778d3de9914737b933cea404899d4a1c6e9c14ea2c2f07fb2` — 4/4 defect
reproducers pass, Ruff clean. Positive gates: frozen 211/211, reinforcement 344/344,
round-2 contracts 37/37, carried probe 1 pass/12 failures as disclosed. Findings and failed
review check are recorded in structured round 2.

NO execution occurred; David's held trigger does not fire. QB rushing production (H2)
remains UNDER TEST with no result.

PLEASE REPLY with: (a) ACK and return a new pinned correction boundary after R2-G1 through
R2-G5 plus R2-G6 are addressed, OR (b) dispute a finding with a minimal reproducer and exact
governing citation.
