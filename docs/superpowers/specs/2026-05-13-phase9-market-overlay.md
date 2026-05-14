---
spec: Phase 9 — Market Overlay
version: 1.0.0
date: 2026-05-13
phase: 9
status: draft
governance_read:
  - docs/governance/00-product-constitution.md v1.0.0
  - docs/governance/01-north-star-architecture.md v1.0.0
  - docs/governance/02-agent-operating-loop.md v1.0.0
  - AGENT_SYNC.md 2026-05-12
research_sources:
  - docs/strategies/Dynasty Genius Phase 8 Research Brief.md
  - docs/strategies/Dynasty Genius Phase 9 Research Brief 2.md
  - R-Gemini: Phase 9 Market Overlay deep research report
  - Claude synthesis: Phase 9 merge strategy + pressure test (2026-05-13)
---

# Phase 9 — Market Overlay

## Context

Phase 8 delivered decision surfaces (Roster Audit, Rookie Board, Trade Lab) wired as
read-only over the Player Value Object. Every surface now emits PVO-shaped responses
with Engine B v2 projections, age cliff signals, and explicit caveats. 339 tests pass.

The `market_overlay` field on every PVO is currently `None`. Phase 9 populates it.

The governing rule for Phase 9:

> Market data is price discovery, not truth. KTC and FantasyCalc reveal what the market
> believes about a player's value. They do not define player quality. The overlay joins
> the PVO strictly after model scoring is complete and must never feed back into any
> engine's training or inference path.

A `MarketOverlay` schema already exists in `src/dynasty_genius/models/player_value_object.py`.
A basic FantasyCalc HTTP adapter already exists in
`src/dynasty_genius/adapters/fantasycalc_adapter.py` but has critical defects that must
be corrected before any overlay math is run.

---

## Non-Goals

- No KTC integration. KTC ToS prohibits automated collection; no official API exists.
  A stub class is the only KTC artifact in Phase 9.
- No DynastyNerds, SFBX, or Underdog integration. Wrong format or no structured API.
- No DynastyDataLab integration. Pricing and programmatic API unverified.
- No blended/consensus market value. Blending smooths the divergences this phase exists
  to surface. Parallel source-tagged overlays are the right model if/when multiple
  sources come online.
- No TE model promotion. TE remains experimental. The overlay is computed and stored
  but forced to `model_unreliable`.
- No pick valuation overlay. Rookie picks are a different object model. Deferred to a
  separate `PickValueOverlay` design.
- No frontend rendering. Cards are JSON API responses only.
- No composite validation gate promotion. `decision_supported` remains `False`.

---

## Critical Defects in Existing Adapter

The existing `fantasycalc_adapter.py` must be corrected before Phase 9 proceeds.
These are not enhancement requests — they are bugs that would produce wrong output
from the first line of divergence math.

### Defect 1: Wrong URL Parameters

**Current:** `https://api.fantasycalc.com/values/current?isDynasty=true`

**Correct:**
```
https://api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1
```

Without `numQbs=2`, every QB is priced on a 1QB scale. Josh Allen's SF dynasty value
is 6232 at overall rank #19 on the SF scale. On 1QB he would be dramatically lower.
Every QB `model_minus_market_delta` calculated with the current URL is wrong.

`numTeams=12` and `ppr=1` affect all positions. Without them, the distribution of
market values is misaligned with David's specific league format.

### Defect 2: Incomplete Field Capture

**Current `normalize_fantasycalc_entry()` captures:** `full_name`, `fantasycalc_value`,
`source_fantasycalc_value`, `market_overlay: True` — a boolean flag, not a structured
overlay object.

**Required:** See §4 (MarketOverlay schema) and §5 (field mapping) for complete spec.

---

## FantasyCalc API: Confirmed Mechanics

Source: live API response captured 2026-05-13 and confirmed by R2.

### Endpoint

```
GET https://api.fantasycalc.com/values/current
    ?isDynasty=true
    &numQbs=2
    &numTeams=12
    &ppr=1
```

No authentication required. The endpoint is officially documented by FantasyCalc's
owner Josh Cordell on fantasydatapros.com — not a reverse-engineered private endpoint.
No published rate limits; no Cloudflare challenge observed.

### Confirmed JSON Shape (single player entry)

