From Codex (RED/review lane) — RED v22 FINAL FREEZE `c06ff106…`; replay baseline, then gate held repair

The contradictory inherited v9 assertion is amended without weakening its fail-closed purpose: it accepts the historical internal `event_at_invalid:*` code or the new public `operation_clock_invalid` code, while the v22 tests bind `operation_clock_invalid` exactly at the public boundary.

FINAL FROZEN RED — I will make no edits until your gate returns:

- `tests/contract/test_footballguys_phase_a_red.py`
- SHA-256 `c06ff1065a26dee8faabbb33e995a88844ea9b17c7b6a97f8ccab353736f2bd4`
- 6,885 lines / 265,254 bytes

Coherence control measured while you were HOLDING:

- held GREEN `b0bf23acc3a2ecbcd2ef42ce515c52ef6a9d5e57602b19af7f56f73262cc54cb`
- exact strict command: **623 passed, exit 0** in 25.70s
- both hashes verified immediately before the run

For attributable RED/GREEN evidence, please use this sequence:

1. Preserve the held `b0bf23ac…` patch reversibly.
2. Restore the named baseline GREEN `a0e7793b58b79e90a98371ede3ac2dd164e3504dd36b447a0244a7a0f97a832f` byte-exact.
3. Reproduce the strict census against the final frozen RED and report exact failures/passes/exit. Expected from the logically non-breaking amendment is 19F/604P, but the measurement rules.
4. Reapply the staged repair, returning to `b0bf23ac…` byte-exact if possible (otherwise disclose the new pin and delta).
5. Run the complete hash-bracketed gate: strict module, tracked full suite, Ruff, strict compile, diff check, and real-store byte-copy probe. Reverify both hashes before and after every long run.

Do not edit the RED. If any new contract issue appears, HOLD and report it rather than changing either pin mid-gate.

Scope remains unchanged: no commit, push, capture, provider contact, scheduler, or Phase B/C/D. H2 QB rushing remains UNDER TEST and unrelated.

PLEASE REPLY with the measured baseline census followed by the final GREEN gate card.
