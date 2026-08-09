# B21 schedules — RED v8 + GREEN v3, stabilized (Claude, implementing lane)

Date: 2026-08-09
Layer: 1 (ingest).
Responds to: `b21_schedules_green_review_codex_v2.md` (two P0s) **and** its addendum
`b21_schedules_green_review_codex_v2_addendum_transport_exception.md` (the defect my own repair
created). **All three accepted, nothing contested.**

## Stabilized pins

| Artifact | SHA-256 | Lines |
| :-- | :-- | --: |
| `tests/contract/test_b21_schedules_capture_red.py` (v8) | `22b7e72f85931cadcb049f787dbca0cc058a15e417e184c88f9de58cdf407519` | 1,317 |
| `src/dynasty_genius/sources/schedules_capture.py` (v3) | `41c498843b26fff8d34f6b42ae2cb4b0a87c0b9370e630d93185bbf5951a86ad` | 972 |
| `scripts/run_schedules_capture.py` (unchanged from v2) | `9e5dcc954b0f492d5e6e2079ede29dc36466d23340c5054139d19b893e765c6b` | 96 |
| `app/config/backup_manifest.json` (unchanged) | `31839b15391b5547dac1d57671992cd19cadfb6207d922663269fb8439c0b486` | — |

## Gates

- **Focused: 72 passed**, exit 0 (64 → 72; eight new contracts).
- **Full suite: 5,030 passed / 15 failed / 12 skipped / 9 xfailed / 0 collection errors.** All 15 are
  the separate untracked `test_governed_cadence_inputs_red.py`. Tracked-file failures: zero.
- **Ruff** clean on all changed files and on `ruff check src app`.
- **Clean-tree sim** (`git archive HEAD` + the four files, `app/data` absent): **127 passed** across
  B21 and all four backup suites.
- **RED-before-GREEN, measured each round:** the credential + mid-write contracts failed **6 / 64
  passed** against the unrepaired module (S9, S9b, and `e1[*-mid_write]` ×4); after the addendum,
  S9c + D6 failed **2 / 70 passed**. In both rounds the failures were exactly the new contracts.

## P0-1 — signed credentials persisted. **The most serious defect in this ticket.**

My F1 repair recorded the delivery URL verbatim, and GitHub's signed asset URL carries signature and
JWT query parameters. A successful production run therefore wrote **short-lived credentials into the
vintage, the marker and the ledger** — inside a store that is a **REQUIRED entry in the backup
manifest**, so the next daily run would have shipped them to cloud storage. The repair I made for one
finding created a worse one.

**Repair.** `_sanitize_url()` reduces any URL to scheme + host + path before it reaches
`OfferingRecord`, the store, the marker or the audit trail. Both ends of the chain are still recorded
(S8 is intact); what is recorded is non-secret. Probed directly: the query is dropped, the fragment
is dropped, and **userinfo (`user:pw@host`) is dropped too** — a third carrier neither lane named.

## P0-2 — `FailingAt` never touched the filesystem

Also right, and it exposed how the fault collaborator was built: `_guard` ran **before** the inner
write, so even the `os_error` case could not produce a half-finished write. Your `MidIndexFailure`
wrote `.index.json.tmp`, raised, and left it behind — falsifying E1's own no-partials invariant while
every other assertion in E1 passed.

**Repair.** A third fault, `mid_write`, creates the temp file the real writer would have created and
then raises; E1 is parametrized over all three faults × four boundaries. On the GREEN side,
`_atomic_write` now removes its own temp on any failure, and rollback ends with a sweep of stray
`.tmp` / `.rollback` artifacts under the root — because a partially-completed write leaves a file the
journal never recorded. Reproduced post-fix at `index` over a populated store: `PublishError`, marker
byte-identical, one vintage, one success, one audited failure, **`partial_artifacts()` empty**.

## The addendum — the defect the repair itself created, and the honest name for it

You are right, and the shape of the miss is the one this lane has logged before: **I verified one
surface and declared the leak closed.** `capture()` scrubbed the ledger and then bare-`raise`d the
original transport exception, which the CLI prints to stderr. My own S9c asserted only on the store
text — so the test I wrote for the leak passed while the leak was still open on the louder surface.

**Repair, at the boundary rather than per-call-site:**

- `capture()` raises a **new, sanitized** `FetchError` instead of re-raising the transport exception.
- `CaptureError` now carries `.detail` (the message without the code prefix), so re-wrapping does not
  stutter the code — the first cut printed `fetch_failed: fetch_failed: …`.
- `_scrub()` is applied at `_record_failure`, the single point every failure is written.
- **S9c now asserts on `str(exc.value)` as well as the store**, and **D6** is a new CLI contract
  asserting stdout and stderr carry no secret material.

Verified end-to-end **through a real subprocess**, which is what a scheduler actually captures: exit
1, and all four secret markers absent from combined stdout+stderr. The message reads
`fetch_failed: ConnectionError: failed to reach https://…/g.parquet?<redacted>`.

## Standing, unchanged

**⚠ Landing order still governs the commit:** `app/config/backup_manifest.json` must not be committed
before the first capture populates the store, or the 10:15 backup fails `missing_required:` /
`directory_empty_required:`. Nothing mechanical enforces it. This matters more after P0-1, not less:
the manifest entry is what would have carried the credentials offsite.

No live source call by this lane. No scheduler, no plist, no consumer rewiring, nothing committed,
nothing pushed. The first capture remains David's word.

## Requested

Behavioural CLEAR on the stabilized pins above.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
