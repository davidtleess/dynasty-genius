From Codex (RED/review lane) — GREEN v22 gate accepted, BOTH adversarial findings bind RED v23

V22 gate accepted exactly as measured: final RED `c06ff106…`, baseline GREEN `a0e7793b…` =
19F/604P, repaired GREEN `b0bf23ac…` = 623/623; full tracked suite 5,856 passed with only the 15
standing untracked cadence-RED failures; Ruff/compile/diff/real-store probe clean. V22 is
CONTRACT-CLEAR, not production-clear.

I reproduced two defects after that gate:

1. CRITICAL — CORRUPT ORPHAN CONTENT OBJECT. Insert a corrupt or NULL
`semantic_evidence_objects` row under the incoming evidence SHA, without an attachment/assertion.
The writer returns `written`; the immediate loaded state is `active_evidence_unverifiable`.
The v22 check keys on evidence-id references, so the separate object-dedup edge bypasses it.

2. HIGH — CLOCK DEPENDENCY FAILURE. Clocks raising ordinary `RuntimeError`/`ValueError` leak bare
exceptions from intake, semantic assertion write, and read_model. Returned bad values are
translated; a dependency that fails to return is not.

RED v23 IS NOW FROZEN; I will not edit it during your implementation/gate:

- RED `tests/contract/test_footballguys_phase_a_red.py`
- SHA-256 `9f97d47468d8f9f8387e93ee2d58b7c6562e7adcf49dd53e6c458a4c7a3c1172`
- 7,027 lines / 270,814 bytes
- baseline GREEN `b0bf23acc3a2ecbcd2ef42ce515c52ef6a9d5e57602b19af7f56f73262cc54cb`
- strict census **632 = 8 failed + 624 passed, exit 1**
- all 623 inherited v22 controls pass; v23 is 8F/1P; Ruff/strict compile/diff check clean

Required repair boundaries:

- Before `INSERT OR IGNORE` reuses a content-addressed evidence object, verify its stored blob is
  bytes and exactly matches the incoming SHA/content. Corrupt/NULL reuse refuses
  `semantic_evidence_unverifiable:evidence-horizon-v1` with every semantic table unchanged.
  Exact-byte orphan reuse remains the positive.
- Translate ordinary clock dependency exceptions to `operation_clock_invalid` on both write
  boundaries with no governed residue. Read-model translates them to the exact literal row-9
  state with no filesystem mutation. Do not catch process-control `BaseException` classes.

Please reproduce the frozen baseline before editing, implement, and return the complete
hash-bracketed strict/full-suite/Ruff/strict-compile/diff/real-store gate. If the contract itself
is inconsistent, HOLD rather than editing either pin.

No commit, push, capture, provider contact, scheduler, or Phase B/C/D. H2 QB rushing remains
UNDER TEST and unrelated.

PLEASE REPLY with the measured baseline census and the final GREEN gate card.
