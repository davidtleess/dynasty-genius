# CFBD retry policy — independent CLEAR

Date: 2026-08-01  
Reviewer: Codex  
Layer: 1 (source ingestion)  
Scope: `cfbd_http.py`, its two adapter call sites, and
`test_cfbd_retry_policy.py`; offline review only

## Verdict

**RETRY POLICY CLEAR.** The two challenged rows are closed. I found no remaining
classification or transition gap in the reviewed scope.

## Independent checks

1. **Exact classifier:** the implementation retries only
   `httpx.TimeoutException`, `httpx.NetworkError`,
   `httpx.RemoteProtocolError`, and HTTP statuses
   `{408, 429, 500, 502, 503, 504}`. The previously misclassified boundaries are
   corrected: 408 retries; 501, 505, `LocalProtocolError`, and
   `UnsupportedProtocol` do not.
2. **One policy, adapter-local transport:** both adapters call the shared
   `cfbd_http.with_retry` helper, but each retains its own `httpx.get` call. The
   existing adapter-local patch targets therefore remain effective and offline.
3. **G2 preserved:** exhaustion re-raises the originating failure for typed
   adapter wrapping. Retry never converts a failure into an empty response or
   no-data value.
4. **Mutation boundary:** `raw_sink` is extended only after a successful,
   list-shaped response. Exhaustion leaves it untouched; recovery records the
   provider response once.
5. **Definite-response boundary:** malformed/decode errors classify
   non-retryable. Wrong-root payload validation occurs after the retry helper
   returns, so it also costs one attempt and fails as schema, not no-data.
6. **Transition lock:** the new contract covers transient-to-success, persistent
   exhaustion at exactly three calls/two sleeps, retryable status recovery,
   definite statuses at exactly one call/zero sleeps, sink behavior, and both
   adapters.

## Reproduction

- Seven-suite CFBD slice: **158 passed, 2 skipped** in 7.05s.
- Ruff on the shared helper, both adapters, and the retry contract: **clean**.
- `git diff --check` on the reviewed files: **clean**.

The running refresh uses the pre-tightening classifier, but its observed
`ReadError` remains retryable under the accepted policy. That does not invalidate
this run. `Retry-After` handling and partial-stage preservation remain useful,
separately scoped follow-ups; neither is required to clear this bounded fix.

No live request, refresh interaction, production/test edit, CSV mutation,
promotion, or model work was performed by the reviewer.
