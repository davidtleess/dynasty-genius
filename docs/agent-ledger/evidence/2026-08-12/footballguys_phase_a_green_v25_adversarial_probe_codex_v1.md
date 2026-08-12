# Footballguys Phase A GREEN v25 adversarial probe — Codex v1

Date: 2026-08-12  
Layer: 1 — source intake and governed persistence  
Reviewed GREEN SHA-256: `d551fb66cb741cd0e27a7deb86d42c22673601ca40327e8e4514d8dd27e90e17`  
Reviewed RED v25 SHA-256: `08ad86b2e866865104fb6bb1b5382788bcba66223392dce3e081b181a2e0b4fa`

## Verdict

NOT CLEAR. The repair translates the first validation-method failure but retains the
caller-owned datetime object for later use.

## Finding C1 — validation does not establish ownership of the pinned instant

The repaired `_observe_operation_clock` invokes `isoformat()` inside the translation boundary,
validates the result, and then returns the original datetime subclass. Downstream write steps
invoke methods on that same caller-owned object after governed mutation.

Measured with a stateful subclass:

- if `isoformat()` succeeds once and raises on call 2, intake leaks `RuntimeError` after creating
  `receipts.db` and `semantics.db`;
- if it succeeds twice and raises on call 3, intake leaks after publishing the canonical paid
  ZIP, with no receipt; database/WAL residue also exists.

Two sibling probes demonstrate the same ownership defect outside repeated `isoformat()`:

- a subclass comparison override leaks from semantic write, direct semantic reduction, and the
  read-model clock pin;
- an `astimezone()` override on the explicit `read_model(now=...)` value leaks later from the
  calendar-state evaluator.

## Required boundary

The validation boundary must produce a base `datetime` owned by the implementation (or an
equivalent immutable canonical representation). All downstream comparisons, serialization,
calendar conversion, event allocation, and semantic reduction must use that owned value. One
valid dependency observation must be sufficient for the complete operation.

No commit, push, capture, provider contact, scheduler, or Phase B/C/D is opened. QB rushing H2
remains UNDER TEST with no result and is unrelated.
