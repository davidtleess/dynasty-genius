# BUILD-1 Tier-1 Graduation — Increment 3: Trade Lab (behind the FE mitigation)

**Date:** 2026-07-04 · **Author:** Claude (implementation lead) · **Status:** DRAFT v3 — cockpit dual-CLEAR (Codex R1×7 + R2×3 integrated; Gemini iteration-3 copy confirmed); pending David gate (spec commit + branch + A1 RED)
**Binding precondition being discharged:** increment-2 spec (`2026-07-02-build1-tier1-increment2-design.md`): *Trade Lab stays Tier-0 until its FE ships the mitigation contract — model and market lanes at equal visual weight + explicit copy that the panel computes no trade-outcome delta and evaluates no transaction suitability.*

## 0. Objective and trace

Graduate `trade_lab` to `diagnostic_grade_active_limited` in the Tier-1 registry — the LAST surface of the current graduation set — only after the FE mitigation lands. Gemini's soft-verdict trap (inc-2) governs everything here: a Diagnostic Grade signal on the *trade evaluator* is the maximal badge-as-verdict surface; David mid-negotiation glances for accept/reject and will conflate "pipelines fresh" with "trade validated" unless the mitigation makes the distinction impossible to miss.

## 1. Sequencing (Codex scope ruling)

ONE branch, TWO ordered logical gates: **Task-group A (FE mitigation RED→GREEN) commits BEFORE task-group B (registry row RED→GREEN).** "FE must ship first" = the mitigation commit exists ahead of the registry commit on the branch; a separate merged-to-main PR is not required (David may still split if he wants the mitigation live earlier). Cap-2 boundary respected: this increment graduates exactly one surface.

## 2. The FE mitigation contract (task-group A)

**Mitigation copy (Gemini verbatim draft, David-facing):**
> "This diagnostic panel does not calculate whether you win or lose this trade, and it does not judge if this transaction fits your team. It keeps the model and market views separate and surfaces stale or unavailable data as caveats, so you can evaluate the numbers yourself."

