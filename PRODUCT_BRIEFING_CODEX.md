# Dynasty Genius: Current Product Briefing

## What It Is

Dynasty Genius is a local web application for one Sleeper dynasty football league. It combines a league and player snapshot with locally generated model artifacts and a market-data overlay. The application is a FastAPI service that serves a built React single-page application and JSON endpoints under `/api`.

The user-facing surfaces present roster, player, trade-package, league-context, and model-validation data. Current primary-surface copy labels the outputs as descriptive rather than decision-grade.

## Screens And Views

The application starts on **Daily What-Changed**. Main navigation and the command palette expose these views:

| View | Data shown | Available interaction | Current observed state |
| --- | --- | --- | --- |
| Daily What-Changed | Model-output and market-price changes since the previous snapshot; separate roster and league movement lists; entered and exited players; roster-context sections; feed diagnostics; receipts. | Expand each movement list from its top rows to all rows. | The July 14 local response returned `200`, with 51 changes and a model-output section reporting no player movement. Its movement series rendered as pending. |
| Roster Audit | Roster player table with position, team, age, model grade/status, DVS, age signal, signal completeness, caveat count, and QB context cards. | Filter positions and player scope; sort by default, age-cliff risk, age, completeness, or xVAR; group by position, depreciation band, or xVAR bracket; expand a player row. | The endpoint returned `200` and `status: active`. The rendered roster contains both modeled/prospect records and `PRE_MODEL` records. |
| Trade Lab | Searchable player and draft-pick asset catalog; assets sent and received; optional counterparty roster; separate model and FantasyCalc market reconciliation lanes; player inspector. | Search with three or more characters, choose the active give/receive side, add assets, choose a counterparty roster, run a comparison, and open the inspector. | Search and both reconciliation POSTs returned `200` during review. The two lanes can return different scales, availability, caveats, and transaction-rule states. |
| Roster Capacity | Roster capacity totals, active-slot overflow, capacity-cut count, cut-exposure-ranked candidates, xVAR, cumulative and marginal value-at-risk ranges, and position replacement ranges. | Read-only. | The endpoint returned `200` with `status: ok`; the observed render included unavailable replacement ranges for many positions. |
| League Pulse | League artifact timestamp/status, partner rankings, team postures, team-value overview, model-native opportunity cards, and market-overlay cards. | Read-only. | The endpoint returned `200` with `status: degraded`; the view rendered the available tables and cards. |
| Model Trust | Position tabs for QB, RB, WR, and TE; validation gates, fold metrics, uncertainty, model-card use/caveat text, and provenance. | Switch position tabs. | The QB tab loaded from two `200` endpoints. The displayed trust data marks `decision_supported = false`. |
| Accuracy Tracker | Realized-outcome settlement status, maturity, cohort metrics, tracking rows, excluded counts, and input-fidelity content when supplied. | Read-only. | The endpoint returned `200` with `status: inactive`, `settlement_status: unsettled`, and no cohort metrics or tracking rows. |
| Rookie Board | A parked-state card. | Navigation only. | No executable React rookie data view is mounted. |
| Waiver Radar | A parked-state card. | Navigation only. | No executable waiver data view is mounted. |
| Research Assistant | A parked-state card. | Navigation only. | No executable research-assistant view is mounted. |
| Project Tracker | Internal phase records returned by the project-plan API. | Refresh and expand phase records. | The endpoint returned `200`; the rendered data timestamp was June 24, 2026. |

There is also a URL-only developer capture view at `?surface=asset-primitive-capture`. It renders fixed examples of identity, spread-bar, and metric-cell components. It is absent from the navigation rail and command palette.

Global application elements include:

- A keyboard command palette, opened with `Cmd/Ctrl+K`, with text filtering, arrow-key navigation, Enter selection, and Escape dismissal.
- A system-status control. During review it displayed `Status unavailable`; `/api/health` returned `503` with `system_health_unavailable` while feature endpoints continued to return data.
- A player inspector. Selecting a trade asset opens a compact player preview with model and market availability, evidence counts, and controls for a full evidence card. The full card shows player identity, model lane, market lane, divergence, drivers, risks, counterargument, and caveats.

Client-side view selection uses the `surface` query parameter. Examples include `?surface=roster-audit`, `?surface=trade-lab`, and `?surface=league-pulse`; an absent or invalid value opens Daily What-Changed.

## Users And Current Workflows

The current product is used by a dynasty fantasy-football manager operating a Sleeper league.

- **Daily review:** open Daily What-Changed, compare the roster movement list with league movement, expand the lists, and inspect the current roster-context blocks.
- **Roster evaluation:** filter, sort, group, and expand roster rows in Roster Audit; view capacity exposure and replacement ranges in Roster Capacity.
- **Trade-package analysis:** search the tradeable-asset catalog, build sent and received packages, optionally identify a counterparty roster, run the separate model and market reconciliations, and inspect an included player.
- **League scan:** read opponent posture, partner-ranking, team-value, and opportunity data in League Pulse.
- **Model and outcome inspection:** switch model positions in Model Trust and open Accuracy Tracker. The current scorecard is inactive.

The SPA exposes no live rookie-board, waiver-radar, or research-assistant workflow. It does not submit Sleeper transactions or alter a Sleeper roster.