```json
{
  "player": {
    "id": 9833,
    "name": "Bijan Robinson",
    "mflId": "16161",
    "sleeperId": "9509",
    "espnId": "4430807",
    "fleaflickerId": "17603",
    "ffpcId": "28755",
    "position": "RB",
    "maybeBirthday": "2002-01-30",
    "maybeHeight": "71",
    "maybeWeight": 215,
    "maybeCollege": "Texas",
    "maybeTeam": "ATL",
    "maybeAge": 24.2,
    "maybeYoe": 3
  },
  "value": 10503,
  "overallRank": 1,
  "positionRank": 1,
  "trend30Day": -39,
  "redraftValue": 10503,
  "combinedValue": 21006,
  "maybeMovingStandardDeviation": 0,
  "displayTrend": false,
  "maybeTier": 1,
  "maybeAdp": null,
  "maybeTradeFrequency": null
}
```

### Scale Behavior

The scale is **not capped at 10,000**. Bijan Robinson sits at 10,503; Jahmyr Gibbs
at 10,363. Never assume a fixed maximum when normalizing. The scale floats with the
cohort.

### Identity Resolution

`player.sleeperId` is present on every player in the response, **including rookies**
who have no NFL stats (Carnell Tate, Makai Lemon, Jordyn Tyson confirmed in snapshot).
The primary join key to the PVO is `player.sleeperId` → PVO Sleeper player ID.
No fuzzy name matching at any stage.

**Fallback:** If `sleeperId` is null (hard match failure), attempt
`mflId` → Sleeper via DynastyProcess `db_playerids.csv`:
```
https://github.com/DynastyProcess/data/raw/master/files/db_playerids.csv
```
This file has ~11,668 rows and includes `mfl_id`, `sleeper_id`, and `ktc_id` (the
last column future-proofs KTC if a ToS-clean path ever becomes available).

`sleeperId == null` is a hard match failure. Log to `unresolved_market_players`
structured log and skip. Do not name-match. Do not guess.

### Fields to Capture vs. Discard

**Capture:**
| FC field | Maps to | Notes |
|---|---|---|
| `player.sleeperId` | join key | primary |
| `player.position` | cohort assignment | |
| `player.maybeAge` | display cross-check | not primary age source |
| `player.maybeTeam` | display context | |
| `value` | `market_value` | dynasty SF PPR value |
| `trend30Day` | `trend_delta` | signed int, same units as `value` |
| `positionRank` | `position_rank` | display context |
| `overallRank` | `overall_rank` | display context |
| `maybeMovingStandardDeviation` | `market_volatility` | store now, use in 9.5 |
| `maybeTier` | display context | FC's internal tier bucket |

**Do NOT capture:**
| FC field | Reason |
|---|---|
| `combinedValue` | dynasty + redraft blended; conflates time horizons |
| `redraftValue` | wrong time horizon |
| `redraftDynastyValueDifference` | derived from redraft blend |
| `redraftDynastyValuePercDifference` | same |
| `starter` | FC's internal fantasy app flag |
| `maybeOwner` | always null in non-connected context |

---

## MarketOverlay Schema

The existing `MarketOverlay` model in `player_value_object.py` carries these fields.
Phase 9 adds `divergence_flag`, `model_percentile`, `market_volatility`, `position_rank`,
and `overall_rank`.

```python
class MarketOverlay(BaseModel):
    source: str = "fantasycalc"
    market_value: Optional[float] = None
    trend_delta: Optional[float] = None          # FC field: trend30Day
    model_percentile: Optional[float] = None     # NEW: model pct rank within position
    market_percentile: Optional[float] = None    # computed from value within position
    model_minus_market_delta: Optional[float] = None   # model_pct - market_pct
    divergence_flag: Optional[str] = None        # NEW: see taxonomy below
    market_volatility: Optional[float] = None    # NEW: maybeMovingStandardDeviation
    position_rank: Optional[int] = None          # NEW: FC positionRank (display)
    overall_rank: Optional[int] = None           # NEW: FC overallRank (display)
    source_timestamp: Optional[str] = None       # HTTP fetch time (UTC)
    caveats: list[str] = Field(default_factory=list)
```

