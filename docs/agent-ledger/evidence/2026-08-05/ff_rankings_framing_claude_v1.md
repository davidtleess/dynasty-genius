# `ff_rankings` — framing v1 (stream 6 of the six-loader batch)

**Lane:** Claude Code. **For adversarial challenge by:** Codex, per `02` §Strategy/UX framing first.
**Layer:** 1 (ingest), with a governance question that reaches `01` §Market Overlay.
**Authority:** David's sequencing word this session — *"V12 first, then ff_rankings."* That authorizes
taking the stream up. **It is not build authority, and none is sought here.** No StreamSpec, no RED,
no GREEN, no code, no capture, no store.

**This framing exists because `ff_rankings` is the one stream in the batch that is NOT a variant of
the other five.** Everything below is measured live from `nflreadpy 0.1.5` today, not inferred.

---

## 1. What it actually is

`load_ff_rankings(type=...)` returns **FantasyPros ECR** — expert consensus rankings. The provenance
is unambiguous in the payload itself: `fp_page`, `fantasypros_id`, `player_page_url` pointing at
`fantasypros.com`.

`00` §Evidence Hierarchy places **FantasyPros consensus in tier 3, "Market signal sources"** — price
discovery, explicitly *not* truth. `01` §Engine A and §Engine B **both name FantasyPros in their
disallowed feature classes, by name**. So its status is settled doctrine before we design anything:
**overlay only, never a model input.** That is not the open question. The open questions are below.

## 2. It is TWO streams, not one — measured

| | `type="draft"` | `type="week"` |
| :-- | :-- | :-- |
| rows × cols | **5,281 × 25** | **809 × 28** |
| `scrape_date` | **2026-07-31** (single) | **2025-12-30** (single) |
| axis | no season/week key → **snapshot** | no season/week key → **snapshot** |
| identity key | `id` (FantasyPros id) | `fantasypros_id` |

**Different schemas, different content, different freshness.** Twenty-five columns versus
twenty-eight, with almost no overlap in the discriminating fields. Landing these as one stream would
require exactly the heterogeneous-batch shape the contracts contract refuses. They are two
`StreamSpec`s or they are neither.

## 3. The finding that changes the disposition: `draft` carries DYNASTY rankings

`page_type` distribution on the 5,281 draft rows:

```
dynasty-op 540 · redraft-op 526 · redraft-overall 511 · dynasty-overall 502 · best-overall 355
dynasty-wr 238 · redraft-wr 226 · dynasty-rb 181 · redraft-rb 175 · dynasty-idp 174
best-wr 158 · redraft-te 149 · dynasty-te 129 · redraft-idp 124
```

**~1,760 rows are dynasty-specific consensus rankings.** That is a *second independent market
source* alongside KTC — and per the standing product thesis, the per-player **our-value vs
market-value margin** is the product. A second market lane makes that margin checkable against two
independent price sources rather than one, and makes "the market" a measurable spread rather than a
single vendor's number.

**Stated as status, not as a claim:** this is a *candidate* use of unestablished value. Whether a
two-source market lane improves anything is unvalidated, and the divergence itself remains
descriptive, not a proven edge. Nothing here licenses a decision-grade claim.

## 4. The finding that blocks the other half: `week` is redraft start/sit with verdict language

Measured on the 809 `week` rows:

- `start_sit_grade` ∈ {A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F}
- `tag` ∈ {**start**, **sit**}
- `recommendation` non-null on 17 rows
- `player_opponent`, `player_bye_week`, weekly `ecr` — **single-week redraft framing throughout**

Two doctrine problems, both hard:

1. **`00` §Descriptive Tools Issue No Verdicts.** `start`/`sit` is a normative imperative and
   `start_sit_grade` is a hand-assigned letter grade. `00` also restricts named tier labels to a
   David-ratified calibration model — an external vendor's A+/F scale is the opposite of a
   disclosed-basis calibrated position. If these columns ever reach a David-facing surface
   unfiltered, the product emits verdicts it is built not to emit.
2. **`00` §Separate Dynasty And Redraft.** Weekly start/sit serves no dynasty decision in the
   constitution's list. And `00` §Standing Non-Goals bans best-ball tooling — the `draft` payload's
   first row is literally `/nfl/rankings/best-ball-dst.php`, and `best-*` page types are ~500 rows.

**Freshness compounds it:** the `week` payload's only `scrape_date` is **2025-12-30**. In August
2026 that is last season's final week, frozen. It is not a live weekly feed today.

## 5. Identity — feasible, but the bridge does not exist

| | resolvable to canonical `gsis_id` | unresolved |
| :-- | --: | --: |
| `week` (via `fantasypros_id`) | **758 / 809 = 93.7 %** | 51 |
| `draft` (via `id`) | **4,259 / 5,281 = 80.6 %** | 1,022 |

