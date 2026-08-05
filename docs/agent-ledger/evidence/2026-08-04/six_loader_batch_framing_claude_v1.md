# Framing — Layer-1 six-loader batch (AGENT_SYNC board block C)

**Author:** Claude Code (implementing lane) · **Date:** 2026-08-04 · **Status:** v1, awaiting Codex challenge
**Governance read:** `02` v1.5.0 · `00` v1.1.0 · `05` v1.3.1 · `01` v1.0.0 · `03` v1.1.0 · `AGENT_SYNC.md`
through `END CURRENT BOARD` · `docs/agent-ledger/2026-08-04.md`

**Layer served (05 §3 Rule 1):** **Layer 1 — ingest.** Primary and sole. The layers 1–2 dependency
check (Rule 2) applies to work at layers 3–6 and is **not applicable**: this work *is* the
foundation, not a symptom of it.

**Repo state at framing:** `HEAD == origin/main == 34da22f`, tracked tree clean, zero untracked.

---

## 1. The concrete situation this serves

David's ruling, verbatim on the board: *"1) We have a lot of powerful data...land it all --- this is
our fuel: layer 1."* and *"i want fresh agents to start their session with the ingestion - i want
them to make strong progess on layer 1"*. The metric he ratified is **usable streams landed, rows
second**; a session landing no new stream is a MISS unless it names an external blocker.

The board directs: land the six free zero-caller nflverse loaders as **one batch**, copying
`src/dynasty_genius/nflverse_usage.py` rather than inventing a mechanism, under a **reduced
per-stream gate** with **one** independent review and **one** full-suite/Ruff gate for the batch.

## 2. What I measured, and the premise it breaks

Probes are read-only, run 2026-08-04 against the live source with `nflreadpy 0.1.5`; scripts and raw
JSON are promoted alongside this document. Seasons 2023–2025 except where a stream has no season
axis.

| Stream | Rows | Cols | Unique grain proven? | Player identity | Verdict |
| :-- | --: | --: | :-- | :-- | :-- |
| `load_pfr_advstats` | 46,575 (4 types) | 16–29 | **YES — 0 dup groups** on `(season, week, team, pfr_player_id)`, all four types | `pfr_player_id`, 100% | **Drop-in** |
| `load_ftn_charting` | 143,572 | 29 | **YES — 0 dup groups** on `(nflverse_game_id, nflverse_play_id)`, zero nulls | **NONE — no player column at all** | Mechanism gap |
| `load_ff_opportunity` | 18,140 | 159 | **NO — 65 dup groups** (max 29) on `(season, week, player_id)`; **1,280 null `player_id`** | `player_id`, 93% | Design needed |
| `load_depth_charts` | 628,854 | 26 | **NO — two disjoint eras**; old era 1,827 dup groups, 448 null weeks | `gsis_id`, 99% | Design needed |
| `load_contracts` | 51,803 | 25 | **NO — best candidate still 2,901 dup groups** (max 9) | `gsis_id` 92%, `otc_id` 100% | Design needed |
| `load_ff_rankings` | 5,281 | 25 | YES on `(ecr_type, page_type, id)` | name/`id` only, no gsis | **Governance conflict** |

**The board's premise — six drop-in `StreamSpec` entries, one batch — is measurably wrong. Exactly
one of the six is drop-in.** I am recording this now rather than absorbing it, per the board's own
standing obligation: *"if the gate begins expanding mid-batch, the implementing lane says so AT THAT
MOMENT rather than absorbing it and reporting a long session afterwards."*

This is a finding about the work, not a request to stop. Streams still land this session.

### 2.1 The four that are not drop-in — the specific reason each

**`load_ff_rankings` — this is FantasyPros ECR, i.e. market data.** Columns `fp_page`, `ecr_type`,
`ecr`, `sd`, `best`, `worst`, `player_owned_espn`, `player_owned_yahoo`. `00` §KTC And Market Data
names FantasyPros explicitly: *"overlays only… must never enter Engine A or Engine B as predictive
model features."* `01` §Feature Store requires market-derived values be *"physically and semantically
separated from Engine A and Engine B training features."*

`app/data/nflverse_usage.db` **is** the Engine-B feature substrate — its export is read by
`scripts/run_feature_refresh.py` and `scripts/assemble_engine_b_dataset.py`. Landing FantasyPros ECR
into that store puts market data physically inside the feature store. **It must not land there.**
Second, independent problem: `scrape_date` holds a **single value (`2026-07-31`)** — this is a
current snapshot that overwrites, not a history. Under the compounding lens it belongs to the
existing market PIT capture lane, not to a feature-substrate batch.
→ **Recommend: remove from this batch.** Destination is a separate decision.

**`load_ftn_charting` — no player identity exists.** Grain is play-level and provably perfect
(143,572/143,572 unique, zero nulls on `(nflverse_game_id, nflverse_play_id)`). But `StreamSpec`
requires `identity_column` + `identity_kind` and runs identity resolution on every row. A play-grain
stream has no player to resolve. → Needs a *narrow, reviewed* mechanism extension (identity-exempt
streams), not a fabricated identity column.

