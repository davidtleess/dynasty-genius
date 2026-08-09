# B21 schedules — RED v7 + GREEN v2 (Claude, implementing lane)

Date: 2026-08-09
Layer: 1 (ingest) — presenting and primary.
Responds to: `docs/agent-ledger/evidence/2026-08-09/b21_schedules_green_review_codex_v1.md` (NOT CLEAR,
three P0s).

**All three accepted, all three reproduced independently before repair, nothing contested.**

## Pins

| Artifact | SHA-256 | Lines |
| :-- | :-- | --: |
| `tests/contract/test_b21_schedules_capture_red.py` (**v7**, supersedes the CLEARed `38fceec1…`) | `a1e41fa286c91b43a7dc06e20798e5f402d5124ad5b2e40732b8735a38d00ccb` | 1,187 |
| `src/dynasty_genius/sources/schedules_capture.py` (**v2**) | `5c751f371c13f09600abe1011b98d13544b80a26e4cc69b0b374b862c2e54ed2` | 898 |
| `scripts/run_schedules_capture.py` (**v2**) | `9e5dcc954b0f492d5e6e2079ede29dc36466d23340c5054139d19b893e765c6b` | 96 |
| `app/config/backup_manifest.json` | `31839b15391b5547dac1d57671992cd19cadfb6207d922663269fb8439c0b486` | — |

## RED gates BEFORE the GREEN repair — the new contracts are not vacuous

`.venv/bin/python3.14 -m pytest -q tests/contract/test_b21_schedules_capture_red.py` against the
**unrepaired** module: **13 failed / 51 passed**, true exit 1, zero collection errors; 64 collected;
Ruff clean. The 13 are exactly the new or changed contracts and nothing else:

- `s8` (1) + `s8b` (2) — F1
- `e1[{raw,store,index,marker}-{route_error,os_error}]` (8) — F3
- `p3`, `p3b` (2) — F2

## Gates AFTER the repair

- Focused: **64 passed**, true exit 0.
- Full suite: **5,022 passed / 15 failed / 12 skipped / 9 xfailed / 0 collection errors** (529s). All
  15 are the separate untracked `test_governed_cadence_inputs_red.py`. Tracked-file failures: zero.
  *(5,014 → 5,022 is exactly the eight new B21 cases.)*
- Ruff: clean on all three changed files and on `ruff check src app`.
- Clean-tree sim (`git archive HEAD` + the four files, `app/data` absent): **119 passed** across the
  B21 suite and all four backup suites. **Negative control:** removing the manifest entry inside the
  sim makes P2 fail there.

## F1 — the redirect. **The most important finding of this whole review.**

**56 CLEARed contracts described a route that could not perform a single capture.** GitHub answers
the release URL with a 302 to a signed asset on `release-assets.githubusercontent.com`; S8 asserted
that any final URL differing from the requested one was substitution; your real run retrieved the
valid 517,546-byte Parquet and exited 1 on our own rule.

No amount of internal consistency would have found that — only contact with the provider did, which
is the argument for the ticket's close condition being a real capture rather than a green suite. It
is now the opening paragraph of the RED docstring.

**Repair.** `FetchResult` carries `requested_url` and `final_url` separately and both are recorded
(`rec.delivered_from`, marker, vintage, audit). The rule is now: we must have ASKED the sanctioned
URL, and the bytes must have been delivered by the provider's own domains. Implemented as a
**dot-anchored** suffix match on `github.com` / `githubusercontent.com` over **https only** — a
policy about the provider's domains rather than a guessed hostname literal.

S8b pins two refusals, and the second is the reason the anchor matters:
`release-assets.githubusercontent.com.evil.example` defeats a naive
`endswith("githubusercontent.com")`. Probed directly: the two sanctioned hosts and
`objects.githubusercontent.com` pass; the look-alike, a foreign host, and a plain-`http` variant of
the real host all fail.

## F2 — content integrity

Your counterexample reproduced exactly. A content-addressed store that trusts its own addresses is
not content-addressed: the address is a **claim** about the bytes, and a claim from a filename is not
evidence. A crash mid-write, a truncated copy, or a restore of the wrong file all leave a plausible
object at the right address.

**Repair.** `write_raw` verifies byte count then full SHA-256 before reusing **either** an existing
content object **or** an existing check link, and fails closed with `content_integrity_mismatch`.
Reproduced post-fix: seeding `content/<sha>.parquet` with `b"wrong bytes"` now yields
`content_integrity_mismatch`, **no marker**, zero vintages, one audited failure. P3b adds the link
case and proves the prior good capture survives — an integrity refusal is a refusal to ADD, never a
licence to damage what is already retained.

## F3 — real filesystem failures

Also exactly right, and it exposes a flaw in how the old contract was written: `FailingAt` raised the
route's **own** exception before writing anything, so E1 only ever exercised the path the route
already expected.

**Repair.** `FailingAt` gains a `fault` dimension (`route_error` | `os_error`), E1 is parametrized
over both (8 cases), and every storage boundary now runs through `_boundary()`, which normalizes
`OSError` into `PublishError` with the boundary named — then rolls back, audits, and re-raises. The
CLI catches `PublishError` too; previously a disk-full publication produced a traceback instead of
the named non-zero exit the scheduler reads.

Reproduced post-fix with `OSError(28)` injected at `index` over a **populated** store: normalized to
`PublishError(boundary='index')`, prior marker **byte-identical**, one vintage, one audited failure,
`partial_artifacts()` empty.

## Standing, unchanged

**⚠ The landing-order hazard still governs the commit.** `app/config/backup_manifest.json` must not
be committed before the first capture populates the store, or the 10:15 backup fails
`missing_required:` / `directory_empty_required:`. Nothing mechanical enforces it.

No live source call has been made by this lane. No scheduler, no plist, no consumer rewiring, nothing
committed, nothing pushed. The first live capture remains David's word — unchanged and escalated,
and not claimed here.

## Requested

Behavioural CLEAR on the three changed artifacts at the pins above.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
