# B21 schedules RED v12 — CLEAR

Date: 2026-08-09  
Reviewer: Codex, independent review lane  
Layer: Layer 1 retained source integrity and replay

## Cleared pin

- `tests/contract/test_b21_schedules_capture_red.py`
- Submitted and recomputed SHA-256:
  `d4e5287dbdafc2ef5778a34fd4718329c1a5111c146fb828cb4fdf3ae9042b4e`
- Working-tree state: tracked, modified, uncommitted.

## Independent checks

- Focused RED against shipped GREEN: `11 failed / 73 passed`, true exit 1.
- The eleven failures are exactly F0b, F0c, F0d ×6, F0f ×2 and F0e.
- Ruff: clean.
- `git diff --check`: clean.
- Full-suite collection: 5,269 tests, exit 0, zero collection errors.

## Review result

**CLEAR.** The contract now independently forces:

- named refusal for a missing retained content object;
- full SHA verification through a valid same-length, same-schema content substitution;
- stored byte-count verification through untouched content with only the metadata claim changed;
- row and column count agreement;
- minimally changed dtype-value agreement and order-only dtype-sequence agreement;
- full schema-hash agreement through a one-nibble valid-hex mutation;
- supported parser-version enforcement; and
- requested/stored/content vintage identity binding from both pointer-swap directions.

The positive controls and mutation preconditions prevent refuse-everything or collapsed-fixture
implementations from satisfying the new cases. No further RED finding was identified.

This is a contract CLEAR only. GREEN, provider data, canonical store, config, commit, push and
terminal CI remain unreviewed by this artifact.
