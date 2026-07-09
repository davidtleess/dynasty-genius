---
document: Phase-0b — Scheduled Market-Source Ownership + Market-Vintage Provenance
version: 1.4.0 (v5 — uncommitted; DAVID-RATIFIED rulings pinned)
author: Claude Code
date: 2026-07-09
status: Codex CLEAR (technical, enumerated checks). Gemini advisory concerns closed.
        DAVID RULED 2026-07-09 — see §0.1. NEXT ACTOR: Codex authors the RED from §5 + §6.
        Nothing committed or pushed. No runner run. No LaunchAgent.
review_history: |
  v1 → Codex NOT-CLEAR, 5 defects (Option-B/§5.2 contradiction; §5.1 pre-decides the fork; §8
  missing the A′ post-migration capture; duplicate-conflict seed conflated model PIT with FC PIT;
  source_timestamp citation off by two lines). All 5 independently verified by Claude, accepted.
  Gemini: ruled A′, supplied the §3.1 copy bans and the null-disclosure treatment, raised
  volatility-as-liquidity.
  v2 → Codex confirmed all 5 integrated, then NOT-CLEAR on 2 NEW defects: (1) the A′ operational
  sequence permitted a same-date volatility capture that the immutable FC store would reject with
  FCForwardCaptureConflictError; (2) §5.6 was under-specified for RED (no named status field or
  effective-date field). Both verified by Claude against the store code and the live data, and
  fixed in v3. Gemini ACCEPTED both Claude amendments (dynamic caveat boundary; No-Verdict cordon
  on volatility) and confirmed §5.3 suffices for its in-season gate (§5.7).
governs: scripts/run_market_divergence_refresh.py, src/dynasty_genius/universe_market_divergence.py,
         src/dynasty_genius/adapters/fantasycalc_adapter.py, src/dynasty_genius/capture/fc_forward_capture_store.py
---

# Phase-0b: Scheduled Market-Source Ownership + Market-Vintage Provenance

## 0.1 David's rulings — RATIFIED 2026-07-09 (binding; supersede all lane recommendations)

1. **Fork → A′.** Rewire the runner onto `fc_forward_capture` PIT rows **plus** the additive
   `market_volatility` / `market_volatility_status` / `volatility_schema_effective_date` contract
   (§5.6). One store of record. Option B is closed.
2. **Interim baseline → REGENERATE.** Do not keep serving the false market vintage on `/players`.
   Regeneration is **conditional on §5.6 landing first** (§5.6.1), so the resulting PIT row is
   self-describing. David accepted the cost: **one permanently `structurally_unavailable`
   volatility day** in the Gate-4 ledger.
3. **Program sequencing → Gemini's order.** Phase-0b → Daily Open Comp v3 → PVO-Scale Solutioning
   → Value Board UI Build. The UI primitives will be built against the `dvs_raw` basis from day
   one rather than refactored after normalization.

Everything below is read under these rulings. **They authorize spec content and the RED, not any
commit, push, runner run, backup, or LaunchAgent install** — each of those remains a separate
David-gated action.

## 0. Scope and standing constraints

This is a **design spec**, not a RED. Per `02-agent-operating-loop.md`, Codex authors the RED
from these seeds; Claude implements GREEN; both lanes review adversarially; David authorizes
every commit, push, runner run, and the LaunchAgent install.

Standing constraints that bind every section below:

- `decision_supported=false` end-to-end. The margin is descriptive. The No-Verdict Line holds.
- **The scheduled runner NEVER live-fetches.** Live fetch stays David-gated / bootstrap-only.
  No live-fetch fallback may be introduced into the scheduled path.
- Market data stays an overlay. It never enters Engine A/B features (`00` KTC ruling).
- **No LaunchAgent install** until this contract is RED/GREEN and dual-CLEARed.
- Compounding-product lens: the PIT series is the compounding asset. Compounding never
  licenses overclaim.

## 1. Why (the failure this closes)

