# Dynasty Genius AI Context

Use this file as the first-stop context for any GPT/Codex/Claude session working on Dynasty Genius.

## Project Identity

Dynasty Genius is a personal dynasty fantasy football intelligence app for David.

It is not a public SaaS product. Do not add authentication, multi-user account systems, billing, roles, or enterprise abstractions unless David explicitly asks.

The core mission is to build a continuous dynasty valuation engine for every relevant NFL player at QB, RB, WR, and TE. The system should project future dynasty value for:

- David's roster
- Incoming rookies
- Waiver players
- Players on opponent rosters

The competitive advantage should come from:

- A high hit rate on incoming rookies using pre-NFL signal quality
- More accurate predictive values for active NFL players across the league

Primary working principle: never optimize for short-term feature completion over long-term valuation accuracy.

## Current Stack

- Backend: FastAPI, Python
- Data/modeling: `nfl_data_py`, scikit-learn, pickle model artifacts
- HTTP/data collection: `httpx`, `requests`, BeautifulSoup, Playwright
- Configuration: `python-dotenv`
- Current app entrypoint: `app/main.py`

Important structure:

- `app/api/` route handlers
- `app/services/` business logic
- `app/data/` external API clients, scrapers, pipelines, model artifacts
- `app/models/` Pydantic models, when present
- `docs/` canonical planning and architecture docs

## Data Sources

Approved or intended data sources:

- Sleeper API: free, no auth, username-based; primary roster and league source
- PlayerProfiler: subscriber scraping; dominator rating, athleticism, production context
- PFF: subscriber scraping; snap counts, routes, grades, YPRR
- KTC / KeepTradeCut: market value scraping; deferred for the current sprint
- RAS / ras.football: Relative Athletic Score; approved for ingestion
- Pro Football Reference: historical stats and career data
- `nfl_data_py`: NFL usage, production, and historical modeling features

Scraping should be treated as fragile. Prefer clear adapters, cached/raw snapshots where useful, and explicit validation over hidden assumptions.

## Product Direction

The roadmap has moved from a narrow rookie evaluator into a unified player valuation system.

Current architecture direction:

- Engine A: Incoming Rookie Forecast
- Engine B: Active NFL Player Forecast
- Unified Dynasty Value Layer

### Engine A: Incoming Rookie Forecast

Purpose: pre-draft and rookie-draft decisions.

Input class: pre-NFL and draft-time features only.

Example features:

- Draft capital
- Age at entry
- RAS
- College production metrics
- Position-specific prospect indicators

Output: long-horizon projection at player entry.

### Engine B: Active NFL Player Forecast

Purpose: ongoing valuation for current NFL players.

Input class: NFL usage, efficiency, time-series production, market context, and aging context.

Example features:

- Target share
- Air yards share
- Route participation
- Snap share
- EPA-based metrics
- YPRR and efficiency
- Age curve state
- Multi-year production trends

Output: forward dynasty projection for active players.

### Unified Dynasty Value Layer

Both engines should feed one comparable dynasty value scale.

Required output fields should converge toward:

- `dynasty_value_score`
- `confidence_band` or uncertainty range
- `projection_1y`
- `projection_2y`
- `projection_3y`

This shared value layer should eventually power:

- League-wide rankings
- Roster hold/sell/buy signals
- Waiver pickup prioritization
- Trade package comparison
- Rookie board and rookie draft decisions

## Current Implementation Snapshot

Existing FastAPI app:

- `app/main.py` creates the FastAPI app and mounts rookie, roster, and trade routes under `/api`.
- `app/services/rookie_evaluator.py` loads one pickled model per position from `app/data/models` and scores prospects using `pick`, `round`, and `age`.
- `app/services/roster_auditor.py` reads David's Sleeper roster using hardcoded username, league name, and season, then flags players around age cliffs.
- `app/services/trade_analyzer.py` currently values picks with static round values and values players by reusing the rookie evaluator plus an age discount.
- `app/data/pipeline/train_models.py` trains current model artifacts.

Known current limitations:

- Some service code still has hardcoded David/league/season assumptions.
- Current rookie scoring is early-stage and uses only draft pick, round, and age.
- Trade analysis is internal and preliminary; do not treat it as a validated market-value engine.
- The active-player valuation engine is not fully represented yet.
- The unified value schema is a target architecture, not fully implemented.
- Validation harnesses and quality gates need to be added before expanding product surfaces.