*(Copy iteration history: Gemini's "fresh today" draft overclaimed freshness (Codex R1 #1 — the market route deliberately serves 200-with-caveats); the "available and passing" rewording still state-claimed while rendering on initial load and persisting through degraded lanes (Codex R2 #1); the final copy above is NON-STATE-CLAIMING — true in every panel state, describing only what the panel does. Gemini confirmed at each iteration.)*

- **Placement (Codex R1 #4 — matched to real behavior):** an uncollapsed text block directly below the Trade Lab card header, rendered on INITIAL LOAD with no scroll/hover/expansion; the lane pair (which only renders after a comparison run — `hasRun`) appears AFTER the copy in DOM order. No lane-pair-on-initial-load behavior change is introduced. Enforced as **exact copy** (the health-disclaimer Literal precedent): this is a contract, not styling (Codex d).
- **Equal visual weight (Gemini's four symmetry requirements):** (i) side-by-side columns of identical width on desktop, stacking with identical margins on narrow viewports; (ii) identical typography for xVAR and FantasyCalc numbers (size/weight/color); (iii) NO primary accent on either lane — same neutral tokens, no highlighted background/border; (iv) identical label treatment: "Model Diagnostics (xVAR)" / "Market Price Discovery (FantasyCalc)". The named asymmetry risk: any treatment that quietly re-privileges one lane re-creates the analytical-separation violation.
- **Testability (Codex b + R1 #5 — semantic hooks AND a source guard, because markers alone false-green):** both panels render under a stable `data-testid="trade-lane-pair"` parent; each lane carries `data-visual-weight="equal"`; NO `data-primary`/dominance marker on either. **Real current state: `.dg-lane--model` / `.dg-lane--market` carry DISTINCT colored borders today — the lanes are not equal yet; the GREEN removes lane-specific visual treatment** and a narrow CSS source guard (favors-guard style, scoped to the trade stylesheet) bans model/market-specific border/background/color/font-size/font-weight rules on the lane containers. CSS containment for narrow viewports per the health-card precedent (Gemini seed 5). Copy asserted by exact text on initial load.
- **Verdict-leakage guard (Codex d, extending the favors-guard precedent — scoped to `frontend/src/trade/`, no global linter expansion):** rendered result surfaces contain no "suitable/unsuitable", "recommended", "buy/sell/hold", "winner/loser", "favors", and no blended/combined/average-delta text. The existing favors-guard tests remain green untouched.

## 3. The registry row (task-group B — the inc-1/2 pattern exactly)

- `trade_lab` → `diagnostic_grade_active_limited` with **live preconditions = the two EXISTING closed-set ids only: `model_provenance_ok` + `capture_health_ok`** (Codex R1 #2: `live_preconditions` is a closed id set; extending it is a model/schema/adapter change this increment does not make). The model-lane, market-lane, and assets routes (`/api/trade/reconcile/*`, `/api/trade/assets`) are pinned as **route_ids/evidence** per the inc-1/2 pattern. Either live precondition degraded → `preconditions_degraded`, never a clean grade (subsumes Gemini seed 4 — degradation flows from the registry mechanism; no new Trade-Lab-FE-to-`/api/health` coupling).
- **The FE-mitigation linkage (Codex R1 #3 — ownership split, no cross-stack grep):** the FE VITEST owns the exact copy, placement, and data-* DOM contract; the registry row's **evidence path = the FE test file**, with its expectation string carrying the versioned contract id `trade_lab_fe_mitigation_v1` (Codex R2 #2 — compatible with the existing evidence-path/runtime existence model); the Python registry RED asserts the evidence path exists and that the expectation string or the referenced FE test contains the token — never grepping component implementation. Backend readiness stays decoupled from FE structure while the binding precondition remains enforced in code.
- RED rows (Codex R1 + #7, the full inc-1/2 pattern): `trade_lab` absent before GREEN; **`ratified_date: null` → `not_graduated`/awaiting-David (the structural activation block), David-stamped date → `_limited`**; active_limited only when preconditions pass AND the mitigation evidence is present; each single-precondition degradation case; cap-2 hold behavior unchanged; **post-GREEN registry surface set pinned = the existing three graduated surfaces UNCHANGED + `trade_lab`**.
- Preconditions live-smoke style but fixture/DI in committed tests — no gitignored-artifact dependency (CI-independence).

## 4. Overclaim cordon (Gemini part 5)

Wherever the grade surfaces (the tier-readiness API today), the wording stays "Diagnostic Grade" with the dormancy/limitation disclosed — never "Validated" as a standalone label. **Explicitly OUT OF SCOPE: no Tier-1 badge renders inside the Trade Lab FE in this increment** (no badge UI exists for the other graduated surfaces either; a future badge increment would be separately framed and inherits Gemini's badge-trap seeds). `decision_supported=false` unchanged everywhere; graduation changes NOTHING about decision authority.

## 5. Falsification seeds

1. Mitigation copy renders on INITIAL LOAD, exact text, no scroll/hover/expansion; AFTER a comparison run, the lane-pair parent renders after the copy in DOM order (Codex R2 #3 — split to match real hasRun behavior); narrow-viewport containment per the health-card precedent.
2. Lane-pair symmetry markers present; either lane carrying a dominance marker FAILS; the pair renders under the stable parent.
3. Verdict-leakage scan over rendered trade result surfaces (scoped guard) — including the blended-delta ban.
4. Registry: `trade_lab` reports `preconditions_degraded` when EITHER live precondition (`model_provenance_ok`/`capture_health_ok`) degrades; route_ids pinned as evidence; never a clean grade with a degraded precondition.
5. Registry RED fails if the mitigation evidence entry (versioned contract id → FE test file containing the token) is absent — the binding-precondition tripwire, ownership-split per §3.
6. Existing favors-guard + lanes + forced-cut-range suites stay green (no regression of the PR #92/#95 contracts).
7. Determinism + fail-closed states of the existing Trade Lab state machine untouched (idle/ready/unavailable per lane).
8. Banned-language gate green; **guard scoping pinned (Codex R1 #6): the verdict-leakage scan covers RESULT surfaces only, or strips exactly the mitigation-disclaimer node before scanning** — the copy contains "win" and existing Trade Lab tests use broad body scans in places, so the exemption is explicit, node-exact, and tested (a broad-scan false-fail on the disclaimer is itself a RED case).

## 6. Task plan

- **A1 (Codex RED):** FE mitigation contract — copy/placement/symmetry-marker/leakage-guard tests over the existing Trade Lab components. **A2 (Claude GREEN):** copy block + layout/marker changes + guard extension.
- **B1 (Codex RED):** registry row + preconditions + the FE-linkage tripwire. **B2 (Claude GREEN):** registry entry + adapter wiring per the inc-1/2 pattern.
- **T-final:** full closeout ENFORCE PASS → dual-CLEAR → David gates push/PR → CI-green merge → zero-divergence → close.

Branch (on David's word): `feature/build1-tier1-increment3`.
