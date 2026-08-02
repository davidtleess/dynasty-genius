# Codex review — CFBD bounded retry policy

**Date:** 2026-08-01  
**Reviewer:** Codex  
**Scope:** working-tree retry diff; offline only  
**Verdict:** **CHALLENGE — bounded retry preserves G2 in principle, but the policy is untested and
the implemented classifier is not “transient only.” The active ReadError relaunch may continue.**

## What is sound

- Retrying an idempotent GET after a connection reset does not turn failure into no-data.
- Both adapters still raise typed errors after exhaustion.
- JSON decode and non-list payload failures are not retried.
- The receiving adapter mutates `raw_sink` only after a successful list response; the QB adapter
  returns raw payloads only after its fetch set completes.
- Three attempts with bounded backoff is proportionate for the actual `httpx.ReadError` that aborted
  the first run.
- The first run's discarded partial raw tree should remain a separate wrapper-contract question;
  do not change teardown/reuse semantics during this refresh.

## Finding 1 — no retry transition is locked by a test

The current G2 tests exercise persistent failure, but they do not assert call count, retry class,
backoff, recovery, or non-retry behavior. They pass after sleeping through the new attempts. No test
currently proves any of these required rows in either adapter:

- transient `ReadError` then success → exactly two calls, one backoff, returned data preserved;
- persistent transient failure → exactly three calls, then the existing typed error;
- HTTP 429 / retryable 5xx → retry;
- definite 4xx / malformed JSON / wrong root type → one call, no retry;
- `raw_sink` remains untouched on exhaustion and is populated once after recovery.

This is the same vacuity class just closed for `sack_rate`: green tests do not yet distinguish a
working retry loop from an incorrectly classified or unbounded one. Monkeypatch `time.sleep` so the
failure rows do not add real backoff to the suite.

## Finding 2 — the classifier disagrees with “transient only”

An offline classification probe against the actual helper returned:

```text
HTTP: 408=False, 429=True, 500=True, 501=True, 502=True, 503=True, 504=True, 505=True
Transport: ReadError=True, ConnectError=True, UnsupportedProtocol=True,
           LocalProtocolError=True, RemoteProtocolError=True
```

`501 Not Implemented`, `505 HTTP Version Not Supported`, `UnsupportedProtocol`, and
`LocalProtocolError` are deterministic/configuration failures, not transient blips. Conversely,
`408 Request Timeout` is the explicit HTTP timeout status but is currently non-retryable. A narrower
idempotent-GET policy is:

- retry `httpx.TimeoutException`, `httpx.NetworkError`, and `httpx.RemoteProtocolError`;
- retry statuses `{408, 429, 500, 502, 503, 504}`;
- do not retry other 4xx/5xx or local/unsupported-protocol failures.

429 is retryable, not rejected. If a numeric `Retry-After` is present, honoring it under a declared
cap is preferable to blindly sleeping 0.4/0.8 seconds; this is secondary to making the classification
and tests explicit.

## Boundary and current run

The active relaunch is responding to `ReadError`, which lies inside both the current and proposed
retry sets, so this review does not request an abort. It is a pre-commit/post-edit gate on the general
policy. No paid call, process interaction, code/test edit, refresh mutation, CSV change, promotion,
or model work was performed by Codex.
