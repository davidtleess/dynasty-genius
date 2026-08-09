# B21 — post-push divergence audit (Claude, independent reviewer for this commit)

Date: 2026-08-09
Commit audited: **`5e077cfb3832b00f2de9b64445330b67a950a361`** — "feat(data): land nflverse schedules
capture", authored 07:52:54 -0400, **pushed** (`git rev-list --count origin/main..HEAD` = 0).

`02` §Closing the loop requires the **independent** reviewer to audit the actual commit diff. I did
not author this commit, so that reviewer is me (§Falsification #4: for Codex-authored implementation
the reviewer is Claude).

## Verdict: **CLEAR on divergence.** Two findings, neither blocking, one worth acting on.

## What I verified

**Byte-identical to the CLEARed pins** — recomputed from the committed blobs, not from the worktree:

| File | Committed blob SHA-256 | Matches CLEAR |
| :-- | :-- | :-- |
| `tests/contract/test_b21_schedules_capture_red.py` | `4d924d6ce9bace5d5e4816c46eca43ac69385284efe9743807bbcf755439f79a` | ✅ |
| `src/dynasty_genius/sources/schedules_capture.py` | `2f5425f3264bc09ec36ae197ae61d0a1b05941be54353c3cfae832d0c7a5c10f` | ✅ |
| `scripts/run_schedules_capture.py` | `9e5dcc954b0f492d5e6e2079ede29dc36466d23340c5054139d19b893e765c6b` | ✅ |

**Exclusions honoured.** The commit's full file list is 10 paths plus docs. The **frozen wire pair is
untouched** — `scripts/dg_delivery.py` still `b3247ec8…` and
`tests/contract/test_wire_health_profile_refresh_red.py` still `fd924eb1…`, both still uncommitted.
No loose plists, no cadence RED, no unrelated evidence.

**CI: SUCCESS on the exact pushed SHA** `5e077cfb3832b00f2de9b64445330b67a950a361`
(run created 2026-08-09T11:53:17Z).

**Landing order satisfied — the hazard I raised did not fire.** `app/config/backup_manifest.json`
and a **populated** store landed in the same commit, so the required entry never pointed at an absent
or empty directory. The 10:15 backup is safe.

**Credential hygiene holds against the REAL provider.** The committed `ready.json` and
`ledger.jsonl` both carry
`delivered_from: https://release-assets.githubusercontent.com/github-production-release-asset/452908115/20471cd8-193e-41a5-aac5-06b3ab16148a`
— scheme, host and path only. **No signed query, no userinfo, no token material anywhere in the
committed provenance.** The sanitizer worked on a live response, which is the first time that has
been proven outside a fixture.

**Capture figures reconcile** with both Codex's independent temp-store run and Gemini's report:
raw `eeea1f47644cc498676be92b5ac0fb853fd4bce238348f0436aa786c1440d5c1`, 517,546 bytes, vintage
`v-eeea1f47644cc498`.

## Finding 1 (act on this) — the parsed vintage is 9.1 MB of permanent git history, and it repeats

`vintages/v-eeea1f47644cc498.json` is **362,503 lines / 9.1 MB uncompressed (~0.84 MB packed)**. It is
a **parsed duplicate** of the raw Parquet, which is committed alongside it at 505 KB.

The route is **revision-bearing by design** — that is why it exists — and the provider's measured
off-season cadence is a median of **7 days**. So every future capture that finds a change adds another
~0.84 MB of permanent history: **≈44 MB/year at weekly cadence**, for content already fully
recoverable from the committed Parquet plus `parse()`.

This is not a defect in the code — the store was designed to retain vintages, and it does. It is a
question about **which vintages belong in git versus in the gitignored store plus the backup**. It is
also the same class as the open snapshot-retention decision already on David's list (~17.7M rows/year
for `contracts`), and it is cheapest to settle now: unwinding committed history later means a rewrite.

**Not opened, only recorded.** Options exist (commit raw + manifest only and leave parsed vintages to
the backup-covered store; or keep the current shape deliberately) and the choice is David's.

## Finding 2 (informational) — a claim of mine to correct

I previously reasoned that `app/data/` was gitignored. **It is not**, and committing files there is
**not** a precedent change: 136 `app/data` paths were already tracked at `12c6f0d`, 142 at `HEAD`.
My clean-tree simulation saw `app/data/sources` absent because nothing under it was tracked yet, not
because a rule excluded it. Recording the correction because I stated it as fact in an earlier packet.

## On Gemini's telemetry report — one claim right, two wrong

Checked against the repo rather than accepted:

- ✅ **The capture is real and its figures are correct** (7,548 rows, 272 for 2026, vintage
  `v-eeea1f47644cc498`, 0 failures). Credit where due — this was the load-bearing claim.
- ❌ **"10 committed in git (… 2 new plists tracked in repo)."** Measured: **8 tracked**, 10 files on
  disk, and the two named plists are **UNTRACKED**. This is the *same error the board already
  corrected once* on 2026-08-08, repeated verbatim.
- ❌ **"full test suite at 4,958 passed / 0 failed (commit 268def2)."** Stale by two commits. Measured
  this session at the current tree: **5,030 passed / 15 failed / 0 collection errors**, all 15 in the
  separate untracked `test_governed_cadence_inputs_red.py`.

Its §3 "Guidance" recommends build work (wiring B21 into the cadence engine; extending the inbox
pattern to three sources). That is action-bearing rather than fact-bearing and sits outside the
ratified Operations & Telemetry seat, so it is **input, not direction** — noted without prejudice,
since David reportedly asked for its opinion.

## Standing

Not done, and each still a separate word: scheduler installation, any consumer rewiring (the Realized
Outcome job still infers `"final"` from a populated score), and the catalog update from measured
evidence.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
