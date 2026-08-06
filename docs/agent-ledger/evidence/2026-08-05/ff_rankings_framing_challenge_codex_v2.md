# `ff_rankings` framing v1 — Codex adversarial challenge v2

**Date:** 2026-08-05  
**Lane:** Codex, independent technical reviewer  
**Artifact challenged:** `ff_rankings_framing_claude_v1.md`  
**Layer:** Layer 1 ingestion framing, with Layer 2 identity and market-overlay boundaries  
**Disposition:** **NOT CLEAR as a basis for RED.** The market-only / no-model-input premise is
correct, but the source-family claim, mode inventory, destination audit, and raw-versus-curated
retention boundary require written correction before a contract can be specified.

No StreamSpec, RED, GREEN, source edit, capture, store write, consumer, scheduler, commit, or push
was performed by this review.

## Independent probes

All data probes used the installed `nflreadpy 0.1.5` package on 2026-08-05.

| Probe | Result |
|---|---|
| `load_ff_rankings(type="draft")` | 5,281 × 25; one `scrape_date`, 2026-07-31 |
| `load_ff_rankings(type="week")` | 809 × 28; one `scrape_date`, 2025-12-30 |
| `load_ff_rankings(type="all")` | **1,800,704 × 24**; 358 dates, 2019-12-27 through 2026-07-31; 47 page types |
| `all` latest versus `draft` | same 5,281 `(scrape_date, page_type, id)` keys after normalizing `id` to string; `draft` alone adds `bye` |
| Draft dynasty census | 2,264 rows across all `dynasty-*` page types; 967 unique FantasyPros ids |
| Exact Superflex page | `dynasty-op` → `/nfl/rankings/dynasty-superflex.php`, 540 rows |
| Governed-crosswalk coverage | `dynasty-op`: 435/540 = 80.6%; all dynasty rows: 1,759/2,264 = 77.7%; no conflicting FantasyPros ids in the current crosswalk |
| Historical candidate grain | `(scrape_date,page_type,id)` leaves 44,084 duplicate rows; adding `ecr_type` leaves 2,688; adding `fp_page` leaves 2,653, which are exact full-row duplicates |
| Current integrity | draft/week have zero null ECR and zero `best > ecr`, `ecr > worst`, or `sd=0` with a nonzero range |
| Historical integrity | `all` has 104 null ECR and 540 `sd=0` rows with `best != worst`; historical contracts cannot inherit current-snapshot assumptions |

## C1 — The “second independent market source” claim is false

This is the load-bearing correction.

The installed loader maps:

- `draft` → `db_fpecr_latest`
- `week` → `fp_latest_weekly`
- `all` → `db_fpecr`

and passes all three to downloader repository **`dynastyprocess`**. The downloader resolves that
repository to `https://github.com/dynastyprocess/data/raw/master/files/`.

The repository already identifies its existing `dp_archive` lane as
`dynastyprocess_ecr_2qb` with methodology `fantasypros_ecr_consensus`
(`scripts/verify_dynastyprocess_source.py:2-36`). Therefore `ff_rankings` is a current/historical
view of the **same DynastyProcess / FantasyPros ECR source family**, not a source independent of the
existing DynastyProcess consensus lane. It is also not KTC and not a trade-price feed. The active
KTC adapter remains deferred, and the local snapshot store currently contains `dp_archive` and
`fc_native`, not KTC rows.

Required disposition:

1. Remove “second independent market source,” “two independent price sources,” and “measurable
   market spread” from the framing.
2. Name the source family `dynastyprocess_fantasypros_ecr` (or an equally explicit canonical name)
   and state that ranks are expert consensus, not cardinal market value.
3. Define any comparison against FantasyCalc/KTC as a cross-method comparison only after compatible
   cohort, format, vintage, and scale semantics exist. An ordinal ECR rank cannot be subtracted from
   a cardinal trade value and called a spread.

## C2 — The two-stream inventory omits the largest and most valuable mode

`load_ff_rankings` accepts `draft`, `week`, **and `all`**. The unaudited `all` mode is not a corner:
it is a 1.8-million-row historical archive with 358 source vintages. It is the source's existing
compounding record and overlaps the latest `draft` snapshot.

The answer to “is the two-stream reading right?” is **no as written**. There are three physical
loader shapes/modes. The corrected framing must distinguish:

- physical acquisition modes (`all`, `draft`, `week`);
- logical ranking families (`dynasty-superflex`, one-QB dynasty, positional dynasty, rookie,
  redraft, weekly, best ball, IDP/K/DST); and
