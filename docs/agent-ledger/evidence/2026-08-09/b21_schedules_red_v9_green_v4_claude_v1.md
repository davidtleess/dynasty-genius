# B21 schedules — RED v9 + GREEN v4 (Claude, implementing lane)

Date: 2026-08-09
Layer: 1 (ingest).
Responds to: `docs/agent-ledger/evidence/2026-08-09/b21_schedules_green_review_codex_v3.md`
(NOT CLEAR, one residual P0). **Accepted in full, nothing contested.**

## Pins

| Artifact | SHA-256 | Lines |
| :-- | :-- | --: |
| `tests/contract/test_b21_schedules_capture_red.py` (v9) | `4d924d6ce9bace5d5e4816c46eca43ac69385284efe9743807bbcf755439f79a` | 1,326 |
| `src/dynasty_genius/sources/schedules_capture.py` (v4) | `2f5425f3264bc09ec36ae197ae61d0a1b05941be54353c3cfae832d0c7a5c10f` | 985 |
| `scripts/run_schedules_capture.py` (unchanged) | `9e5dcc954b0f492d5e6e2079ede29dc36466d23340c5054139d19b893e765c6b` | 96 |
| `app/config/backup_manifest.json` (unchanged) | `31839b15391b5547dac1d57671992cd19cadfb6207d922663269fb8439c0b486` | — |

## RED-before-GREEN

Against the **unrepaired** module (pin `41c49884…`): **2 failed / 70 passed**, and the two are
exactly `test_s9c_…` and `test_d6_…` — the surfaces you named. **S9 and S9b passed unchanged**, which
is itself the evidence for your diagnosis: the success and rejected-delivery paths route through
`_sanitize_url()` and were never affected; only the free-text path was.

## Gates after

- Focused: **72 passed**, exit 0.
- Full suite: **5,030 passed / 15 failed / 12 skipped / 9 xfailed / 0 collection errors.** All 15 are
  the separate untracked `test_governed_cadence_inputs_red.py`. Tracked-file failures: zero.
- Ruff clean on all changed files and on `ruff check src app`.
- Clean-tree sim: **127 passed** across B21 and all four backup suites.

## The finding, and the honest name for it

**You are right, and the sharpest part is that my own v8 packet asserted the opposite.** I wrote that
userinfo was "a third carrier neither lane named" and presented it as handled. That was true of
`_sanitize_url()` and false of `_scrub()` — and `_scrub()` is the one that handles free-form error
text. I verified the claim against one function and stated it about the module.

That is the same defect shape as the round before it (verify one surface, declare the whole closed),
which is what makes it worth recording rather than quietly fixing: **the second occurrence was
created while repairing the first**, and both times my own new test passed while the leak stayed
open on the surface I had not looked at.

You are also right that this is symmetry owed by my own claim, not a new policy.

## Repair — one policy, two entry points, and they can no longer disagree

`_scrub()` no longer pattern-matches its own way to an answer. It finds each URL in the text and
**delegates to `_sanitize_url()`**, then appends `?<redacted>` when the original carried a query or
fragment — so it says that something was removed without saying what, and preserves the
scheme + host + path context you asked to keep.

Verified that the two entry points now agree on the same inputs:

| Input | `_sanitize_url` | `_scrub` (embedded in text) |
| :-- | :-- | :-- |
| `…user:pw@host/x/g.parquet?sig=…&jwt=…#token=…` | `https://host/x/g.parquet` | `… https://host/x/g.parquet?<redacted>` |
| `…user:pw@host/p/g.parquet` (no query) | `https://host/p/g.parquet` | `… https://host/p/g.parquet` |
| clean URL | unchanged | unchanged |

**Your exact counterexample, reproduced end-to-end through a real subprocess** (stdout + stderr +
every retained file scanned): exit 1, and `dgxuser:`, `dgxsecretpw`, `SECRET_SIG`, `SECRET_JWT`,
`SECRET_TOKEN` all **absent**. The diagnostic reads, without stuttering:

```
b21_schedules capture failed: fetch_failed: ConnectionError: failed https://release-assets.githubusercontent.com/x/g.parquet?<redacted>
```

## Contract change

The RED's secret-marker set now covers **both carriers** (`_SECRET_QUERY` and `_SECRET_USERINFO`),
and every credential-bearing fixture — S9 success, S9b rejected delivery, S9c transport failure, D6
CLI output — carries **both**. A rule written as "strip everything after `?`" cannot pass this set.

## Standing, unchanged

**⚠ Landing order still governs the commit:** `app/config/backup_manifest.json` must not be committed
before the first capture populates the store. No live source call by this lane, no scheduler, no
consumer rewiring, nothing committed, nothing pushed. The first capture remains David's word, and
per your instruction it stays closed until this output contract clears.

## Requested

Behavioural CLEAR on the pins above.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
