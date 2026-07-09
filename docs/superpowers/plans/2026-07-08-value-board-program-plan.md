# The Value Board Program — Decision Record + Build Plan

> **Audience:** all three agents (Claude, Codex, Gemini). This is the memorialized, authoritative decision record for the 2026-07-08 Value Board program and the phased build plan we execute against. Governance files (00–04) still govern on any conflict; the CORE THESIS below is David-ratified doctrine.
> **Status:** decisions David-ratified 2026-07-08; execution begins at Phase 0. Uncommitted pending David's word on commit.
> **Related:** thesis + running decisions also in Claude memory `project_product_thesis_value_margin`; composition v2 at `docs/design-comps/2026-07-08-value-board-composition-v2.md` (→ v3 pending Phase-0 fresh data).

---

## 1. THE CORE THESIS (David 2026-07-08 — the core thread of all future thinking)

The product exists to hold a **better, more accurate, more predictive value for each player than the market.** The competitive edge is the **MARGIN** between our per-player value and the market's per-player value, across the whole player universe. "What changed"/trends are secondary and gradual (our values rest on large samples). **Honesty boundary:** we SHOW the margin descriptively; we do NOT claim it proves we're right — unvalidated (Gate-4 deferred, ledger empty, QB weakest); `decision_supported=false`; no buy/sell/underpriced/edge/target; the compounding realized-outcome track record earns the "more accurate" verdict over time.

## 2. RATIFIED DECISIONS (this session)

