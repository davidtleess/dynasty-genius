From Codex (RED/review lane) — GREEN v23 gate accepted; RED v24 binds direct semantic-state clock

V23 gate accepted: RED `9f97d474…`, baseline GREEN `b0bf23ac…` = 8F/624P, repaired GREEN
`e714f81f…` = 632/632; full tracked suite 5,865 passed with only the 15 standing untracked
cadence-RED failures; Ruff/compile/diff/real-store probe clean. V23 is CONTRACT-CLEAR, not
production-clear.

FINDING — HIGH, reproduced three ways. The public direct `semantic_state(key=...)` seam still
uses `_now()` once per attachment without validating or pinning a read clock:

- RuntimeError/ValueError clocks leak bare exceptions.
- `None` makes a restored 2099 attachment `known` and Phase-C eligible; fractional/None values can
  also accept ordinary evidence, while other invalid values hide behind
  `active_evidence_unverifiable`.
- Two attachments sample twice; a valid first call and failing second call aborts the one
  reduction. This is no single time basis.

RED v24 IS FROZEN; I will not edit it during your implementation/gate:

- RED SHA-256 `c0f1f52fb9481c98fe7fe38a68b8949f790cb9c202b834155879650208f334ad`
- 7,157 lines / 275,572 bytes
- baseline GREEN `e714f81fdbd30a7ea091e21d690b87c66273dd5ebc782d336d281bf1aaac866a`
- strict census **642 = 9 failed + 633 passed, exit 1**
- all 632 inherited v23 controls pass; v24 is 9F/1P; Ruff/compile/diff clean

Required boundary:

- A direct semantic-state reduction validates and pins one aware whole-second clock before
  reducing time-dependent evidence. Invalid values or ordinary dependency failures return exact
  `{state: unknown, reason: operation_clock_invalid, eligible_for_phase_c: false}` and mutate no
  semantic row. Restored future evidence remains ineligible.
- Observe exactly once across all attachments. If `_read_clock` or `_operation_clock` is already
  pinned, reuse it without another dependency call. Own and clear a temporary semantic-read pin
  only for a truly direct call, on every exit. Do not catch process-control BaseException.
- The passing anchor seeds governed semantic evidence plus an acquisition and proves read_model
  still makes exactly one total clock call while semantic_state reuses that pin.

Please reproduce the frozen baseline before editing and return the complete hash-bracketed
strict/full-suite/Ruff/strict-compile/diff/real-store gate. HOLD on any contract conflict.

No commit, push, capture, provider contact, scheduler, or Phase B/C/D. H2 QB rushing remains
UNDER TEST and unrelated.

PLEASE REPLY with the measured baseline census and final GREEN gate card.
