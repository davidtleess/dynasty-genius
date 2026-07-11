---
name: metrics-review
description: Review Dynasty Genius operational and model metrics descriptively. Use for a capture-health / freshness read, a model-provenance drift check, a realized-outcome accrual review, or a margin/divergence-trend read. Metrics describe; they never prescribe. Not product analytics (there is one user) — this is model and data-reliability telemetry.
argument-hint: "<focus: capture-health | provenance | realized-outcome | margin/divergence>"
---

# Metrics review (descriptive only)

> Sources are DG's own telemetry surfaces — see [SOURCES.md](../../SOURCES.md). This is **not** product analytics (adoption/retention/NPS are meaningless for a single-user tool). It reviews whether the data is fresh and honest and whether the model is behaving — and it does so **descriptively, never as a verdict.**

The No-Verdict Line is the hard constraint here, more than in any other skill: a metrics review that drifts into "so you should trade X" or "the model has an edge" has broken DG's core discipline. Report what the numbers *are* and what *changed*; stop before the recommendation.

## What DG actually measures

### Operational reliability (is the data honest?)
- **Capture-health** (`GET /api/system/capture-health`) — PIT store freshness, gaps (laptop-sleep holes), streak, staleness grace windows, season-aware thresholds. "Silence is not success" — an absent/stale marker is a finding, not a pass.
- **Model-provenance** (`GET /api/system/model-provenance`) — byte-drift (`hash_mismatch`/`local_override`), fresh-clone absence, pointer integrity. Nothing silently serves unapproved bytes.
- **Report freshness / trust** (`GET /api/health`) — per-artifact status + freshness gates; `producer_failed` and degraded rollups by tier.
- **Backup** — `app/data/ops/backup_status_latest.json`: `status`, `sha256_verified` (earned by the restore drill, not implied), `failures`.

### Model behavior (is the model behaving?)
- **DVS / PVO / xVAR distributions** — value scale, top-end compression (the known DVS-100 ceiling), positional spread. Describe shape and drift; flag compression as a *calibration observation*, not a fix mandate.
- **Margin / divergence trend** — the per-player gap between DG value and market value over the forward-capture history. **Descriptive and explicitly unvalidated** — the divergence edge is a hypothesis gated on accrual (~Dec), not a proven signal. Never present it as "the market is wrong."
- **Realized-outcome accrual** — weekly scoring vs. real NFL outcomes against **frozen** predictions. Off-season: honestly empty/inactive. In-season (~Sept+): calibration begins to accrue (ECE/Brier/AUC where n supports it).

## Workflow

1. **Scope the read** — pick a focus (don't dump everything). State the as-of time and the source.
2. **Pull the numbers** — from the live routes / stores / markers. Quote real values; do not synthesize.
3. **Trend, don't just snapshot** — what changed vs. the prior read, and over what window. Use the forward-capture history where it exists.
4. **Grade the evidence** — is this a live-validated number, a provisional read, or accrual-gated (not yet earned)? Say which. The validation ladder never flips `decision_supported`.
5. **Surface findings, not directives** — "margin on the RB cohort widened; divergence remains unvalidated" is a finding. "Buy the RB cohort" is a No-Verdict breach.

## Cadences

- **Daily** — the market/margin tape and capture-health (the "did model & market move on my players overnight?" read). In the off-season the model is frozen day-to-day; the tape is a *market* tape against a frozen model anchor — say so.
- **Weekly** — provenance drift, roster-capacity/opportunity artifacts, backup marker.
- **Accrual milestones** — ~Sept: realized-outcome calibration starts; ~Dec: Gate-4 / divergence track records become buildable. Nothing accelerates these but time.

## Hard No-Verdict rules

- Metrics are **descriptive**. `decision_supported=false`. No buy/sell/hold/start/bench, no nominated targets, no "edge" claim.
- The margin is a **hypothesis**, not a proven edge — frame every divergence read that way.
- Respect the **frozen-model constitution** — never retroactively rewrite what a frozen model said; realized-outcome grades frozen predictions.
- Don't promise **outcome-validated** tiers/claims before outcomes accrue. "Ranks well; calibration unproven at n≈X" is the honest shape.
- Off-season byte-identical model output is expected, not a bug — the model *cannot* diverge overnight when frozen.

## Output

A scorecard-style read (short table of numbers + a prose "what changed / what's unproven"). Findings and observations only — route any *action* implied by the numbers through a spec (`dg-pm:write-spec`) and the cockpit, David-authorized.

## Tips

- If you're about to write a recommendation, stop and hand it to a spec instead — the review's job ends at the honest finding.
- Distinguish "the producer failed" (operational) from "the value moved" (model) — they degrade different things.
- An empty realized-outcome scorecard in the off-season is a healthy 200, not a gap. Don't alarm.
