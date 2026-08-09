# CFBD FBS schedules GREEN v1 — independent behavioral review

Date: 2026-08-09  
Layer: 1 — source capture and retained provenance  
Reviewer: Codex  
Verdict: **NOT CLEAR**

## Reviewed pins and checks

- RED v5: `bbe3cd0b9278e2143d744e7365f03cb6fa0366a3f52d7720484cf2e5eed4e8ad`
- Module v1: `52d222dd3bfc3eae51b81f234aab4af5066ec137423b45aa37d39f25d3c9b797`
- CLI v1: `a03bd4ed3a76242c1a94493a27b2a6f9b6a1ac2438eacf3fdc923141478f2f47`
- Backup manifest: `22afdf528d90febd2bad7e51f5e0099fe79c96eecdfb3508396be1e82dbda396`
- Pins independently recomputed and matched.
- Focused suite: **172 passed** in 3.29s.
- Ruff across RED/module/CLI: **clean**.
- Backup manifest anti-rot + directory suites: **12 passed**.
- The one-line RED precondition repair is correct: equal-valued int/float and bool/int mutants now
  prove a value-or-exact-type change without changing behavioral expectations.

The suite is green, but the following independent probes falsified behavior outside it.

## Consolidated findings

### P0-1 — source identity accepts credential/userinfo, fragment, and foreign-port variants

`_validate_delivery` checks scheme, hostname, path, and parsed query, but not URL userinfo, fragment,
or explicit port. With otherwise exact query parameters, all three of these produced a successful
canonical capture:

- `https://user:pw@api.collegefootballdata.com/games?...`
- `https://api.collegefootballdata.com/games?...#secret`
- `https://api.collegefootballdata.com:444/games?...`

The S10 mutant combines userinfo with an extra query parameter, so the query mismatch catches it and
never proves userinfo itself is refused. A fourth probe using `:bad` raised uncaught `ValueError: Port
could not be cast to integer value`, before quarantine or failure audit, because `_sanitize_url` runs
outside the capture validation `try`.

Repair: parse and validate the final URL inside the guarded boundary; refuse any username, password,
fragment, or explicit non-default port (prefer exact no-port identity for this route); normalize malformed
ports into `source_identity_unexpected`; and add isolated mutants where every other component is exact.
Each retrieved refusal must quarantine and audit without retaining the secret text.

### P0-2 — success-audit failure leaves a published success while the CLI reports failure

The success ledger append occurs after raw, vintage, index, and marker publication and outside the
journaled `try`. An injected `OSError(28)` from `append_audit` produced:

- uncaught `OSError` (the CLI would report capture failure),
- `status_latest.json` present and `status=ok`,
- index/raw/vintage present,
- no success ledger event.

This is a split-brain terminal state. The acceptance packet treats the marker and audit as one capture;
they must commit or roll back together.

Repair: make the success audit an explicit publication boundary within the transaction, use an atomic
ledger update rather than an unprotected append that can leave a partial JSON line, and inject
route/OS/mid-write failures at that boundary. On failure, prior canonical state must be byte-identical,
no new check/vintage may remain, and one failure record should be attempted through the base recovery
path without masking the named publication error.

### P0-3 — a malformed prior marker can leave newly published orphan state

With a pre-existing malformed `status_latest.json`, the capture wrote the raw content, check, vintage,
and new index, then `json.loads` of the marker raised outside the handled exception classes. The journal
did not roll back and no failure was audited. A malformed prior `index.json` also escapes as raw
`JSONDecodeError`, though it happens before publication.

Repair: normalize corrupt index/marker reads to a stable state-integrity error, include reads whose
failure occurs after writes in the journaled rollback boundary, preserve the exact prior bytes, and audit
the failed paid check. Add populated-store mutants for malformed index and marker so the repair cannot
pass only on an empty root.

### P0-4 — local replay trusts corrupted check bytes

`replay()` parses the check object and returns its newly computed hash but never compares it with the
index entry. After a valid capture, replacing the retained check bytes with a different, fully valid 2026
FBS Game caused replay to succeed with a different SHA and game ID:

- indexed/expected SHA: `10b6862d3bcb1068967309506f9971ce66a006cf48bb77fbbe63be297b84d763`
- replayed SHA: `cb97028887c43442211658843794b0593bcd40fd437d6b97501b01e3aa64e568`
- replayed game ID: `999`

Repair: before parsing, verify check bytes against the index's full SHA and byte count, then verify the
content object and vintage agree with the same identity. Fail with `content_integrity_mismatch` and do
not mutate the store. Add corrupt-but-valid-JSON check and content replay mutants.

### P1-5 — source date validation admits truncated non-provider shapes

The committed field is OpenAPI `date-time`; the contract deliberately allows provider-naive timestamps
but intends a real kickoff datetime. `datetime.fromisoformat` also accepts `2026-09-05T19`,
`2026-09-05T19:30`, and `2026-09-05 19`, and the current guard accepts all three. Those are wider than the
measured/example provider shapes and can silently normalize absent minutes or seconds.

Repair: retain aware or provider-naive values verbatim but require a complete lexical timestamp with
date, `T`, hour, minute, and second (optional fractional seconds and optional `Z`/offset). Add truncated
hour/minute and space-separated mutants plus positive fractional/offset controls.

## Disposition

**NOT CLEAR** on the four GREEN pins. No paid provider request should occur. Return one revised RED/GREEN
packet disposing P0-1 through P1-5, including RED-before-GREEN failure evidence for the new contracts.

