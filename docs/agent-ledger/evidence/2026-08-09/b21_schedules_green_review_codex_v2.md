# B21 schedules GREEN v2 review — Codex v2

Date: 2026-08-09
Layer: Layer 1 acquisition and lossless retention
Verdict: **NOT CLEAR**

## Pins reviewed

| Artifact | SHA-256 |
| :-- | :-- |
| `tests/contract/test_b21_schedules_capture_red.py` | `a1e41fa286c91b43a7dc06e20798e5f402d5124ad5b2e40732b8735a38d00ccb` |
| `src/dynasty_genius/sources/schedules_capture.py` | `5c751f371c13f09600abe1011b98d13544b80a26e4cc69b0b374b862c2e54ed2` |
| `scripts/run_schedules_capture.py` | `9e5dcc954b0f492d5e6e2079ede29dc36466d23340c5054139d19b893e765c6b` |
| `app/config/backup_manifest.json` | `31839b15391b5547dac1d57671992cd19cadfb6207d922663269fb8439c0b486` |

All three v1 findings are accepted in substance: the real GitHub redirect now succeeds, existing
content/check objects are verified, and an `OSError` raised at a boundary entrance is normalized,
rolled back, and audited. Two further P0 defects remain. Both were found by production-shaped
counterexamples not covered by the 64 GREEN contracts.

## P0-1 — a successful live capture persists signed URL credentials

`HttpFetcher` retains `response.url` verbatim (`schedules_capture.py:148-152`). A normal GitHub
release retrieval resolves to a `release-assets.githubusercontent.com` URL carrying expiring signed
query material. `capture` passes that full value to `record_offering` (`:737-739`), which writes it
verbatim into the vintage (`:798-803`), ready marker (`:821-838`), and audit ledger (`:853-859`).

Independent production-CLI smoke:

```text
root: /private/tmp/b21-cli-v2-review.<random>
exit: 0
raw_sha256: eeea1f47644cc498676be92b5ac0fb853fd4bce238348f0436aa786c1440d5c1
byte_count: 517546
schema_hash: 9bbd6413bc4c498d190db8502a9b6dd7dd326c2feffa6b7208e1ef99d6b4c6a5
requested host: github.com
final host: release-assets.githubusercontent.com
stored final URL query: contained expiring signature and JWT parameters
```

The raw capture succeeded and proves the redirect repair works. It also produced three metadata
files containing the complete signed URL. No secret values are reproduced in this review. The exact
temporary root was deleted immediately after measurement and its absence was verified.

This is not harmless provenance. Signed query values are bearer-like delivery material and must not
be committed, backed up, logged, or returned as durable metadata. The correct provenance boundary is
the sanitized final origin/path plus separately measured redirect class/host; query values and
fragments must be dropped or irreversibly redacted before constructing `OfferingRecord`. Add a RED
using realistic `sig`, `jwt`, SAS, and generic secret-like query keys and assert none survive in the
record, vintage, marker, audit, CLI output, exception details, or failed-attempt detail.

## P0-2 — the `OSError` test still fails before the filesystem boundary writes anything

E1 says it covers failures from `mkdir`, temp writes, link/copy, and `os.replace`
(`test_b21_schedules_capture_red.py:1051-1057`). It does not. `FailingAt` calls `_guard` before the
inner storage method (`schedules_capture.py:317-342`), so every injected `OSError` occurs at the
boundary entrance. The atomic writer creates `.<name>.tmp` and then calls `os.replace`
(`:197-202`), while `_Journal` tracks only the target paths (`:278-294`). A real failure after the
temp write therefore leaves an orphan the rollback does not know about.

Independent counterexample used a `FilesystemStorage` subclass whose `write_index` wrote
`.index.json.tmp` and then raised `OSError(28)`, over a pre-existing accepted vintage. Result:

```text
raised=PublishError boundary=index
marker_unchanged=True
vintages=1 successful=1 failed=1
prior_vintage_exists=True
partial_artifacts=['.index.json.tmp']
```

Normalization, marker survival, and audit now work; atomic cleanup still does not. That directly
falsifies E1's `partial_artifacts() == []` invariant for the failure shape the test claims to cover.
Add an after-temp-write/before-replace fault for each atomic boundary (and the link/copy path where
applicable), require cleanup of temp/rollback files, and ensure cleanup failure itself cannot silently
erase or mask the failed-attempt record.

## Independent positive gates

- Exact pins and line counts recomputed.
- Focused B21 suite: **64 passed** in 4.40 seconds.
- Four backup suites: **55 passed** in 2.85 seconds; with B21, the claimed clean-tree total is 119.
- Ruff on RED, module, and CLI: clean.
- Real temporary CLI capture: exit 0, correct 517,546-byte raw hash and schema hash, sanctioned
  GitHub final host, no canonical-store mutation.
- Existing-object/content-link integrity behavior inspected and the new focused contracts passed.

## Required next packet

One revised RED pin must cover both findings before GREEN repair. Then provide revised module/CLI
pins and focused/backup/Ruff gates. Do not perform the canonical capture, commit the backup-manifest
entry, install a scheduler, commit, or push until behavioral CLEAR.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
