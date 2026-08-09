# B21 schedules GREEN review — Codex v1

Date: 2026-08-09 ET
Layer: 1 (source acquisition and lossless retention)
Verdict: **NOT CLEAR**
RED pin reviewed: `38fceec11f9a4d623b53dee986fb59efe96fbf12429e18a2950190c9eca9cb86`
GREEN module pin reviewed: `6da5666413ee08774aaafd049ba3129516d5fa1e40a2651d86e5e306c1da49ce`

## Outcome

The cleared contract suite is GREEN, the current release Parquet parses and passes the semantic
validator, and backup coverage is present. The production route is nevertheless not runnable and
two durability properties are self-confirming rather than real. Do not perform the canonical live
capture on this GREEN.

## Consolidated findings

### F1 — P0: the production transport refuses GitHub's normal release-asset redirect

`HttpFetcher.fetch` follows redirects and returns `response.url`
(`src/dynasty_genius/sources/schedules_capture.py:119-130`). `ScheduleStore.capture` then requires
that final URL to equal the original GitHub release URL exactly. The RED's S8 likewise describes
every redirect as substitution (`tests/contract/test_b21_schedules_capture_red.py:395-405`).

That model is false for this provider. On 2026-08-09, an independent `curl -I` to the exact
sanctioned URL returned HTTP 302 with a signed HTTPS location on
`release-assets.githubusercontent.com`. Running the real CLI against a temporary root performed the
normal retrieval and exited 1 with `source_identity_unexpected`; it published no marker and wrote
only a failed-attempt ledger. Thus the exact production path cannot create the first capture even
though all 56 focused contracts pass.

The redirect contract must distinguish the provider's sanctioned GitHub release delivery chain
from a foreign substitution. Preserve the exact requested URL and redirect/final-host provenance;
allow only a measured, narrow GitHub release-assets chain; continue to refuse an arbitrary mirror.
This requires a revised RED pin as well as GREEN.

### F2 — P0: an existing content-addressed object is trusted without verifying its bytes

`FilesystemStorage.write_raw` skips the content write whenever the expected path already exists,
then links/copies that file to the check path without hashing it
(`src/dynasty_genius/sources/schedules_capture.py:188-201`). The success marker and vintage still
claim the hash computed from the newly retrieved bytes (`:687-729`, `:746-762`).

Independent counterexample: I pre-seeded `content/<sha256-of-valid-payload>.parquet` with
`b"wrong bytes"`, then recorded the valid payload. The call reported success and
`partial_artifacts()` returned empty, but `read_raw(check_id)` had SHA-256
`e2247e2d0a18ae64dddde4817edc2667df1a8edc117b95edbe27cd640cd7d64f` while both the record and
marker claimed `73816c9f3bf8e382beb043d98bad4e2968c7b80561bc314430e3a1046d5a9207`.
The retained raw was not the provider bytes and replay was no longer reproducible.

Before reusing a content path or check link, verify its byte count and full SHA-256 against the
address and incoming payload; fail closed and audit an integrity error on mismatch. Add a RED
counterexample that begins with a pre-existing wrong object and proves no false marker/check is
published.

### F3 — P0: real filesystem failures bypass rollback and failure audit

The transaction rolls back only `PublishError` (`src/dynasty_genius/sources/schedules_capture.py:
712-767`), but the production filesystem methods raise ordinary `OSError`/`PermissionError` from
directory creation, temp writes, links, copies and replace calls (`:188-231`). The contract's
`FailingAt` collaborator raises `PublishError` before the real write, so E1
(`tests/contract/test_b21_schedules_capture_red.py:982-1013`) never exercises the production
exception class or a partly completed boundary.

Independent counterexample: after one accepted vintage, a storage collaborator raised
`OSError("disk full")` at `write_index`. The exception escaped unnormalised; rollback did not run;
failed-check count remained 0; a second content object, raw check and vintage were left behind; and
`partial_artifacts()` reported the orphan raw and vintage. The CLI catches only `CaptureError`, so
this class also produces a traceback rather than the named scheduler failure it promises.

Normalize real boundary exceptions to a named publication failure, roll back everything already
journalled, clean temp files, preserve the prior marker byte-for-byte, and audit the attempt. The
RED must inject a genuine production-shaped I/O exception (including one after earlier boundaries
have written), not only the route's own expected exception.

## Independent positive evidence

- Exact RED SHA-256 recomputed: `38fceec11f9a4d623b53dee986fb59efe96fbf12429e18a2950190c9eca9cb86`.
- Focused B21 suite: **56 passed** in 4.69 seconds.
- Backup manifest suites (`backup_directory`, `backup_manifest_anti_rot`, `dgx02_backup_coverage`):
  **27 passed** in 2.34 seconds.
- Ruff on the module, CLI and RED: clean. `git diff --check`: clean.
- Full suite: **5,014 passed / 15 failed / 12 skipped / 9 xfailed** in 681.47 seconds. All 15
  failures are the separately untracked `tests/contract/test_governed_cadence_inputs_red.py`; no
  B21 test failed. This is a disclosed dirty-tree RED baseline, not a B21 regression and not a
  clean-tree result.
- Live release Parquet, downloaded only to `/private/tmp` for review: 517,546 bytes; SHA-256
  `eeea1f47644cc498676be92b5ac0fb853fd4bce238348f0436aa786c1440d5c1`; 7,548 rows × 46 columns;
  272 rows for season 2026; schema hash
  `9bbd6413bc4c498d190db8502a9b6dd7dd326c2feffa6b7208e1ef99d6b4c6a5`; validator PASS; 259 null
  `gametime` values globally and zero in 2026; zero null `gameday` values.
- No canonical capture, scheduler change, provider contact, commit or push was performed.

## Required next packet

Return one revised RED pin covering F1-F3, its true failing count/collection state, then the revised
GREEN hashes and complete gates. Behavioral CLEAR remains a prerequisite to the canonical live
capture.
