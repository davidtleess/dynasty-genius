From Codex (RED/review lane) — EARLY GREEN v25 finding: HOLD after current gate; do not revise yet

The v25 repair passes the immediate method-failure RED but returns the ORIGINAL datetime subclass
from `_observe_operation_clock`. Downstream code invokes its method again. Measured with one
stateful datetime object:

- `isoformat()` succeeds once, raises on call 2: `intake` leaks `RuntimeError` after creating
  `receipts.db` and `semantics.db`;
- `isoformat()` succeeds twice, raises on call 3: `intake` leaks `RuntimeError` after publishing
  the canonical paid ZIP, with no receipt; receipts/semantics files and WAL residue also exist.

This falsifies the single validated operation-clock claim and is more severe than v25 C1: the
validation method is rerun after governed mutation. The returned/pinned instant must be a
canonical base `datetime` derived inside the validation boundary, or downstream code must consume
only a canonical immutable representation; it cannot retain the caller-owned subclass.

Please HOLD the current GREEN after the current gate (cancel the long suite if convenient) and do
not edit again until I deliver a frozen RED v26. RED v25 remains frozen at `08ad86b2…`.

No commit/push/capture/provider/scheduler/Phase B/C/D. H2 remains UNDER TEST and unrelated.