Unresolved `week` rows by position: **DST 32 · TE 6 · LB 4 · WR 3 · DL 3 · K 2 · DB 1** — dominated
by DST/IDP/K, positions outside a Superflex PPR player-valuation universe.

The bridge is `app/data/identity/_runs/ff_playerids_20260516.json`: 7,952 rows, `gsis_id` 100 %,
`fantasypros_id` 4,652 (58.5 %), `yahoo_id` 5,356 (67.4 %).

**But `IdentityIndex.from_governed_crosswalk()` exposes only `gsis_ids` and `pfr_to_gsis` today.**
A `fantasypros → gsis` bridge would be **new identity infrastructure**, not a spec field — and
`01` §Identity Resolution requires canonical `player_id` with source IDs in one mapping layer, no
adapter inventing its own. **This is real scope and I am naming it now rather than discovering it
mid-build**, per the standing obligation about gate expansion.

## 6. The central question this framing puts — DESTINATION

The other five streams landed in `app/data/nflverse_usage.db`, which holds twelve model-feeding
training streams. `01` §Feature Store: *"Market-derived values may exist in overlay tables, but they
must be physically and semantically separated from Engine A and Engine B training features."*
`01` §Market Overlay: the overlay joins **after** model scoring and **never feeds the predictive
score.**

**So `ff_rankings` cannot land where the other five landed.** Putting a market source into the
training store and relying on a spec flag to keep it out of features is semantic separation without
physical separation — one config error from leakage, in the exact place `01` says not to put it.

I am **not** selecting the destination. Candidates, with the tradeoff:

- **(a) A separate market-overlay store** (e.g. `app/data/market_overlay.db`). Physical separation
  as `01` describes. Cost: new store, new export path, new provenance surface; a second market
  source alongside whatever KTC/FantasyCalc capture already exists needs a coherent shared shape,
  not two ad-hoc tables.
- **(b) Join the existing market-capture surface.** There is already market/divergence capture in
  this repo. Reusing it keeps one market lane. Cost: I have not audited whether its shape fits a
  snapshot ECR payload, and asserting it does without measuring would be the failure mode this
  session has been correcting all day.
- **(c) `blocked_for_use` and do not land now.** Defensible for `week` on freshness + verdict
  columns alone. Weaker for the ~1,760 dynasty `draft` rows, which are the genuinely useful part.

## 7. Proposed disposition, per the standing landing requirement

Under the closed vocabulary — and this is a proposal for challenge, not a decision:

- **`ff_rankings type=draft`, dynasty page types** → market-overlay candidate. Disposition
  `substrate_only` **if and only if** it lands in a market-separated destination; `blocked_for_use`
  otherwise.
- **`ff_rankings type=week`** → **`blocked_for_use`**. Named blockers: verdict columns
  (`tag`, `start_sit_grade`, `recommendation`) against `00` §No-Verdict Line; redraft framing against
  §Separate Dynasty And Redraft; single stale `scrape_date` 2025-12-30.
- **Verdict-shaped columns must not be stored at all**, in either stream, unless someone can state
  the decision they serve. Dropping at read time is not enough — a stored `start_sit_grade` is one
  careless surface away from being rendered.

## 8. Falsification seeds for whoever writes the RED

1. A `page_type` never seen before appears → must refuse, not bucket into "other".
2. `scrape_date` identical across two captures → is that one observation or two? (Contracts settled
   the accumulate-by-`snapshot_id` rule; ECR re-scrapes make it live again.)
3. An unresolved-identity row carrying a real ranking — the contracts exclusion premise was that
   unidentified rows hold no production; here an unresolved row holds a *rank*, which is the payload.
4. `ecr` ties, and `sd`/`best`/`worst` inconsistent with `ecr` (best > worst, sd = 0 with best ≠ worst).
5. The same player under two `fantasypros_id`s, or two players under one.
6. Dynasty and redraft rows for one player disagreeing sharply — must never be silently averaged.
7. A banned-language scan over anything derived from `tag` / `start_sit_grade` / `recommendation`.

## 9. Overclaim check against the No-Verdict Line

Nothing here proposes a David-facing surface. If one is ever built: FantasyPros ECR is **market
price discovery, not truth** (`00` §Evidence Hierarchy); any model-vs-market margin computed against
it stays **descriptive**, `decision_supported=False`, and is **not** a proven edge; and a second
market source does **not** make divergence more credible — only broader.

## 10. What I want challenged

1. Is the two-stream reading right, or is there a single-spec shape I have missed?
2. Destination — (a), (b) or (c), and does (b) survive an actual audit of the existing market surface?
3. Is `blocked_for_use` for `week` too strong? It is the disposition that stores nothing.
4. Is the `fantasypros → gsis` bridge in scope for this stream at all, or does it belong to a
   separate identity thread that must land first?
5. Is landing any of this justified before Layer 2 exists, given that six streams already have zero
   consumers and this would be the seventh?
