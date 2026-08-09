# B21 schedules GREEN v3 independent review — NOT CLEAR

Date: 2026-08-09
Layer: 1 — source capture and retained provenance
Reviewer: Codex
Packet reviewed: `b21_schedules_red_v8_green_v3_claude_v1.md`

## Pins recomputed

- `tests/contract/test_b21_schedules_capture_red.py`: `22b7e72f85931cadcb049f787dbca0cc058a15e417e184c88f9de58cdf407519`
- `src/dynasty_genius/sources/schedules_capture.py`: `41c498843b26fff8d34f6b42ae2cb4b0a87c0b9370e630d93185bbf5951a86ad`
- `scripts/run_schedules_capture.py`: `9e5dcc954b0f492d5e6e2079ede29dc36466d23340c5054139d19b893e765c6b`
- `app/config/backup_manifest.json`: `31839b15391b5547dac1d57671992cd19cadfb6207d922663269fb8439c0b486`

Independent gates already run on these pins:

- B21 focused contract: `72 passed in 3.09s`
- four backup suites: `55 passed in 1.54s`
- Ruff on the three changed Python artifacts: clean
- zero pin or line-count mismatch

## Consolidated finding

### P0 — transport-failure URL userinfo still leaks to both retained audit and raised/CLI text

The v8 repair correctly routes successful and rejected-delivery URLs through `_sanitize_url()`, whose
documented rule drops URL userinfo as well as query and fragment. But the transport-exception path
does not call that sanitizer. It calls `_scrub(exc.detail)`, and `_scrub()` only replaces a query or
fragment matched after `?` or `#`. A `user:password@host` authority therefore survives intact.

Independent counterexample against the pinned module:

```text
RecordingFetcher.error =
  ConnectionError: failed https://user:pw@release-assets.githubusercontent.com/x/g.parquet
  ?sig=SECRET_SIG&jwt=SECRET_JWT#token=SECRET_TOKEN

raised:
  fetch_failed: ConnectionError: failed
  https://user:pw@release-assets.githubusercontent.com/x/g.parquet?<redacted>

marker census across raised text plus every retained file:
  user:pw       True
  SECRET_SIG    False
  SECRET_JWT    False
  SECRET_TOKEN  False

retained files:
  ledger.jsonl
```

The same leaked raised exception is printed by `scripts/run_schedules_capture.py`, so the defect has
two output surfaces: the required/offsite-backed audit store and scheduler stderr. The current S9c
and D6 marker set contains only query-string carriers (`X-Amz-Signature`, its value, `token=`, and a
JWT prefix), which explains why 72 tests pass.

This is a repair-created symmetry gap, not a speculative new policy. The v8 packet expressly names
userinfo as a third credential carrier and says it is dropped; that is true on successful URL-field
publication but false when the same carrier arrives embedded in transport error text.

Required repair/contract:

1. Add URL userinfo to S9c and D6 (or add dedicated symmetric cases) and prove the contracts fail
   against the current pinned module.
2. Sanitize every URL authority embedded in free-form failure text so userinfo cannot reach the
   ledger, the raised exception, stdout, or stderr, while retaining useful scheme/host/path context.
3. Keep the existing query/fragment redaction and non-stuttering `fetch_failed` diagnostic.
4. Report the new RED-before-GREEN failure count and the stabilized pins.

## Verdict

`NOT CLEAR` on module pin `41c498843b26fff8d34f6b42ae2cb4b0a87c0b9370e630d93185bbf5951a86ad`.

No other residual finding is being issued from this review round. The canonical live capture remains
unrun until the credential-output contract is symmetric across success, refusal, transport failure,
retained audit, and CLI output.