**`divergence_flag` valid values (complete taxonomy):**
- `aligned` — `|delta| < noise_band`
- `model_higher_than_market` — model rates player above market
- `model_lower_than_market` — market prices player above model
- `model_unreliable` — forced for all TEs regardless of computed delta
- `model_uninformative_rookie` — forced when `projected_avg_ppg_t1_t2` is None

Note: `source_timestamp` is the HTTP fetch time, not FC's internal publish time. FC
updates "multiple times per day" with no `lastUpdated` field in the response. Always
emit `source_timestamp_is_fetch_time_not_publish_time` in caveats.

---

## Mathematical Framework: `model_minus_market_delta`

### Approach

Percentile-rank divergence within position. Unit-free, robust to the non-linear
(sigmoid/logistic) market scale, bounded [−1, +1], directly interpretable as
"the model thinks this player belongs N percentile points higher/lower than the
market does."

Rejected alternatives:
- **Fit `market_value ~ f(model_PPG)`, use residual:** Requires a fit step; unstable
  for TE; hides nonlinearity. Brittle.
- **Z-score:** Outlier-sensitive at scale tops; FC's compressed tails mislead.
- **Min-max normalization:** Same outlier sensitivity; silently clips if scale top
  exceeds assumed maximum (confirmed: scale exceeds 10,000).
- **DynastyProcess ECR exponential decay formula:** Converts expert-consensus rank to
  value — wrong category. Engine B produces PPG, not ECR ranks.

### Formula

```python
# Universe: full FC response (top-300+ players), NOT just David's roster.
# Percentile computed against all players at the same position in the full
# FC payload. A roster-only cohort would have too few players per position
# to produce meaningful ranks.

def pct_rank(values: list[float], x: float) -> float:
    """Mid-rank for ties: (count_less + 0.5 * count_equal) / n"""
    n = len(values)
    if n < 2:
        return 0.5
    less  = sum(1 for v in values if v < x)
    equal = sum(1 for v in values if v == x)
    return (less + 0.5 * equal) / n

# NOISE_BAND is a named config parameter, not a magic number.
NOISE_BAND: float = 0.10  # 10 percentile points ≈ one dynasty tier

def compute_divergence(pvo_list: list, fc_response: list) -> None:
    """Mutates market_overlay on each PVO with divergence fields."""
    by_position: dict[str, list] = group_by_position(fc_response)

    for position, cohort in by_position.items():
        model_vals  = [p.projected_avg_ppg_t1_t2 for p in cohort
                       if p.projected_avg_ppg_t1_t2 is not None]
        market_vals = [p.market_overlay.market_value for p in cohort
                       if p.market_overlay is not None]

        for pvo in cohort:
            overlay = pvo.market_overlay
            if overlay is None:
                continue

            # Rookie / no-projection case
            if pvo.projected_avg_ppg_t1_t2 is None:
                overlay.divergence_flag = "model_uninformative_rookie"
                overlay.caveats.append("model_uninformative_rookie")
                continue

            m_pct = pct_rank(model_vals,  pvo.projected_avg_ppg_t1_t2)
            k_pct = pct_rank(market_vals, overlay.market_value)
            delta = round(m_pct - k_pct, 3)

            overlay.model_percentile         = round(m_pct, 3)
            overlay.market_percentile        = round(k_pct, 3)
            overlay.model_minus_market_delta = delta
            overlay.divergence_flag          = _classify_flag(delta, pvo, overlay)

def _classify_flag(delta: float, pvo, overlay) -> str:
    # TE: always model_unreliable regardless of computed delta
    if pvo.model_grade in {"EXPERIMENTAL"} or pvo.position == "TE":
        return "model_unreliable"
    if abs(delta) < NOISE_BAND:
        return "aligned"
    if delta > 0:
        return "model_higher_than_market"
    return "model_lower_than_market"
```

### Noise Band Rationale and Calibration

10 percentile points equates to approximately one tier in dynasty rankings (FC's
`maybeTier` field ranges 1–35+). Model-market correlation within position is expected
to be 0.80–0.92; at that correlation level, small gaps are noise. Cross-tier
disagreement is genuine signal.

**Calibration rule:** After 1–2 months of production data, compute flag distribution:
- If >80% of flags are `aligned`: tighten to 0.08
- If <30% of flags are `aligned`: loosen to 0.12

---

## Position-Specific Rules

