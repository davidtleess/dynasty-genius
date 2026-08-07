# A-C Steps 1-3 Fresh-Pin Recheck — Codex v2

**Date:** 2026-08-06 ET  
**Layer:** Layer 1 inventory  
**Role:** independent reviewing lane  
**Artifact reviewed:** `docs/layer-1-data-inventory-catalog.md`  
**Reviewed SHA-256:** `d92b6d0c92c1a6aba8bc6b8ddb7ccfb7e6d288b9e41d3e187620b7b8b478c758`  
**Verdict:** **NOT CLEAR**

The fresh pin and the authoring lane's F1-F7 dispositions were read in full. I reran the stated
bound/captured/exported probes, checked the physical B22/B23 artifacts, checked N14's capture-ledger
grain, inspected the current N18 markers/job/log history, and traced the live writer and consumer
paths named below. Most of the repair holds. Four residual findings remain; R1 is material.

## R1 — MATERIAL: N11 is not `static_pinned`; three live writer paths target it

The plan defines `static_pinned` as an **immutable validation/history input whose correct cadence is
no refresh**. The catalog changes N11 `fc_snapshots.db` from `manual_only` to `static_pinned` on the
basis that "nothing exports to this store at all." The repo contradicts that basis:

1. `scripts/snapshot_fantasycalc.py:26-31,91-107` performs a live FantasyCalc HTTP fetch and
   appends it to the default `app/data/fc_snapshots.db`.
2. `scripts/ingest_market_archive.py:155-174` accepts a CSV and defaults its write target to the
   same database.
3. `scripts/backfill_market_archive.py:38,91-103` also defaults its immutable backfill writes to
   the same database.

The store may be dormant and superseded in practice, but it is neither physically immutable nor
incapable of refresh. `static_pinned` therefore overstates current state. The disposition must name
the actual class using the seven-class definitions and reconcile N11 in §§4.4, 6C, 6E, and 6F. If
the desired state is truly `static_pinned`, physical write immunity is a future pass condition, not
an already-measured fact.

## R2 — Canonical reconciliation is incomplete: N12/N13 still say `manual_only`

The repaired canonical rows classify N12-N14b as `automatic_candidate`, correctly distinguishing
"a human happened to run it" from "the access path requires a human." But the live canonical prose
at catalog line 283 still says:

> **N12/N13 stay `manual_only` and consumerless.**

That contradicts §§4.4, 6C, and 6E in the same document. Preserve the consumerless fact and replace
the stale automation-class assertion. This is the same correction-without-whole-document-
reconciliation defect the catalog itself records.

## R3 — N19's source-publish clock is still unmeasured, not `n/a`

Section 6E records N19's **SOURCE-publish** field as `n/a — a one-time 2023–2026 exact endpoint
replay`. The one-time replay is a local capture event, not an upstream change rhythm. N19 contains
Sleeper transactions, matchups, league, users, rosters, traded picks, and draft endpoint families;
those source objects can change independently of the July 19 research pull.

The plan's row contract requires a measured upstream cadence or `UNVERIFIED`. Until that is measured,
step 3 has at least two open source-clock groups: N1-N8 PlayerProfiler **and N19**, not only
PlayerProfiler. This finding does not invent a recurring local job or recurring use; it keeps the
source clock distinct from the one-time local capture history.

## R4 — B20 has no replayable source capture, but "no store of any kind" is false

The B20 captured cell says `no store of any kind`, then the adjacent consumed cell correctly says
the live read mutates the active training artifact. The latter is directly evidenced:

- `scripts/build_w2_features.py:520-524` calls `nflreadpy.load_combine`;
- lines 597-605 merge combine-derived values into each row; and
- lines 637-647 rewrite `V3_CSV` with those derived fields.

The defensible captured state is: **no exact/raw/canonical Combine source capture or replay store;
derived Combine values are persisted in the active training artifact**. That preserves the R7
distinction without making a literally false physical-storage claim.

## R5 — Reporting correction: the stated diff counts do not match the fresh tree

At the reviewed pin, `git diff --numstat -- docs/layer-1-data-inventory-catalog.md` reports
**222 insertions / 64 deletions**, while `git diff --stat` reports `286` total changed lines. The
handoff and ledger state `+286/-78`. This is not a content blocker by itself, but the repo-state
claim must be corrected rather than carried into the next handoff.

## Independently checked and not challenged

- Fresh catalog hash matches `d92b6d0c...`; `git diff --check` is clean and governance validation
  passes.
- N18 supports `automatic_active_verified`: current `ok` marker, ready marker, loaded job, empty
  error log, and consecutive successful run history. Its absent raw replay remains a separate
  quality defect rather than an operational-health class.
- B15-B19's current routes are active/health-unverified, with the desired canonical routes recorded
  separately as candidates.
- Roster Auditor is both a consumer edge and an acquisition defect: it reaches live Sleeper HTTP
  through `app.data.sleeper._get`.
- N19's uniqueness claim is correctly narrowed to exact historical endpoint representation, not
  data held nowhere else.
- N14 has four capture-ledger rows and is not additive to transaction observations.
- B20-B24 are absent from the 13 bound specs, the canonical nflverse store tables, and the 12-file
  ready export. B22's 257-row frozen draft-picks pin and B23's 12,457-row frozen identity pin plus
  7,952-entry governed run were independently reproduced.
- N16/N17's wording now correctly distinguishes callable builder/evaluator consumption from
  unproved production-model consumption.
- No §1 checkbox moved. This review authorizes no code, capture, scheduler, consumer migration,
  commit, push, or Layer 2 work.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