## Data Boundaries

### Sleeper Integration

`app/data/sleeper.py` makes unauthenticated HTTP GET requests to these Sleeper API paths:

- `/user/{username}` and `/user/{user_id}/leagues/nfl/{season}`
- `/league/{league_id}`, `/league/{league_id}/rosters`, `/league/{league_id}/users`, `/league/{league_id}/traded_picks`, and `/league/{league_id}/drafts`
- `/draft/{draft_id}` and `/draft/{draft_id}/picks`
- `/players/nfl` and `/state/nfl`

The snapshot builder retains player identity fields (`full_name`, `position`, `team`, `age`, `years_exp`, and Sleeper status); league settings, scoring settings, and roster positions; league users; roster membership, starters, taxi, and reserve status; current draft data; NFL state; and traded-pick ownership data. It reconstructs future-pick ownership from the league roster IDs and Sleeper traded-pick records. Numerical future-pick xVAR is calculated locally from `app/data/valuation/draft_pick_value_curve_v1.json`.

The normalized Sleeper snapshot contains no model value, DVS, xVAR, external market value, market delta, model-versus-market divergence, usage statistic, or realized-outcome metric. This integration does not call a Sleeper transactions endpoint; past player transactions are not included in the snapshot. The default league ID is embedded in the snapshot script and can be overridden with `DYNASTY_SLEEPER_LEAGUE_ID`; `DYNASTY_SLEEPER_DRAFT_ID` can override draft selection.

### Local Artifacts And API Behavior

Feature routes read local artifacts under `app/data` and validate their response shape in the React client with generated Zod schemas. A non-`200` response or a schema mismatch produces a loading, unavailable, or parse-error state rather than an unvalidated data table.

The current Trade Lab labels its market lane as a FantasyCalc market snapshot. Its model and market reconciliations are separate API calls:

- `POST /api/trade/reconcile` for model payloads
- `POST /api/trade/reconcile/market` for market references

The API also contains endpoints for rookie scoring, Engine B scores, player details, system provenance, capture health, tier readiness, and health. Not every API endpoint has an SPA navigation view.

## Front-End Stack And Local Run

The frontend is a Vite 8 single-page application written in TypeScript 6 and React 19. It uses Vanilla CSS, Zod 4 response validation, Vitest 4, Playwright, Biome, and generated OpenAPI TypeScript definitions. The checked-in Node version is `24.15.0`; the package manager field specifies npm `11.14.0`.

The backend uses FastAPI and Uvicorn. The checked-in Python tooling targets Python `3.14`; the active environment reported Python `3.14.4`.

From a fresh terminal at the repository root:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

cd frontend
npm ci
npm run build
cd ..

.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. The built frontend calls relative `/api/...` URLs on the same origin.

Frontend verification commands:

```bash
cd frontend
npm run gate
npm run visual:smoke
```

The frontend package has no `npm run dev` script. `npm run preview` serves the built Vite files on port `4173`; it does not serve the FastAPI API routes.

## Hard Technical Constraints

- **Python version:** the repository’s CI workflow, Ruff target, virtual environment, and current dependencies use Python 3.14. Python 3.9 cannot parse source files that use PEP 604 union annotations such as `dict[str, Any] | None`.
- **Built SPA requirement:** `app/main.py` only mounts the SPA fallback when `frontend/dist/index.html` exists. Without a frontend build, FastAPI still exposes API routes but does not register the SPA fallback.
- **Same-origin API requirement:** frontend fetches use paths such as `/api/roster/audit` and `/api/trade/reconcile`. The Vite configuration contains no development proxy.
- **Artifact availability:** roster, capacity, pulse, trust, scorecard, trade, and daily endpoints read local artifact files. Missing, stale, malformed, or incompatible artifacts produce endpoint errors or frontend unavailable/parse-error states.
- **Optional headshots:** `app/main.py` mounts `/assets/headshots` only when `app/data/assets/headshots` exists. Missing headshot files produce the frontend initials fallback. Review requests included headshot `404` responses.
- **External data availability:** the Sleeper snapshot process depends on the public Sleeper endpoints listed above. The source client calls `response.raise_for_status()` for each request.

## Current State At Review Time

The following local browser and endpoint checks were run on July 14, 2026:

- `GET /api/league/what-changed`, `/api/roster/audit`, `/api/roster/capacity`, `/api/league/pulse`, `/api/trust-surface/QB`, `/api/trust-surface/QB/model-card`, `/api/realized-outcome/scorecard`, `/api/internal/project-plan`, `/api/system/model-provenance`, and `/api/system/capture-health` returned `200`.
- `GET /api/health` returned `503` with `{"error":"system_health_unavailable","message":"system health configuration unavailable","decision_supported":false}`. The shell status control displayed `Status unavailable`.
- Daily What-Changed, Roster Audit, Roster Capacity, League Pulse, Model Trust, Accuracy Tracker, Project Tracker, Trade asset search, and both Trade Lab reconciliation calls rendered in the local browser.
- Accuracy Tracker is inactive. The response contains no cohort metrics or tracking rows.
- Rookie Board, Waiver Radar, and Research Assistant are parked views rather than data surfaces.
- The current Daily What-Changed response rendered a pending movement series.
- `npm run build` completed successfully in `frontend` during this review.