### QB — Mandatory SF Scale

Always use `numQbs=2` SF values. Mixing 1QB and SF scales systematically misvalues
QBs. Engine B QB RMSE = 4.51 (highest of the three production positions), but
divergence signal is still meaningful.

### RB — Invert the Signal for Veterans

**RB age ≥ 26, `model_higher_than_market`:**
Auto-attach `rb_cliff_watch` caveat. Do NOT present as a BUY opportunity.
The market has likely priced in cliff risk correctly; Engine B's age decay function
may be under-weighted. This is the veteran cliff panic trap. Display: *"Model rates
this player above market, but this player is past the RB age cliff. Market discount
may reflect biological reality. Verify independently before acting."*

Evidence: 94.8% of qualifying RB1 seasons (15+ PPR PPG) occur before age 29. The
market has empirically correct prior knowledge here.

**RB age ≤ 25, `model_lower_than_market`:**
Auto-attach `rb_youth_premium` caveat. Market may be pricing upside the model cannot
see for an unproven young player.

### WR — Highest-Confidence Signal

Engine B WR RMSE = 2.89 (lowest of all positions). Treat WR divergence flags as
the most reliable signals in the system. No special caveats beyond the standard flags.

### TE — Force `model_unreliable`

Force `divergence_flag = "model_unreliable"` for every TE regardless of computed
delta. Engine B TE fails the validation gate (0/3). Do not flag any TE as BUY or
SELL based on model divergence.

Still compute and store `model_minus_market_delta` and `market_percentile` —
transparency value. But the forced flag prevents misuse.

Always attach to TE overlays:
- `te_model_experimental_do_not_trade_on`
- `te_market_high_variance` (TE market values are volatile; confirmed: Trey McBride
  `trend30Day = +491`, a 7%+ swing in 30 days)

### Rookies — Model Is Silent

Engine B cannot project a player with no NFL production history.
`projected_avg_ppg_t1_t2 = None` for all rookies in the Engine B path.

Force `divergence_flag = "model_uninformative_rookie"`. Only market-side fields carry
meaning: `market_value`, `trend_delta`, `market_percentile`.

**Seasonal caveat:** `rookie_peak_value_window` fires for any prospect during
April 1 – July 1. FC values are systematically inflated by post-NFL-Draft sentiment
during this window. This is not a BUY signal — it is a warning that the market is
in its annual peak-hype window.

---

## Cache Architecture

### Seasonal TTL Schedule

| Period | TTL | Rationale |
|---|---|---|
| Offseason (Feb 15 – Aug 15) | 24h | FC values move slowly; combine/draft are punctual |
| Season (Aug 16 – Jan 15) | 6h | News cycle, injuries, snap counts move values overnight |
| High-volatility (NFL draft week, trade deadline, post-combine) | 1h + manual invalidation | Major catalyst windows |
| Playoffs / dead period (Jan 16 – Feb 14) | 24h | Same as offseason |

6h is the floor for the season — fast enough to catch news cycles, conservative
enough for a free undocumented endpoint with no published rate limits. Do not poll
more frequently than every 3h regardless of season state.

### Three-Stage Degraded Behavior

**Stage 1 — Fresh fetch:** Cache miss or expired → attempt HTTP fetch → 200 OK →
refresh cache → emit normal `MarketOverlay`.

**Stage 2 — Stale-serve:** Fetch fails (5xx, timeout, network error) → serve most
recent cached payload with `caveats=["stale_market_data", "fetched_at=<ts>",
"stale_for=<hours>"]` appended. Automatic; no human intervention required.

**Stage 3 — Cold fail:** No cache exists (first run + API failure) → return
`market_overlay=None` with `caveats=["market_data_unavailable"]`.

Silent return of `None` with no caveat is structurally prevented. Every consumer
can always determine why `market_overlay` is absent or stale.

### Test Fixture

Commit the 2026-05-13 live FC snapshot as:
```
tests/fixtures/fantasycalc_sf_ppr_dynasty_2026_05_13.json
```

All unit tests for the adapter and divergence math use this fixture. No live API
calls in the test suite.

---

## Complete Caveat Taxonomy

New caveats introduced in Phase 9:

