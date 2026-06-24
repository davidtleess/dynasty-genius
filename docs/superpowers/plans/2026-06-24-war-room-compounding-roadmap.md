# The War Room — Compounding-Product Roadmap

**Status:** David-authorized plan (2026-06-24). Cockpit-converged (Claude + Codex + Gemini, three independent opportunity analyses → unanimous). This is the standing product roadmap; individual increments still go through normal spec → cockpit dual-CLEAR → David-authorized build.

## Why this exists
David's standing directive: think holistically on **every** decision — a **daily-login** product, pipelines that **refresh as often as fresh data adds value**, and value that **compounds over time** through accumulated learnings, benchmarks, and patterns. This roadmap is the product expression of that principle; the principle itself is now formalized in the operating loop (`02-agent-operating-loop.md` → Cockpit Process → Compounding-product lens).

## The keystone breakthrough — Dual Daily PIT Capture
Today many of our live decision-surface pipelines **overwrite `_latest`** — keeping the current state and discarding history. (Some stores are already append-only — `MarketSnapshotStore`/`fc_snapshots`, backtest runs, model-artifact runs — but the pipelines that drive *daily surface value* are not.) That overwrite habit is the anti-compounding pattern. The fix is a stance, not a feature: **capture daily, never overwrite — both the *market* (FantasyCalc) AND our own *model outputs* (PVO / DVS / xVAR), as parallel append-only point-in-time series.**

Capturing **both sides** daily does three things at once:
1. **Longitudinal surfaces** — market trend *and* model trend, from day one.
2. **Accumulating benchmark** — "what the model said N days ago vs. what happened" — the product's growing edge.
3. **Forward-resolves `MODEL_PIT_INADEQUATE`.** The Gate-4 divergence-edge verdict is blocked precisely because we never archived point-in-time *model* outputs. Start archiving today — each model snapshot stamped with `model_version` / training-cutoff / provenance — and in ~12 months, **if the coverage/power floors are met**, we hold a native vintage model-output series, so the verdict becomes runnable **without** retroactive PIT reconstruction or walk-forward simulation. Accumulation forward-resolves the *missing-vintage-series* problem; it does **not** by itself guarantee the study will be powered or PASS.

This is why the market-only FantasyCalc forward-capture ("A") is reframed as the **first brick of a dual archive**, architected to pair with model-output capture next.

## The governance throughline (inseparable from the principle)
As surfaces gain a **trend / benchmark** dimension, that dimension stays a **descriptive overlay only** — cordoned from Engine A/B decision mechanics, never folded into a buy/sell or composite score, and **visually quarantined until a pre-registered validation (Gate-4) earns its promotion.** A price/value trend is not predictive until proven. `decision_supported=False` and banned-language discipline hold throughout. **"Daily refresh" must never become "daily false certainty."** Where we report posture, we report a **trajectory / structural edge over time**, not a single over-promising number (e.g. no single daily "championship probability"). Rookie/structural updates tie to **hard structural triggers** (depth charts, draft capital, scheme), never beat-reporter hype.

## Ranked roadmap (cockpit-converged)
1. **Dual Daily PIT Capture** (FC market + model PVO/DVS/xVAR) — *foundational; everything else consumes it.* Append-only, survivorship-complete, dated (`snapshot_date` + `retrieved_at`), idempotent same-day writes, conflict hard-fail, raw sidecar for no-Sleeper-ID rows, machine-readable capture report. FC daily cadence is a **documented assumption** with backoff/fail-loud behavior (no public FC rate-limit/ToS entitlement confirmed), not a right.
2. **Daily "What Changed Since Last Login" diff** — highest daily-login value: what moved in roster posture, xVAR, market value, waiver/drop pressure, and league-mate structure since the prior snapshot. Bridges raw capture to daily habit.
3. **Trust Console Track Record** — the model grades its own homework as games are played: rolling accuracy, **honest misses shown raw (no smoothing)**, divergence outcomes, benchmark deltas. Trails capture (depends on stable PIT outputs); credibility compounds with evidence.
4. **League Pulse / Roster Audit Longitudinal — posture trajectory** — daily run against live Sleeper state surfaced as a **structural-edge trajectory over time**, anchored to model caveats / uncertainty and validation status (confidence bands where the primitive actually exists), NOT a single daily win-probability number.

Then, as consumers of the capture (not standalone architecture):
5. **Surface trend overlays, quarantined** — League Pulse / Trade Lab / Roster Audit show market/model/xVAR/posture trend as labeled descriptive overlays only.
6. **Cadence-tuning audit** — measure where daily vs. weekly cadence actually adds signal, in-season vs. off-season; schedule fresh-when-it-matters.
7. **Rookie Board structural refresh** — draft capital / landing spot / depth chart / CFBD integration; seasonal; hard-trigger-gated.
8. **Trade Lab forced-cut vs. live capacity** — evaluate against daily-updated roster capacity, as a consumer of daily Sleeper + PVO capture.

## The flywheel
> Capture both sides daily (#1) → surfaces show trajectory (#5) → daily "what changed" digest (#2) → track record accumulates (#3) → eventually a pre-registered validated verdict → the model improves → repeat. Cadence-tuning (#6) keeps every loop fresh-when-it-matters.

Every item gets **more** valuable the longer the product runs — the definition of compounding.

## Sequencing
Build #1 first (starting with the FC first brick, then the model-output brick). #2 and #3 are the surfaces that turn accumulating data into daily-login value. #6 (cadence audit) is a cheap parallel win. Each increment is its own spec → cockpit dual-CLEAR → David-authorized build. Not-yet-built items here are **proposals David prioritizes**, not commitments.
