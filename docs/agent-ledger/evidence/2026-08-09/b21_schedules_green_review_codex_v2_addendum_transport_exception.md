# B21 GREEN v2 review addendum — transport exception still leaks credentials

Date: 2026-08-09
Layer: Layer 1 acquisition
Status: **REPAIR-CREATED DEFECT; INCLUDE IN THE SAME V8 PACKET**

Claude correctly added S9c after recognizing that a transport failure message can embed a signed
URL. The current repair scrubs the failure record at `_record_failure`, but `capture` re-raises the
original `FetchError`. S9c asserts only the stored ledger and never inspects `str(exc)` or the CLI's
stderr.

Independent counterexample against module pin
`6060b13d23f19e192296bb1ff7888c062b69657baada66ba3379e2048c31d4a8`:

```text
fetch_failed: ConnectionError: failed to reach
https://release-assets.githubusercontent.com/0/games.parquet?<signed query present>
```

No actual credential value is reproduced here. The synthetic markers were visible in
`str(FetchError)`. `scripts/run_schedules_capture.py` catches that class through `CaptureError` and
prints the exception, so the same material reaches scheduler logs/stderr even though the JSONL audit
is clean.

Required repair and RED:

- S9c must include `str(exc.value)` in its leak assertions.
- A real CLI test must inject the same transport error and assert none of the secret markers reach
  stdout, stderr, or stored files.
- `capture` must raise a sanitized route exception (preserving the original only as an in-memory
  cause if safe) rather than re-raising the unsanitized transport exception.

This is not a new review round over an unchanged repair; it is a genuinely new defect introduced by
the current S9c repair boundary and is therefore included before the v8 pin stabilizes.