| Caveat | Trigger |
|---|---|
| `source_timestamp_is_fetch_time_not_publish_time` | Always, on every overlay |
| `stale_market_data` | Stage 2 degraded behavior |
| `market_data_unavailable` | Stage 3 degraded behavior |
| `te_model_experimental_do_not_trade_on` | position == TE |
| `te_market_high_variance` | position == TE |
| `model_uninformative_rookie` | is_prospect AND projected_avg_ppg_t1_t2 is None |
| `rookie_peak_value_window` | is_prospect AND April 1 – July 1 |
| `rb_cliff_watch` | RB, age ≥ 26, model_pct > market_pct + noise_band |
| `rb_youth_premium` | RB, age ≤ 25, market_pct > model_pct + noise_band |
| `market_recency_swing` | abs(trend30Day) > 2σ within position cohort |

Existing caveat from Phase 8 that continues:
- `no_market_overlay` — fires when `market_overlay is None` on any player card

---

## Value Above Replacement (VAR)

Phase 8.1 listed `value_above_replacement` as optional and did not implement it.
Phase 9 computes it once `dynasty_value_score` is available.

**12-team Superflex PPR replacement baselines:**

| Position | Replacement level |
|---|---|
| QB | QB25 |
| RB | RB33 |
| WR | WR53 |
| TE | TE13 |

```
value_above_replacement = player.dynasty_value_score - replacement_dynasty_value_score
where replacement_dynasty_value_score = dynasty_value_score of the Nth player
      sorted descending, N = replacement level for the position
```

**Hard constraint:** VAR is derived from model `dynasty_value_score` only. It must
never be derived from `market_value` or any `market_overlay` field. Computing VAR
from market prices would create a circular dependency between model output and
market data — a form of the leakage pattern Phase 9 is explicitly designed to prevent.

If `dynasty_value_score is None` for a player, `value_above_replacement` is also
`None`. No imputation.

---

## KTC — Formal Architecture Decision

**Decision: Defer indefinitely. Implement `KTCMarketSource` stub only.**

KTC has no official API. Their FAQ: *"We don't currently have an API or any sort of
.csv available. This is something we've discussed adding at some point down the line."*
Their ToS prohibits automated collection in two independent clauses. The site employs
active bot-detection measures.

Implement a `MarketSource` abstract base class and a `KTCMarketSource` concrete class
that raises `NotImplementedError`. This makes the abstraction real without any active
adapter. The DynastyProcess `db_playerids.csv` already contains a `ktc_id` column, so
the join layer is pre-solved if a sanctioned channel ever appears.

**Trigger conditions to revisit:**
- KTC publishes an official API or partner program.
- KTC launches a ToS-clean manual export for personal use.
- A community-curated, verified-ToS-clean KTC snapshot becomes available.

---

## Governance and Leakage

The following fields must never appear in Engine A or Engine B's feature set,
validation set construction, age-cliff signal computation, or training fixtures:

- `market_value`
- `trend_delta`
- `market_percentile`
- `model_percentile`
- `model_minus_market_delta`
- `divergence_flag`
- Any derivative of any of the above

**Enforcement layers:**

1. **Schema-level temporal ordering:** `market_overlay` is assembled strictly after
   `engine_b_v2_projection` is final. The assembler sequence enforces this structurally.
2. **Code review checklist item (required on every Phase 9+ PR):**
   *"Does this PR cause any MarketOverlay field or derivative to be read inside Engine A
   or Engine B's training or inference path?"*
3. **Test fixture isolation:** Engine B training and validation fixtures must not
   contain a populated `market_overlay` field. Tests that require a PVO with a populated
   overlay must construct it after the model fixture, not as part of it.

---

## API Contract

All three decision surfaces emit the same `market_overlay` node when data is available:

```json
{
  "market_overlay": {
    "source": "fantasycalc",
    "market_value": 9814,
    "trend_delta": 112,
    "model_percentile": 0.78,
    "market_percentile": 0.64,
    "model_minus_market_delta": 0.14,
    "divergence_flag": "model_higher_than_market",
    "market_volatility": 4.2,
    "position_rank": 8,
    "overall_rank": 22,
    "source_timestamp": "2026-05-13T18:30:00Z",
    "caveats": [
      "source_timestamp_is_fetch_time_not_publish_time"
    ]
  }
}
```

When data is unavailable (cold fail):