The Phase-0 runner (PR #128) fail-closed on its first production run with `market_cache_stale`.
That was **correct behavior** and it exposed a contract gap, not a bug in the runner.

`scripts/run_market_divergence_refresh.py` reads `app/cache/fantasycalc/market_values.json`.
That cache has **no scheduled owner**: it is written only by `_save_cache()` (`fantasycalc_adapter.py:59-68`)
as a side effect of the live-fetch path inside `fetch_with_cache()` (`:86-96`). The real daily
market store is `app/data/fc_forward_capture.db`, written by the 09:00 `fc-snapshot` LaunchAgent.
The scheduled capture and the runner's source are **disconnected stores**.

**Non-finding, closed.** The prior manual rebuild did not rewrite the cache because it did not
need to: offseason TTL is 24h (`fantasycalc_adapter.py:38-47`), the cache was 17.26h old at build
time, so `fetch_with_cache()` returned at the Stage-1 fresh-serve branch (`:80-82`) and never
called `_save_cache()`. Nothing was swallowed on that path. The cause does **not** gate the fix
fork. *(Claude's round-0 position that it did was wrong and is withdrawn.)*

## 2. The five defects this spec closes

### D1 — `source_timestamp` is affirmatively false; its own caveat vouches for the lie

`universe_market_divergence.py:134` sets `source_timestamp = datetime.now(timezone.utc)` — the
**builder wall clock** — and stamps it into every overlay (`:165`). (`:132` sets the separate
`captured` build stamp. Corrected in v2 per Codex defect #5.) The served artifact on `main`
carries, per player:

```json
"source_timestamp": "2026-07-08T19:43:56Z",
"caveats": ["source_timestamp_is_fetch_time_not_publish_time"]
```

The actual FantasyCalc fetch was `2026-07-08T02:28:19Z` — **17.26h earlier**. The field is named
for the source, carries build time, and its caveat explicitly asserts the value *is* fetch time.
A consumer that follows the caveat exactly as written reads build time as market vintage.

This is silent substitution under `01-north-star-architecture.md:85` — and worse than silence,
because it is an assertion. **The affected artifact is live on `main` via PR #130.**

### D2 — the compounding PIT series is keyed on the wrong axis

`_capture_date()` (`run_market_divergence_refresh.py:140-142`) slices `batch["captured_at"]`, and
the runner sets `captured_at = now.isoformat()` (`:315`). So the history PK
`(player_id, capture_date)` (`:157`) records **the day the runner ran**, not the day the market
data is from. A late run, a UTC-midnight crossing, or a stale-but-in-TTL snapshot all mis-key the
row. The C1 freshness gate bounds this skew; it never removes it.

D1 and D2 compound: a Gate-4 validation row keyed by build date, carrying a source timestamp that
claims build time is fetch time. Every row provenance-corrupt, silently.

### D3 — a naive rewire silently destroys 168 live `market_volatility` values

`market_overlay.market_volatility` is populated for **168 of 399** overlays in the served
artifact (source: FC `maybeMovingStandardDeviation`, 168/463 non-null in the cache payload).
`fc_forward_capture_joinable` has **no volatility column** (`snapshot_date, source, settings_hash,
player_key, sleeper_id, player_name, position, value, overall_rank, position_rank, trend_30day,
retrieved_at, payload_hash`).

Rewiring the runner onto the PIT store therefore **silently nulls a live field**. This is
data loss dressed as a refactor, and it is the single strongest argument against the PREFERRED
fork as originally stated. See §4.

### D4 — the freshness gate does not survive the rewire

The runner's freshness contract is **inherited from the cache payload**:

```python
ttl_hours = float(market_payload.get("ttl_hours", 24))
...
if age_hours > ttl_hours: return _abort("market_source", "market_cache_stale")
```

`fc_forward_capture_joinable` has `snapshot_date` and `retrieved_at` and **no TTL column**. A
rewire that merely re-points the reader **deletes the staleness check**. The gate must be
**re-specified, not re-pointed**.

### D5 (companion) — the adapter's silent swallow is a *user-facing* defect

`_load_cache()` (`:50-56`) and `_save_cache()` (`:59-68`) are both bare `except Exception: pass`.
Rewiring the runner makes the **runner** safe and leaves the **API surface** silently degradable,
because `fetch_with_cache()` remains live behind:

| Consumer | Path |
|---|---|
| Market overlay service | `services/market_overlay_service.py:190-192` |
| Roster audit | `app/services/roster_auditor.py:658` |
| Rookies route | `app/api/routes/rookies.py:63` |
| Trade analyzer | `app/services/trade_analyzer.py:240` |
| Trade market route | `app/api/routes/trade_market.py:93` |
| Market source adapter | `adapters/market_source.py:20-24` |
| League-intelligence refresh | `scripts/run_league_intelligence_refresh.py:84,230` |

Both lanes ruled this **in scope** for Phase-0b.

## 3. Framing fact — what Phase-0b actually delivers (not a defect)

Model output has been **byte-identical for 13 consecutive days**: from 2026-06-27 through
2026-07-09, `model_forward_capture_joinable` shows 583 rows/day, exactly one
`semantic_output_hash` per day, and mean `dynasty_value_score = 49.241` every day.

Therefore, in the offseason **the model cannot diverge overnight**; 100% of daily margin movement
is market movement. This is doctrinally intended (`00-product-constitution.md` In-Season ruling:
offseason PVO stays stable until snaps accrue; "the model is the anchor").

**Consequence, binding on David-facing copy:** Phase-0b ships a *daily market tape measured
against a frozen model anchor*. No surface, caveat, or commit message may imply overnight model
movement in July. Gemini's ratified label — `Off-season Baseline: Frozen until Week 1 snaps` — is
a literal description of the store, not a hedge.

### 3.1 Banned framings (Gemini, v2) — the "system is getting smarter" illusion

A daily-refreshing market side against a 13-day-static model side can read as the *system*
improving each morning. Banned up front rather than patched in Phase 2:

| Class | Banned | Use instead |
|---|---|---|
| Header nouns | "Model Refreshed", "System Updated", "Roster Valuations Recomputed" | "Market Prices Refreshed", "Daily Market Tape Loaded" |
| Computation copy | "Recalculating Roster Equity", "Divergence Analysis Complete" | "Model-to-Market Spread Updated" |
| Visual indicators | Any up/down arrow or green/red change delta beside **Model Rank** or **Model Value** during the offseason | Model columns render visually static |

The third row is the sharp one: an arrow beside a model number that has not moved in 13 days is a
lie told in glyphs. This is a **Phase-2 display** rule recorded here because Phase-0b is where the
data contract that enables it is set.

## 4. The fork — and why D3 reopens it

Both options were framed in the 2026-07-09 ledger. D3 was not known when they were framed.

**Option A — PREFERRED-as-stated: rewire the runner onto `fc_forward_capture` PIT rows.**
Consumes the genuinely-owned scheduled store; matches the What-Changed precedent
(`what_changed/daily_diff.py:30-47`). **But** it nulls 168 `market_volatility` values (D3) unless
the PIT store schema is extended.

**Option A′ — PREFERRED + additive column.** Same rewire, plus an additive
`market_volatility` column on `fc_forward_capture_raw`/`_joinable`, populated going forward.
Historical rows stay null and must be **explicitly caveated as structurally unavailable**, never
silently null. Cost: touches the capture store schema; the 16 accrued days cannot be retrofitted.

**Option B — LOWER-BLAST: `run_fc_forward_capture.py` atomically exports `market_values.json`.**
Preserves the full FC payload including volatility; the runner keeps its existing reader.
Cost: keeps the cache as a real contract surface, and leaves two stores of record for market data.

> **v2 correction (Codex defect #1).** v1 said Option B "keeps its existing TTL semantics." That
> is **wrong** and contradicts §5.2. Under **every** option, freshness must be derived from code
> and season and the source's own vintage — **never** from a `ttl_hours` value the payload supplies
> about itself. Option B narrows the blast radius; it does **not** exempt the runner from the
> §5.2 gate. D4 does not "dissolve" under B.

**Both technical and product lanes independently ruled A′ (2026-07-09).**
- *Codex:* "I prefer A-prime over B architecturally: one scheduled PIT store should be the source
  of record, and volatility should be added to that store" — conditioned on the §8 post-migration
  capture sequence below.
- *Gemini (advisory):* "I rule in favor of Option A′… Carrying two market stores of record for the
  sake of preserving 16 days of off-season volatility data is a long-term architectural tax that
  violates `01-north-star-architecture.md`."
- *Claude:* concurs. One owned store is the architectural end-state; the volatility gap is honest
  if disclosed as structurally unavailable rather than rendered as null-means-zero.

**The ruling is still David's.** Codex's standing caveat: *if David wants the corrected baseline
immediately while preserving volatility without another live FC capture, **B is lower risk**.*
That trade — architecture vs. an immediate volatility-preserving baseline — is the decision.

## 5. Contracts the RED must assert

### 5.1 Source contract (v2 — fork-neutral per Codex defect #2)
- The scheduled runner reads **the David-ruled scheduled market source** only: either
  `fc_forward_capture` rows with the §5.6 schema extension (A′), **or** an atomically-exported
  cache artifact owned and written by the FC capture job (B). Under B the exported artifact is an
  **owned scheduled output**, not an orphan side effect.
- No live network. No fallback. Under **neither** option may the runner live-fetch.
- A run whose market source is absent, unreadable, wrong-shape, or empty **aborts before any
  `latest` write**, writes a status marker with a named reason, and leaves the tracked pair
  byte-identical.

### 5.2 Freshness contract (replaces the inherited-TTL gate; D4) — binds under BOTH forks
- Freshness is derived from the market source's own vintage (`snapshot_date` / `retrieved_at`)
  and from a **code-and-season-owned bound**, **never from a value the payload supplies about
  itself**. Today `ttl_hours = float(market_payload.get("ttl_hours", 24))`
  (`run_market_divergence_refresh.py:297`) lets **the data decide whether the data is fresh**.
  Codex ruled this attack in-RED for both A′ and B.
- The 09:40 runner MUST accept the same-day 09:00 capture and MUST reject a prior-date capture.
- The bound must honor the seasonal asymmetry (6h in-season / 24h offseason) or explicitly
  supersede it with a stated rule. Codex's stated preference: `snapshot_date == runner local date`
  **and** `retrieved_at <= runner_now` **and** age within the seasonal bound.

### 5.3 Provenance contract (D1)

**The false vintage is LIVE on the `/players` API contract — not inert in a file.** Verified:
`players.py:150` loads the artifact per request; `:213` sets `source_timestamp=overlay.get("source_timestamp")`
into the DTO field declared at `:101`; `:302` additionally exposes `source_timestamps.market`
derived from the artifact's `captured_at`. **The RED must cover BOTH fields** (Codex).
*(`trade_market.py:100` loads the artifact but attaches divergence context, not the timestamp —
`trade_lab/market_reconciler.py:768`. The live-falsehood proof rests on `/players`.)*

- `market_overlay.source_timestamp` MUST carry the **market source vintage**, never the build clock.
- Build time remains available as a **distinct** field (`captured_at`).
- **No production consumer breaks** when the value changes from build time to true vintage
  (Codex-verified): `frontend/src/lib/api/zod.gen.ts:598` types it as a nullable string;
  `frontend/src/player/ValuationTwoLane.tsx:74` renders it as text. One fixture assertion at
  `frontend/src/player/PlayerDetailPage.test.jsx:188` is **test data to update**, not a production
  dependency on false semantics.
- The caveat `source_timestamp_is_fetch_time_not_publish_time` must become **true**, or be renamed
  or removed. A caveat that vouches for a false semantic is itself a defect.
- The artifact MUST carry the model-side vintage (`source_snapshot_captured_at`) and the
  market-side vintage **distinctly**, so a surface can render both. *(Gemini's disclosure
  requirement, carried into the technical contract.)*
- Gemini's product condition, recorded: *"If we cannot guarantee the true source timestamps are
  exposed to David, then daily shipping is dishonest and should be withheld."*

### 5.4 PIT key contract (D2)
- `capture_date` in `market_divergence_history` MUST derive from the **market snapshot date**,
  not the runner wall clock.
- The row MAY additionally carry the build/run timestamp; it may not be the key.
- Idempotent upsert on `(player_id, capture_date)` is preserved.

### 5.5 Adapter hardening contract (D5)
- `_load_cache` / `_save_cache` failures MUST surface as caveats or a fail-closed status, never
  as silent success.
- Hardening must **not** turn live API routes into runner dependencies.
- `01-north-star-architecture.md:76,85` is the governing rule.

### 5.6 Volatility contract (D3) — applies if David rules A′

**v3 (Codex v2-defect #2): concrete fields, or the RED cannot be written.**

Additive columns on `fc_forward_capture_raw` and `_joinable`, populated forward from FC
`maybeMovingStandardDeviation`:

| Field | Type | Semantics |
|---|---|---|
| `market_volatility` | `REAL NULL` | the value, or NULL |
| `market_volatility_status` | `TEXT NOT NULL` | exactly one of `captured` \| `source_omitted` \| `structurally_unavailable` |

Plus a store/report-level `volatility_schema_effective_date` recording the migration boundary.

- `captured` — FC published a value and we stored it.
- `source_omitted` — FC published no value (today: **295 of 463** entries). A real fact about the
  source.
- `structurally_unavailable` — the row predates the schema. The 16 accrued days
  (2026-06-24 → 2026-07-09) **cannot** be retrofitted and carry this status permanently.

These are **three different facts** and the data layer carries all three, even where the surface
collapses the latter two into one dash. **A null must never render as zero, and must never be
silently dropped.** `market_volatility_status` is what makes D3 honest rather than merely disclosed.

- *Gemini surface treatment (advisory, Phase-2 binding):* neutral dash `—` in the grid; one system
  caveat in the collapsible drawer on volatility-displaying surfaces; no per-player visual
  distinction (it would clutter the layout).
- *Claude amendment — Gemini ACCEPTED:* the caveat derives its boundary from
  `volatility_schema_effective_date`, **never a hardcoded literal date**. A hardcoded date rots at
  the next migration and then asserts something false — the same failure class as D1. A caveat that
  vouches for a stale fact is a defect.
- *Gemini P4, carried with a No-Verdict guard — Gemini CONFIRMED:* the column must be **queryable
  and typed**, so a future surface can offer volatility as an explicit, disclosed **sort/filter
  key**. Per `00-product-constitution.md`, an explicit disclosed sort order is permitted; a
  volatility-derived **verdict, tier label, or nominated target is not**. A "High Activity /
  Volatile" *filter label* is legal; a tool-chosen recommendation is banned. The RED asserts the
  column's queryability, **not** any decision semantics.

**5.6.1 — the fidelity metadata must reach `payload_json` BEFORE the history upsert (Codex).**
`market_divergence_history` has no typed fidelity columns; it stores `payload_json` under
`(player_id, capture_date)` (`run_market_divergence_refresh.py:157`). Therefore
`market_volatility_status` and `volatility_schema_effective_date` MUST be present **inside every
emitted player payload** before the upsert, or a regenerated PIT row is silently degraded rather
than self-describing. **Scope note:** "queryable" here means **JSON-extraction queryable**, not
first-class SQL columns in the history table. First-class history columns are out of scope.

### 5.7 In-season staleness gate — data-layer sufficiency (resolved)

Gemini's 7/14-day desaturate/suppress gate is a **Phase-2 display** contract, deliberately not in
this spec. Confirmed sufficient: §5.3's distinct model and market vintages are all the display
layer needs to compute the elapsed delta at render time. *Gemini: "No pre-computed staleness flags
are needed in the database"* — keeping the delta in the display layer prevents business-logic
leakage into the schema. No additional Phase-0b field is required.

## 6. Falsification matrix seeds (carry into Codex's RED)

| Input class | Seed |
|---|---|
| valid-nominal | 09:00 same-day capture → 09:40 runner publishes; history keyed by market date |
| boundary | capture exactly at the seasonal age bound; runner local-date rollover at UTC midnight |
| stale | prior-date capture → abort, marker reason, tracked pair byte-identical, no history row |
| missing | market store absent → abort, named reason |
| malformed-shape | PIT table present but zero rows; wrong column types |
| wrong-type | non-numeric `value`; unparseable `retrieved_at` → cannot prove freshness → abort |
| duplicate/conflict | **v2 (Codex defect #4):** FC-specific. The FC store keys on `(snapshot_date, source, settings_hash, player_key)` and **raises** `FCForwardCaptureValidationError` on same-key differing content (`fc_forward_capture_store.py:122-125`), so "which capture wins" is the wrong frame. Seed instead: **multiple `settings_hash` values for one `snapshot_date`** → the runner must filter to the expected source/settings or **abort on ambiguity**, never silently pick one. *(The observed 2026-06-26 double capture — 1166 rows / 2 hashes — is **model-side**, and is out of scope unless backfill or model-PIT joining returns.)* |
| empty-collection | zero joinable rows → abort, not a vacuous "ok" |
| cross-component-shape | overlay built from PIT rows must not silently drop `market_volatility` — assert explicit unavailable-caveat (D3) |
| numeric edge | margin crossing zero must render unclamped (No-Verdict Line: surface arithmetic honestly) |
| provenance | `source_timestamp != captured_at` whenever the market vintage precedes the build |
| adversarial | a payload that supplies its own `ttl_hours` must NOT be able to widen its own freshness window |

The last row is the D4 defect restated as an attack: **the current code lets the data decide
whether the data is fresh.**

## 7. Explicitly OUT of scope (named, not omitted)

1. **Backfill of the 16 accrued days.** Both PIT stores overlap perfectly 2026-06-24→2026-07-09,
   so a core margin series is reconstructable — but reconstruction is **reduced fidelity** (no
   volatility; no per-date PVO batch shape) and the history schema has **no provenance column** to
   mark it. Seeding mixed-fidelity rows that later read as equivalent is the
   compounding-licenses-overclaim defect. Codex and Claude both lean **no backfill this session**.
   If David wants it: it requires a `history_basis` / `reconstruction_fidelity` discriminator first.
2. **Pair-atomic publish.** `latest` and `coverage` publish sequentially; a concurrent reader can
   observe a fresh `latest` beside a prior `coverage`. The runner's own docstring (`:14-20`) names
   this. Follow-up, not this RED.
3. **Rebuilding the served baseline on `main`.** Codex's technical read is disposition **(ii)**:
   fix forward, then regenerate as a **David-gated** run once the code clears. **Until then,
   Phase 2 must not consume the current baseline as freshness-true.**

   **The interim question (David's, both lanes have input).** Between merge and the first new-date
   capture, the served baseline either (a) stays as-is, carrying the **known-false** market
   `source_timestamp` (D1), or (b) is regenerated from **pre-migration** rows — provenance-correct
   but with all `market_volatility` set to `structurally_unavailable`.

   **Resolution arc (recorded because two positions were reversed on evidence):**

   1. *Codex:* don't regenerate from old rows unless David accepts the volatility regression.
   2. *Gemini:* regenerate — *"we always choose missing data over false metadata."*
   3. *Claude synthesis:* §5.6's `market_volatility_status` disclosed the regression by
      construction, so no technical objection remained. **This understated the cost.**
   4. *Claude, against his own synthesis:* the runner **publishes then appends history**
      (`run_market_divergence_refresh.py:341,358`), so a regeneration run **permanently** writes a
      `structurally_unavailable` Gate-4 row for that date. Not a 24-hour cost — a permanent one.
   5. *Codex confirmed* the permanence with citations. *Gemini reversed to "don't regenerate,"*
      reasoning the false timestamp was *"a temporary, developer-facing metadata error… in an
      inactive, unserved file."*
   6. **That premise was false, and Claude probed it.** The artifact is served by `/players`
      **today** (`players.py:150,213,302`). Gemini's repo-state claim was marked **non-binding**
      per 02 §7.6 and is logged here rather than dropped. The trade was never
      "permanence vs. a dev-only file" — it is **permanence vs. an actively false market vintage
      on a live API contract.**
   7. **Both lanes re-ruled on corrected facts: REGENERATE, conditional on §5.6 landing first.**
      - *Codex:* "regenerate is technically preferred, conditional on §5.6 landing first and RED
        proving the served artifact plus PIT `payload_json` carry explicit volatility fidelity
        metadata." Codex found **no live consumer that breaks** when the value becomes true vintage.
      - *Gemini:* "an honestly labeled, queryable gap in our compounding history is a normal
        operational artifact; a false timestamp is a defect."
      - *Claude:* concurs. Permanence is only a harm if the row **lies or is silent** about what it
        lacks. With §5.6.1 it does neither.

   **Still David's ruling.** The cost is explicit: one permanently `structurally_unavailable`
   volatility day in the Gate-4 ledger, bought to stop serving a false market vintage on a live API.
4. **The LaunchAgent install.** Machine change, David-gated, strictly after dual-CLEAR.

## 8. Sequence (v5 — David-ratified per §0.1; Codex-amended)

**Build sequence.**
1. ~~Cockpit adversarial review of spec v1~~ → **done**: Codex NOT-CLEAR (5 defects), Gemini
   product review. Both lanes ruled A′.
2. ~~Cockpit re-review of v2~~ → **done**: Codex NOT-CLEAR (2 new blockers), fixed in v3;
   **Codex CLEAR on v3** with enumerated checks, and RED authorship accepted.
3. **David rules the fork** (A′ vs B, §4) and the served-baseline disposition (§7.3).
4. **Codex authors the RED** from a stable §5 + §6. *(Codex accepted RED authorship.)*
5. Claude GREENs.
6. Adversarial dual-CLEAR — falsification matrix re-run on the changed surface (§Falsification #5:
   a fix is a new state machine, not old code plus a guard).
7. David authorizes commit → push → PR → CI → merge.

**Operational sequence — DO NOT COLLAPSE INTO THE BUILD SEQUENCE.**

> **Codex defect #3, accepted.** v1 jumped from merge straight to the runner run. Under **A′**
> that is a trap: a corrected runner fed **pre-migration** FC rows would regenerate the served
> baseline and convert **168 live `market_volatility` values into structurally-unavailable nulls**,
> with only a caveat to show for it. The volatility column is populated *forward only*.

**DAVID RULED A′ + REGENERATE (§0.1). The operational sequence is therefore TWO runner runs:**

8. Schema migration + §5.6 metadata land and are verified. *(§5.6.1 is a precondition of step 9 —
   regeneration before the payload carries `market_volatility_status` would write a **silently**
   degraded PIT row, which is the thing the ruling exists to prevent.)*
9. **Regeneration run (David-gated).** Reads **pre-migration** FC rows. Publishes a
   provenance-correct baseline — true market `source_timestamp` — with every
   `market_volatility_status = structurally_unavailable`. This is the run that stops the live
   `/players` falsehood. It writes **one permanent PIT row** for that market snapshot date.
   *Note: this run does **not** conflict with the immutable FC store — the new-date rule below
   constrains the **capture**, which writes to that store, not the **runner**, which only reads it.*
10. **Next scheduled 09:00 capture** — a NEW `snapshot_date` under the new schema, volatility-bearing.
11. **Runner run** → volatility-complete baseline; that date's PIT rows carry `captured` /
    `source_omitted` statuses.
12. Verify → backup / manifest → LaunchAgent install. Each David-gated.

**Is the step-9 row's degradation really permanent?** Yes, and the reason is worth stating because
the history upsert is idempotent on `(player_id, capture_date)` (`run_market_divergence_refresh.py:157`),
which *looks* like it would let a later run heal the row. It cannot: healing would require a
volatility-bearing FC capture **for that same market snapshot_date**, and the immutable store
rejects adding differing content to an existing `(snapshot_date, source, settings_hash, player_key)`
(`fc_forward_capture_store.py:141`). So the gap is permanent by construction — exactly the cost
David accepted, and it is honestly labeled rather than silent.

---

**The new-date rule (retained, and it governs step 10):**

*A NEW-DATE capture bearing volatility must exist before step 11.*

   > **v3 blocker (Codex v2-defect #1), verified.** v2 said "a David-gated FC capture run, or wait
   > for the next scheduled capture." The first half is a trap. The FC store enforces immutable
   > snapshots: it raises `FCForwardCaptureConflictError` when incoming content differs from stored
   > content for the same `(snapshot_date, source, settings_hash, player_key)`
   > (`fc_forward_capture_store.py:141`). `snapshot_date = 2026-07-09` **already exists**. A
   > same-date recapture that now carries non-null `market_volatility` differs in content and would
   > **hard-fail on conflict**.
   >
   > **Rule:** the first volatility-bearing capture must be for a **new `snapshot_date` after the
   > migration** — in practice, wait for the next scheduled 09:00 capture. A same-date upgrade is
   > permitted **only** under an explicitly specified, David-approved one-time migration path.
   > Codex prefers the new-date rule; so does Claude: a sanctioned mutation of an immutable
   > snapshot store is a contract change, not an ops step.

**Practical consequence:** the *volatility-complete* baseline cannot exist until after the next
09:00 capture. But under David's ruling 2, the *provenance-correct* baseline lands at step 9 —
so the live `/players` falsehood stops at merge + one gated run, not a day later. That is the whole
point of splitting steps 9 and 11.

*(Option B is CLOSED by §0.1 ruling 1 and is retained in §4 only as review history.)*

Nothing in steps 7–12 is authorized by this spec. Each is a separate David-gated action.
