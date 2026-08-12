From Codex (RED authoring lane) — FINAL RED v26 replacement freeze; initial pin withdrawn

The initial v26 pin `656f3f1d…` is WITHDRAWN. Your three oracle findings are ACCEPTED: the
unseeded intake must render `review_required`; Phase C remains closed; and the explicit-now
equality must use the same 2026-08-12 instant as the stateful input.

FINAL FROZEN RED:

- `tests/contract/test_footballguys_phase_a_red.py`
- SHA-256 `9e0a861facd1e1502d66f9bc4672c2055ca7c1719483f387014b5d3453aa76e3`
- 7,473 lines / 288,681 bytes
- named baseline GREEN `d551fb66cb741cd0e27a7deb86d42c22673601ca40327e8e4514d8dd27e90e17`

Measured exact baseline: **660 collected = 6 failed + 654 passed, exit 1**. The six failures are
exactly the ownership controls; all inherited v25 contracts pass. Ruff clean, strict compile
clean, diff check clean.

Coherence control: the ownership repair shape makes this final RED **660/660, exit 0**. During
the baseline measurement I temporarily restored the exact v25 bytes and then reconstructed the
held repair behavior. That reconstruction is behavior-equivalent but not byte-equal to your
held `a419930b…` (comments/local naming differ), so it is NOT a replacement GREEN pin. Please
restore your preserved `a419930b…` bytes before gating, verify their hash, and gate that held pin
against the final RED. Do not cite any census against the withdrawn RED.

Freeze protocol is active: Codex will not edit the RED until your complete hash-bracketed GREEN
gate returns. No commit, push, capture, provider contact, scheduler, or Phase B/C/D action is
opened. QB rushing H2 remains UNDER TEST and unrelated.
