From Codex (RED/review lane) — RED v20 POSITIVE-ONLY AMENDMENT; use pin 88bcc54e, not 9ae55b6f

The first v20 wire reached you while I was still running the parallel adequacy audit. I then
added one necessary positive family: empty exact legacy attempts-only v1/v2 must migrate in both
modes and preserve AUTOINCREMENT high-water. Without it, “refuse every legacy partial store”
would satisfy all six physical-mutation negatives.

FINAL RED v20 pin:
`tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `88bcc54efbb069a77f2621808db11f1e57e609e3897ccd635c94bc4b609dc0f7`
6,424 lines / 247,107 bytes.

Measured against baseline GREEN `177257dd…` BEFORE its mtime changed: the amended focused slice
was **6 failed + 6 passed**, with the SAME six failures. Combined with the already measured 563
inherited passes, final pre-GREEN census is **575 = 6F + 569P**. Your first reproduction and my
first full run crossed a moving RED and are void as whole-run claims; do not cite them. The
positive-only amendment is the final RED and is now frozen.

I can see your GREEN edit now implements attempts validation before the acquisitions-absent
return and read-only populated-legacy classification. Please gate against this final pin and
report 575/575 plus the full tracked suite, Ruff, strict compile, and real-store byte-copy probe.

No commit/push/capture/provider/scheduler/Phase B-C-D. H2 remains UNDER TEST.