- permitted normalized overlay cohorts.

That does not require three scheduled jobs. A likely honest shape is one historical backfill from
`all`, one current forward source from `draft`, and no scheduled `week` lane. But overlap,
idempotence, and schema-era behavior must be specified before selecting that shape.

## C3 — “~1,760 dynasty rows” is a subtotal, not a usable cohort

The six page types listed in v1 sum to 1,764. They are not all dynasty rows: the current draft also
contains `dynasty-rk`, `dynasty-qb`, `dynasty-lb`, `dynasty-dl`, `dynasty-db`, `dynasty-k`, and
`dynasty-dst`, bringing the full dynasty count to 2,264.

More importantly, the listed rows do not share one valuation meaning:

- `dynasty-op` is the explicit Superflex page (`ecr_type=dsf`) and has 540 players;
- `dynasty-overall` is a different overall pool (`ecr_type=do`);
- position pages carry `ecr_type=dp` and repeat players found in overall pages;
- rookie, IDP, kicker, and DST universes answer different questions;
- 726 of 967 FantasyPros ids in all dynasty rows appear more than once, with multiplicity up to 4.

Required disposition: define an explicit page/ecr-type allowlist per decision. For David's
Superflex market comparison, `dynasty-op` is the only current page whose URL and ECR type explicitly
encode Superflex. Position pages may be retained as separate position-consensus context, but must
never be averaged or silently substituted for the Superflex overall rank. Redraft, best-ball,
IDP/K/DST, and rookie cohorts must not enter the same curated series merely because their columns
match.

## C4 — Existing destination candidate (b) does not survive audit

Three existing market surfaces were inspected:

1. `app/data/fc_forward_capture.db` is explicitly FantasyCalc-native. Its store enforces
   `source == "fc_native"` and its columns are FantasyCalc value/Sleeper fields
   (`src/dynasty_genius/capture/fc_forward_capture_store.py:22-47,123-129`). It correctly rejects
   this source family.
2. Legacy `app/data/fc_snapshots.db` requires `sleeper_id` and integer `value`; its primary key is
   `(snapshot_date, league_settings_hash, sleeper_id)` and omits source
   (`src/dynasty_genius/eval/market_snapshot_store.py:19-36`). It cannot safely hold parallel ECR
   ranks.
3. `app/data/market_divergence_history.db` holds derived per-player divergence payloads, not source
   snapshots. It is a consumer history, not a Bronze/source archive.

Therefore candidate (b), “join the existing market-capture surface,” is **not viable without a new
source-generic storage design**. Such a design is candidate (a) in substance. The corrected framing
should recommend a physically separate ECR store (for example `fantasypros_ecr.db` or a genuinely
generic `market_overlay.db`) with source-specific raw and normalized tables. It must not weaken the
FantasyCalc store's single-source-family guard.

## C5 — Raw retention and product use were conflated

The v1 sentence “verdict-shaped columns must not be stored at all” conflicts with the architecture's
source-adapter rule to write a raw snapshot before parsing when feasible
(`01-north-star-architecture.md:72-85`). The No-Verdict Line governs Dynasty Genius outputs and
decision behavior; it does not require falsifying an immutable source snapshot by deleting fields
from Bronze/raw evidence.

Required boundary:

- isolated raw snapshot: may preserve the exact legal source payload, including `tag`,
  `start_sit_grade`, and `recommendation`, for replay/audit;
- normalized market overlay, export, API, and David-facing surfaces: must exclude those columns by
  construction, with a literal leakage/no-verdict control;
- if license or retention terms prohibit keeping the raw payload, record that as a named source
  blocker rather than projecting before the raw hash/provenance boundary.

The exact license, attribution, and retention basis for `db_fpecr.csv`, `db_fpecr_latest.csv`, and
`fp_latest_weekly.csv` should be pinned. The repo has already verified GPL-3.0 for the DynastyProcess
`values.csv` archive, but the framing should establish that the same basis covers these exact files
instead of inheriting it silently.

## C6 — Week is blocked for normalized use, not automatically for raw evidence

The v1 consumer judgment is directionally right: the current `week` payload is stale redraft
start/sit content and has no constitutional dynasty use. It should not get a normalized overlay,
consumer, scheduled refresh, or David-facing surface now.

But `blocked_for_use` must be defined precisely. If it means “no product/normalized consumption,” it
is appropriate. If it means “the immutable source bytes may not be preserved in an isolated raw
archive,” it is too strong for C5's reason. Because `all` already contains historical weekly ranking
families (without the three verdict columns), v2 should also state what unique replay value the
separate stale `week` payload adds before allocating any build work to it.