**`load_depth_charts` — two eras sharing almost no columns.** 74,639 rows carry
`season/week/club_code/depth_position/game_type`; **554,215 rows carry none of those** and instead
carry `dt/team/espn_id/pos_grp/pos_slot/pos_rank`. The new era is a **daily** snapshot (`dt`), a
different grain entirely, not a weekly one. The old era is *also* not clean: 1,827 dup groups and 448
null weeks on my candidate key. → `StreamEra` exists for exactly this, but two eras with different
*grains* is beyond what the current `StreamEra` expresses (it varies columns, not grain semantics).

**`load_contracts` — no unique key found, plus a nested column.** Best candidate
`(otc_id, year_signed, team, years, value, apy)` still leaves 2,901 duplicate groups. `cols` is
`List(Struct(...))` of year-by-year cap detail — SQLite cannot hold that without an explicit decision
(JSON-encode vs. explode to a child table). → Real design work; also the stream with the least
established dynasty value.

**`load_ff_opportunity` — 1,280 null `player_id` and 65 real duplicate groups.** The nulls are
plausibly team-aggregate rows, which would be a filter/era decision rather than a defect — but that
is a hypothesis I have not tested, and 159 columns need an explicit projection.

## 3. Mislead / nudge risks

- **The market-separation breach above is the headline risk** — it would be silent. Nothing in the
  reduced gate checks "is this source market-derived", and the batch framing ("six free loaders")
  actively obscures that one of them is a price feed.
- **`substrate_only` inflation.** Six new streams with zero consumers make the existing
  no-consumer problem larger, not smaller. The board already says this plainly and I restate it:
  **completing Layer 1 will not produce edge.** The honest headline after this batch is *"fuel
  landed, none of it burning yet."*
- **Contracts are a candidate signal of unestablished value.** The board records a prior overclaim
  ("guaranteed money is a team's revealed expectation of role") asserted as fact. Nothing derived
  from contracts may be asserted as a dynasty signal without Layer-2 validation.
- **Row counts are not progress.** 143,572 FTN play rows would dominate any row-count headline while
  being the stream furthest from a consumer.

## 4. Falsification seeds for the RED

1. **Market-source guard** — a `StreamSpec` whose source is market-derived must be **refused** by the
   feature-substrate store. Positive control: attempt to register `ff_rankings` against
   `nflverse_usage.db` and require a refusal.
2. **Grain uniqueness is enforced, not assumed** — feed a duplicate row on the declared grain; require
   refusal, not last-wins. (Regression target: the depth-chart and contracts dup groups above.)
3. **Unrecognised column set refuses** — additive provider column must fail, per the existing
   `StreamEra.matches` exact-equality contract (`nflverse_usage.py:206-215`).
4. **Null grain coordinate refuses** where `require_populated_grain` is set (448 null depth-chart weeks
   is the live positive control).
5. **Identity-exempt streams still record an identity census** — an FTN row must not silently acquire
   a null `dg_player_id` that later reads as an unresolved player.
6. **Failed run preserves last-good** — existing table counts unchanged after an induced mid-run
   failure; the five existing tables (`ngs_passing` 5,933 · `ngs_receiving` 14,731 · `ngs_rushing`
   6,059 · `player_snap_count` 253,106 · `nflverse_injury_report` 34,812) must be byte-identical.
7. **Replay determinism** — same raw snapshot in, identical normalized rows + row hash out.
8. **Export typing** — integer/float columns publish as real numbers, not `Utf8` (the E1 defect
   recorded at `nflverse_usage.py:231-237`).

## 5. Overclaim check against the No-Verdict Line

This work emits no David-facing surface, no score, no ranking, and no verdict. Every stream lands
`substrate_only` with a named decision owner and the separate validation gate that would be required
before any use. `decision_supported` is untouched. **No claim is made that any of these streams has
predictive value** — contracts, depth charts, FTN charting and expected-points opportunity are all
**candidate** signals of **unestablished** value.

Unrelated ceiling restated because it travels with this repo: **H2 QB rushing remains a registered
hypothesis UNDER TEST; the study has not run and there is no result.**

## 6. Recommended sequence — proposal, not a decision

1. **`pfr_advstats` first, this session.** The only unambiguous stream: four stat types, provably
   unique grain, complete `pfr_player_id`, 46,575 rows. Mirrors the existing NGS pattern exactly (one
   loader → several `StreamSpec`s bound with different `stat_type`). Lands with zero new mechanism.
2. **`ftn_charting` second**, if the identity-exempt extension is cleared — its grain is the cleanest
   of all six.
3. **`ff_opportunity`, `depth_charts`, `contracts`** — each needs its own design answer above; they
   are not one batch and should not be reported as one.
4. **`ff_rankings` — out of this batch.** Destination is a governance-constrained decision for David.

**Open question for David** (surfaced, not assumed): his ruling said *six as one batch*. The
measurement says one is market data that cannot land in the feature store and three need individual
design. **I am not treating "six as one batch" as overridden by my own measurement** — I am reporting
the measurement and proceeding with the streams that are unambiguously in scope.

## 7. What I am NOT asking for

No commit, push, merge, or model/feature use. No consumer is built for any stream. No paid source is
touched. The gitignored duplicate NGS data tree is untouched.

---

**PLEASE CHALLENGE:** every claim in §2 is reproducible from the promoted probe scripts. The
market-separation reading in §2.1 and the "not one batch" conclusion in §6 are the two I most want
attacked.