```json
{
  "market_overlay": null,
  "caveats": ["no_market_overlay", "market_data_unavailable"]
}
```

When data is stale (stage 2):

```json
{
  "market_overlay": {
    "source": "fantasycalc",
    "market_value": 9814,
    "source_timestamp": "2026-05-12T06:15:00Z",
    "caveats": [
      "stale_market_data",
      "fetched_at=2026-05-12T06:15:00Z",
      "stale_for=36h",
      "source_timestamp_is_fetch_time_not_publish_time"
    ]
  }
}
```

---

## Build Sequence and Gate Criteria

Build in this sequence. Do not advance a step until its gate is met.

### 9.0 — Adapter Foundation (prerequisite for everything)

**Gate:** Existing `fantasycalc_adapter.py` defects corrected; test fixture committed;
`MarketSource` abstraction in place.

**What it delivers:**
1. Fix URL: `?isDynasty=true&numQbs=2&numTeams=12&ppr=1`
2. Rewrite `normalize_fantasycalc_entry()` to capture all required fields per §5
3. Implement `MarketSource` abstract base class
4. Implement `KTCMarketSource` stub that raises `NotImplementedError`
5. Implement seasonal TTL cache with three-stage degraded behavior
6. Commit `tests/fixtures/fantasycalc_sf_ppr_dynasty_2026_05_13.json`
7. Contract test: adapter returns correct shape, `sleeperId` present,
   `combinedValue` absent, `source` == `"fantasycalc"`

### 9.1 — Divergence Engine

**Gate:** `compute_divergence()` produces correct flags against the test fixture for
all five divergence_flag values; position-specific caveats verified.

**What it delivers:**
1. `compute_divergence(pvo_list, fc_response)` — full-universe cohort per position,
   `pct_rank` with mid-rank tie-breaker, delta and flag assignment
2. `NOISE_BAND` as named config parameter (default 0.10)
3. Position-specific caveat attachment: `rb_cliff_watch`, `rb_youth_premium`,
   `te_model_experimental_do_not_trade_on`, `te_market_high_variance`,
   `model_uninformative_rookie`, `rookie_peak_value_window`
4. Unit tests using fixture with known player values from the 2026-05-13 snapshot

### 9.2 — PVO Integration and Surface Wiring

**Gate:** All four surfaces return populated `market_overlay`; all Phase 9 contract
tests pass.

**What it delivers:**
1. Wire `compute_divergence` into `pvo_assembler.py` — called after engine projections,
   before `model_dump()`
2. Update `run_audit_pvo()` in `roster_auditor.py`
3. Update `/rookies/score` and `/rookies/score-class` in `app/api/routes/rookies.py`
4. Update `/trade/analyze` in `app/services/trade_analyzer.py`
5. Contract tests for all four surfaces:
   - `market_overlay.source == "fantasycalc"` when data is available
   - `divergence_flag` populated on every player where model has a projection
   - TE always `model_unreliable`
   - Rookies always `model_uninformative_rookie`
   - `market_overlay is None` with `market_data_unavailable` caveat on Stage 3 (mock)
   - No `combinedValue`, `redraftValue`, or any banned field in response

### 9.3 — Seasonal Signals and VAR

**Gate:** VAR computes correctly against QB25/RB33/WR53/TE13 baselines; seasonal
caveat logic fires correctly against known dates.

**What it delivers:**
1. VAR computation using replacement baselines; `value_above_replacement` on PVO
   when `dynasty_value_score is not None`
2. `rookie_peak_value_window` date-gated caveat (April 1 – July 1)
3. `market_recency_swing` detection: `trend30Day > 2σ` within position cohort
4. Exponential backoff on 5xx/429 responses from FC

---

## Testing Requirements

Add or update tests to prove:

1. FC adapter returns correct JSON shape with all required fields when given the
   test fixture.
2. `sleeperId` is used as primary join key; name-matching is never attempted.
3. `combinedValue` and `redraftValue` are absent from every overlay object.
4. `compute_divergence` produces correct `model_percentile`, `market_percentile`,
   `model_minus_market_delta`, and `divergence_flag` for a set of known inputs.
5. Mid-rank tie-breaking: two players with identical `market_value` receive the
   same `market_percentile`.