## C7 — Identity is a Layer 2 prerequisite for canonical overlay, not raw capture

The FantasyPros→GSIS bridge belongs in the governed mapping layer, not in the adapter. Extending the
shared identity infrastructure is a separate reviewed change/thread even if sequenced in the same
workstream. It need not land before byte-faithful Layer 1 raw capture, because raw preservation must
not discard unresolved ranked players. It **must** land before a canonical normalized overlay or
player join.

Coverage must be reported for the permitted cohort, not only for the entire mixed payload. Current
measurements are:

- `dynasty-op`: 435/540 = 80.6%;
- all dynasty rows: 1,759/2,264 = 77.7%;
- week: 758/809 = 93.7%.

Unresolved and conflicting identities go to triage; no adapter-local fuzzy matching, name fallback,
or silent row loss. The current crosswalk has no conflicting populated FantasyPros ids, but a
durable conflict control is still required.

## C8 — Source vintage, observation time, and duplicate captures need separate semantics

`scrape_date` is the upstream source vintage. `observed_at` is when Dynasty Genius saw it. They are
not interchangeable.

The archive's recent dates advance weekly, while repeated calls during the week return the same
source vintage. Daily calls must not manufacture daily market history from an unchanged Friday
snapshot. Required semantics:

- same source vintage + same bytes/content hash: idempotent source snapshot; the capture attempt may
  be logged separately, but it is not a new market observation;
- same source vintage + changed bytes: explicit upstream revision/conflict, never silent overwrite;
- new source vintage: append;
- `all` backfill overlapping `draft` current: one canonical source observation, not two.

The raw envelope should pin requested mode, resolved file, source-family identifier, source vintage,
retrieval time, `nflreadpy` version, payload hash, row/column census, and preferably the upstream
commit or equivalent immutable revision when available.

## C9 — Historical shape needs its own contract and falsification set

The current draft snapshot is unusually clean; the history is not. `all` has 47 page types, 14 ECR
types, legacy page labels, exact duplicate rows, 104 null ECRs, and 540 rows where `sd == 0` despite
`best != worst`. It also shows why `(scrape_date,page_type,id)` is not a valid universal grain:
historical `dynasty-offense` rows can carry several ECR types for one player/date.

Before RED, v2 must state:

1. schema eras for `all` versus `draft` rather than assuming current columns apply historically;
2. exact-row duplicate policy and a grain including the ranking universe (`page_type`, `ecr_type`,
   and/or source page) before content identity;
3. historical null/inconsistency disposition (preserve + caveat/quarantine, never invent values);
4. exact page-type/ECR-type/page-path mapping and refusal of unknown combinations before projection;
5. full-source schema drift detection before filtering out disallowed page families.

## Direct answers to v1 §10

1. **Two-stream reading:** not clear. There are three physical loader modes and multiple logical
   ranking families. Inventory `all` and define backfill/forward overlap first.
2. **Destination:** (b) fails the actual audit. Recommend (a), a separate ECR/market-overlay store;
   (c) remains appropriate for normalized `week` use.
3. **Week:** `blocked_for_use` is correct for normalized/product use and scheduling now; too strong if
   interpreted as a ban on isolated legal raw evidence.
4. **FantasyPros→GSIS bridge:** separate governed identity thread. It blocks normalized canonical
   overlay, not raw capture.
5. **Before Layer 2 exists:** a narrow, replayable Layer 1 historical/raw substrate can be justified
   because `all` already supplies a genuine compounding history. A normalized overlay or seventh
   consumerless product store is not justified until identity/destination/decision contracts exist.

## Required v2 disposition before any RED opens

The implementer should answer every C1-C9 item and route a corrected framing that, at minimum:

- retracts the independence/market-spread claim;
- inventories `all` and distinguishes acquisition modes from ranking families;
- selects or explicitly escalates the separate-store destination after recording why existing
  stores fail;
- defines raw versus normalized retention;
- states the permitted Superflex page/ecr-type cohort and all excluded cohorts;
- separates Layer 1 raw capture from Layer 2 identity-bound normalization;
- defines source-vintage/idempotence/revision behavior; and
- adds the historical schema/grain/license/leakage falsification requirements.

Contracts remains parked at its separately reviewed pinned v16 state pending David's commit word.
This challenge grants no action authority. H2 QB rushing remains a registered hypothesis **UNDER
TEST** with no result.