**Surface model**
- **Hero = a ranked VALUE BOARD** (our value for every player); the **market margin is the killer COLUMN**, not the standalone hero. The board stands on its own where the margin is thin (of ~469 our-valued players, **332 have both lanes / a margin** — the v3.1 static-comp basis; see §4 data facts).
- **Margin readout = paired native positional ranks** ("Model WR8 · Market WR24"), but the comparable magnitude/sort is the **shared percentile delta** from the divergence artifact. Do not subtract raw rank spots across mismatched source populations. The both-lane bar carries magnitude via **gap geometry only** — no intensity/saturation ramp, no green/red.
- **Column header = "DG Model Rank"** (not "our value"); margin column = "vs Market Rank" — so the board reads as *our* ranking, not *the* authoritative ranking.
- **Three tabs:** My Roster (position-grouped, Sleeper-style) · Other Teams (browse each league-mate's roster) · Full Universe (overall rank + position filters).
  - **Full Universe** defaults to the ranked board (v3.1: 332 both-lane rows by xVAR; our-value-only rows carry a "market forming" state); "Show uncomparable" toggle for the no-signal universe.
  - **Free Agents / Rostered** filter on Full Universe. **FA view sorts by OUR value desc** (highest-value FAs at top). **No footnote** — sorting by value (not margin) dissolves the aging-vet liquidity blind spot.
- **Daily Open = the My-Roster daily entry** of the same board + a quiet, market-driven margin-movement note. No action framing ("target/trade" banned).
- **No schema nouns on the surface** (translate `decision_supported=false` → "a descriptive disagreement, not a recommendation", etc.). **Persistent honesty header.** **No general scarcity caveat** (David, sole domain-expert user).

**Data truth (corrected off fresh PVO)**
- Two population numbers, both true (v3.1 is the source of truth for the static comp): **~469 our-valued players** in PVO (`universe_pvo_runtime.json`), of which **332 are "both-lane"** — they have both our xVAR percentile AND a comparable market rank, so they carry a margin (this is the v3.1 board basis; the other ~137 our-valued players render with a "market forming" state, not a fake margin). Fresh divergence artifact: 332 both-lane (WR138/RB89/TE61/QB44), 183 divergent + 149 aligned. David's roster **24 of 27 on-board** (only Braelon Allen, Garrett Wilson, Tank Dell off). The "blank marquee stars" story was a **stale-data illusion** — fresh data values Jeanty/Henderson/Dart/Burden. **Engine-A is NOT the board unlock.** [NOTE: v3 pinned "our value" to DVS; v3.1 corrected it to **xVAR** — the same basis the margin uses — per the Codex+Gemini re-review.]
- Margin is the thin/stale part: divergence artifact last built **June-23**; must be recomputed on fresh market (fc_forward_capture has July-8) + current PVO.

**Deferred (David-ratified defer)**
- **PVO normalization** — rescale DG value from DVS 0–100 to a market-comparable currency (e.g. 0–2000) so roster/market TOTALS compare. Unlocks the **macro roster-equity view** (David wants it; both deferred together).

**Tier / value-band calibration (David correction, 2026-07-08)**
- Fixed percentile labels are **not** the tier system. "Elite" must reflect relative model value, production, age/longevity context, and historical field separation, not an arbitrary `top X%` cutoff.
- Production UI must not render named labels (Generational / Elite / Cornerstone / Starter / Depth) until a tier-calibration artifact exists. Neutral math-first spans are legal: "Top cohort · WR1-7", "Value band · RB18-31".
- The tier-calibration producer must use an **unclamped latent DG value**. Current public DVS is clamped to 0-100 and public xVAR is derived from that clamped value, which compresses the top end for RB/WR/TE. A UI-side threshold over public DVS/xVAR is a defect.
- Market data is overlay-only and cannot influence DG tier boundaries.

## 3. THE OPERATIONAL ROOT CAUSE (found 2026-07-08)

The margin is stale because the **daily margin recompute does not exist as a scheduled job.** Verified:
- Market capture: daily 9:00 (`run_fc_forward_capture.py`) — fresh, June-24→July-8.
- PVO refresh: daily 9:30 (`run_pvo_refresh.py`) — recomputed daily (but off a June-23 source snapshot — secondary, investigate feature freshness).
- What-Changed: daily 9:45 — fresh.
- **Margin (`build_universe_market_divergence.py`): run by NO LaunchAgent — last built June-23.**
A margin-thesis daily-login product REQUIRES the divergence recompute on a daily job. This is the foundation, ahead of surface polish.

## 4. BUILD PLAN (phased; each material step = cockpit TDD: Gemini frames → Codex RED → Claude GREEN → dual-CLEAR → David authorizes)

**Phase 0 — Daily margin recompute (FOUNDATION, build first).**
- 0a. Scope `build_universe_market_divergence.py` + the existing daily-job pattern (`run_pvo_refresh.py` + its LaunchAgent).
- 0b. Produce **fresh margin data now** (recompute against July market + current PVO) — validates the pipeline and gives v3/the comp real current numbers.
- 0c. **Schedule it daily** (LaunchAgent, ~9:40 after PVO 9:30) mirroring the existing jobs. LaunchAgent install is **David-gated** (machine change).
- 0d. Fail-closed + status marker (mirror capture-health discipline); wire into capture-health later (named follow-up).

**Phase 1 — v3 composition on fresh data, then the static comp.**
- Reground v3 on Phase-0 fresh numbers; fold all re-review fixes (header rename, FA sort, universe default, target/trade leak, corrected counts, denominator handling, freshness copy). Cockpit re-review → disposable real-content static comp (hand-joined, inert) → **David's directional preview.**

**Phase 2 — Build the Value Board surface** (only after composition CLEAR + David preview).
- New/extended primitives: PairedRankBar, ValueRow, ScopeSwitcher, PositionGroup, FormingReadCell. The 3 tabs, position-grouped/overall sort, FA/Rostered filter. Full cockpit TDD; No-Verdict enforcement REDs.
- Named tiers are out of Phase 2 unless the tier-calibration artifact is separately specified, RED-tested, built, and cockpit-cleared. Phase 2 may consume neutral cohort spans only if an artifact provides them; otherwise labels remain rank/value-only.

**Phase 3 (deferred) — PVO normalization + macro roster-equity view.**

**Phase 3b (new, David-gated) — Tier calibration producer.**
- Specify and build `tier_calibration_latest.json` (illustrative name) with provenance, method version, current cohort breaks, historical-support state, uncertainty/boundary markers, stale/degraded behavior, and `decision_supported=false`.
- Candidate method: current within-position latent-value segmentation (natural breaks / changepoints / model-selected mixtures) plus historical walk-forward validation against realized Engine B outcomes. Named labels require historical support; otherwise render neutral cohorts only.

**Standing guards (every phase):** No-Verdict / `decision_supported=false`; fresh-data-or-degrade; honesty header; real-shape (build/test against real `*_latest` shapes); scaffolding-hide; cockpit TDD + David authorizes every commit/push/merge/schedule.

## 4b. PHASE-0b FOLLOW-UPS (tracked, not blocking Phase-0 CLEAR)
- **Pair-publish atomicity / mixed-pair read window.** The runner writes latest-then-coverage (each file atomic via temp+rename), but the PAIR is not cross-file atomic — a concurrent reader (e.g. `app/api/routes/players.py`) could observe a fresh latest beside a prior coverage during the write window. Eliminate via a generation pointer, a combined artifact, or a dir-swap. Docstring no longer claims pair-atomicity (Codex v3.1 GREEN re-review, finding #2).
- **Backup bootstrap sequence (operational, David-gated).** `backup_manifest.json` marks `market_divergence_history.db` `required:true` (Codex RED locks it), but the DB doesn't exist until the first refresh. Required order: **commit → run the runner once (creates the DB + fresh margins) → enable/run backup + install the LaunchAgent.** Must precede the next backup run (else `required:true` hard-fails).
- **Wire the status marker into capture-health** (0d) — surface degraded/stale marker states alongside the other daily-job health.
- **Tier-calibration contract patch.** v3.2 changes the tier basis from fixed percentile labels to calibrated value cohorts. Before any production label work, patch the manager-voice roadmap / constitution amendment text so it no longer encodes the old fixed-percentile ladder as implementation law.

## 5. OPEN / TO-VERIFY
- PVO `source_snapshot_captured_at=June-23` — are model features frozen? (Phase 0 investigation.)
- Paired-rank denominator: our pool (RB111) vs FantasyCalc pool (RB107) — normalize to a shared population, or present as source-native + de-emphasize the arithmetic spot-delta (Codex #5). Resolve in v3.
- Exact daily-job time + fail-closed contract (Phase 0 framing).
- Exact tier-calibration artifact path/schema and whether the first implementation should expose neutral cohort spans without named labels.

---
*Execution starts at Phase 0. Hold the whole picture; do not drift from the thesis.*