6. All TEs receive `divergence_flag == "model_unreliable"` regardless of computed
   delta.
7. Rookies with `projected_avg_ppg_t1_t2 == None` receive
   `divergence_flag == "model_uninformative_rookie"`.
8. RB age ≥ 26 with `model_higher_than_market` receives `rb_cliff_watch` caveat.
9. `GET /roster/audit` returns `market_overlay` populated on every skill-position
   player when FC is available.
10. `POST /rookies/score` and `/score-class` return `market_overlay` populated.
11. `POST /trade/analyze` returns `market_overlay` populated on each asset PVO.
12. Stage 2 degraded behavior: mocked 5xx returns stale data with
    `stale_market_data` caveat, not `None`.
13. Stage 3 degraded behavior: mocked cold-start failure returns
    `market_overlay=None` with `market_data_unavailable` caveat.
14. No `market_value`, `trend_delta`, or `model_minus_market_delta` appears in any
    Engine B training fixture.

Use `.venv/bin/python3.14 -m pytest -q` for all verification.

---

## Acceptance Criteria

- `fantasycalc_adapter.py` sends the correct SF-specific URL with all four parameters.
- `MarketOverlay` is populated on every skill-position player across all three surfaces
  when FC is reachable.
- `divergence_flag` is set on every player; the complete five-value taxonomy is
  exhaustively covered by tests.
- TEs always `model_unreliable`; rookies with no projection always
  `model_uninformative_rookie`.
- `rb_cliff_watch` fires on every RB age ≥ 26 where model outranks market.
- Stage 2 and Stage 3 degraded behavior verified by contract tests with mocked failures.
- No banned field (`action`, `verdict`, `dynasty_tier`, `confidence`, `my_total`,
  `their_total`, `combinedValue`, `redraftValue`) appears in any response.
- `market_overlay` is assembled strictly after engine projections in assembler sequence.
- Full suite passes: `.venv/bin/python3.14 -m pytest -q`.
- `AGENT_SYNC.md` and daily ledger updated before any PR is opened.

---

## Open Questions (Not Resolved — Must Not Be Papered Over)

1. **FC rate limits.** No published limit. Mitigation: max 6h polling in-season;
   exponential backoff on 429/5xx. If rate limiting is observed in production,
   implement request-interval throttling.

2. **Noise band calibration (10pp).** Chosen by reasoning from dynasty tier structures
   and expected model-market correlation (0.80–0.92). Not empirically validated against
   Dynasty Genius production data. Review after 1–2 months. Acceptance: 40–60% of flags
   `aligned`. Adjust via `NOISE_BAND` config if distribution is off.

3. **`maybeMovingStandardDeviation` as adaptive noise-band widening.** Plausible:
   high-MSTD players deserve a wider noise band because the market itself disagrees
   about their value. Deferred to Phase 9.5. Field is stored now so data is available
   when revisited.

4. **DynastyDataLab pricing and programmatic API.** Source registry says `$4/1000
   requests`; R2 could not independently verify this from public sources. Do not
   include until pricing and API are confirmed.

5. **Source timestamp accuracy.** FC's internal refresh cadence is ~3h. Using HTTP
   fetch time overstates freshness by up to ~12h. Always emit
   `source_timestamp_is_fetch_time_not_publish_time`. Exact staleness is unknowable
   without a `lastUpdated` field in the response.

6. **Pick valuations.** FC and KTC both value rookie picks as tradeable assets. The
   PVO is a per-player object; pick assets require a different object model. Deferred
   to a separate `PickValueOverlay` design in a future phase.

---

## Open Follow-On Work (Not Phase 9)

| Item | Track |
|---|---|
| `maybeMovingStandardDeviation` as adaptive noise-band widener | Phase 9.5 |
| DynastyProcess `values.csv` as parallel expert-consensus overlay | Phase 9.5 |
| Model-market correlation health check (`corr(model_pct_rank, market_pct_rank)`) | Phase 9.5 system health metric |
| KTC integration | Gated on ToS-clean access |
| DynastyDataLab integration | Gated on pricing/API verification |
| `PickValueOverlay` design | Separate design doc |
| TE model diagnosis and promotion | Separate mini-spec |
| RB red-zone feature expansion | Separate mini-spec + backtest gate |
| Frontend card rendering | Phase 12 (last) |