## Current Sprint Priorities

Prioritize these before frontend expansion:

1. Stabilize configuration and remove hardcoded league/user settings from services.
2. Expand training features from available `nfl_data_py` Year 1 signals.
3. Add RAS ingestion and map RAS into the rookie feature set.
4. Build holdout validation and sanity-check suites with pass/fail gates by position.
5. Add model versioning, artifact metadata, and saved metrics so model outputs are traceable.

Definition of done for the next iteration:

- The code and docs clearly represent two modeling tracks: rookie forecast and active-player forecast.
- Each training run emits a validation report.
- TE model quality improves to non-negative explanatory signal on agreed validation.
- Model artifacts are versioned and not silently overwritten.
- Trade evaluator remains internal but starts reading from the shared valuation direction.

## Modeling Principles

- Prefer position-stratified modeling for QB, RB, WR, and TE.
- Do not invent manual feature weights unless they are explicitly part of a documented baseline or heuristic.
- Preserve bust outcomes as real zero outcomes; do not drop them as nulls.
- Separate pre-NFL rookie features from active NFL usage features.
- Use validation gates before exposing model outputs downstream.
- Treat confidence and uncertainty as first-class product outputs.
- Prefer reproducibility over one-off notebook-style experimentation.

## Engineering Principles

- Keep the system simple because it is for one user.
- Prefer small, inspectable services and pipelines over premature frameworks.
- Keep data source adapters isolated from model logic.
- Use structured config instead of hardcoded usernames, league names, seasons, paths, or model settings.
- Add tests or validation scripts where model behavior, scoring, or external-data parsing can silently drift.
- Avoid broad refactors that do not directly support the valuation mission.

## GitHub Status

David does not have GitHub set up yet. Do not assume remote branches, pull requests, or GitHub Actions exist.

Until GitHub is configured, use local git safely:

- Check `git status` before making major changes.
- Create local branches for separate lines of work if git is initialized.
- Do not run destructive git commands without explicit permission.
- Keep work split into small, reviewable local changes.

## Agent Review Prompt

Use this prompt when asking an agent to review the existing work:

```text
Read AI_CONTEXT.md, README.md, docs/, and the current app code.

Review Dynasty Genius against its mission: a unified dynasty valuation engine for rookies and active NFL players.

Focus on:
- correctness of current dynasty-football logic
- alignment with the two-engine architecture
- model/data leakage risks
- validation and reproducibility gaps
- scraper/data-source reliability risks
- code simplicity for a single-user app

Return findings in this order:
1. Critical bugs or misleading outputs
2. Architecture gaps vs the mission
3. Model/data quality risks
4. Quick wins
5. Recommended next implementation sequence

Do not optimize for frontend polish before model credibility.
```

## Parallel Agent Session Prompts

### Session A: Modeling and Backend

```text
Read AI_CONTEXT.md, docs/model-architecture.md, docs/next-sprint.md, and the backend code.

Act as the modeling/backend reviewer for Dynasty Genius.

Goal: design the next backend implementation steps for the two-engine valuation architecture.

Focus on:
- Engine A rookie forecast inputs, training, validation, and artifact versioning
- Engine B active player forecast inputs and service boundaries
- unified value schema
- configuration cleanup
- data pipeline reliability

Return:
- the top backend/modeling gaps
- a small implementation plan with dependencies
- files likely needing changes
- tests or validation checks required
```

### Session B: Product and Dynasty Strategy

```text
Read AI_CONTEXT.md, docs/mission.md, docs/roadmap.md, and the current API/service code.

Act as the dynasty-football product strategist for Dynasty Genius.

Goal: ensure the system being built will actually help David make better dynasty decisions.

Focus on:
- rookie draft board usefulness
- roster hold/sell/buy recommendations
- trade and waiver decision surfaces
- explanation quality for recommendations
- confidence/uncertainty presentation
- where market data should and should not influence model output

Return:
- highest-value product decisions
- misleading or premature product surfaces to avoid
- recommended output fields for users
- the next three product features after model validation improves
```

## Synthesis Prompt

Use this after Session A and Session B complete:

```text
Read AI_CONTEXT.md plus the outputs from Session A and Session B.

Synthesize both into one prioritized Dynasty Genius build plan.

Return:
- the next 5 implementation tasks in order
- why each task comes before the next
- dependencies and risks
- the validation gate that proves each task worked
- what should explicitly be deferred
```
