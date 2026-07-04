# League Pulse Tier-1 Graduation — the reopened hold, discharged the Trade Lab way

**Date:** 2026-07-04 · **Author:** Claude (implementation lead) · **Status:** DRAFT v2 — Codex R1 ×4 integrated (exported-constant coupling; FE-mirrored weights, no API change; intent-certainty guard scoping; both exact-set tripwires named); Gemini copy-correction ACCEPTED ("a disclaimer that under-describes its own basis is itself an overclaim"); pending round-2
**Reopening authority:** David's explicit word, 2026-07-04 ("reopen League Pulse graduation") — the inc-2 hold-indefinitely ruling is lifted by the only authority that could lift it. The reopened question got a real answer, not automatic reversal: Gemini restated the hold's grounds and ruled graduation defensible ONLY under the mitigation-first pattern PR #119 proved.

## 0. The hold and why it can lift

The inc-2 grounds, verbatim: *"opponent-posture heuristics are narrative-driven; certifying them implies false mathematical certainty about opponent intent."* Another manager's strategy, targets, and valuations are unobservable; a Diagnostic Grade near a posture label reads as "the system validated this manager's intent." What changed: the Trade Lab mitigation-first pattern (inc-3) proved a narrative-adjacent surface graduates safely when the defusing contract ships FIRST and is tripwired in the registry. Same shape here, or no graduation.

## 1. The FE mitigation contract (task-group A — ships before any registry work)

**Mitigation copy (Gemini draft, CORRECTED to the true heuristic basis — Codex verified the actual posture code, and the original "roster age and projected scoring" wording under-described it, the exact overclaim class the Trade Lab copy needed three iterations to purge):**
> "Opponent posture labels (contender, rebuilding, and similar) are mathematical heuristics computed from four weighted roster signals — starter-weighted model value, roster age profile, early draft-pick balance, and taxi/development stash — with the weights disclosed in this panel's basis. They do not represent the actual trade intent, active strategy, or internal valuations of other league managers, which are unobservable."

- **Placement:** uncollapsed block directly below the League Pulse header, above all posture/league panels, visible on initial load with no scroll/hover/expansion; exact-copy enforced (the Literal precedent). The four weights surface as the disclosed basis alongside — **source of truth (Codex R1 #1/#2): A2 includes a behavior-preserving refactor exporting `POSTURE_SIGNAL_WEIGHTS = {starter_weighted_model_value: 0.60, roster_age_profile: 0.20, early_draft_pick_balance: 0.15, taxi_development_stash: 0.05}` in `team_posture.py`** (the weights are inline expressions today — a named constant makes the coupling assertable without brittle arithmetic-scanning); **the FE renders registered constants mirrored from that export — NO API/OpenAPI change** (the pulse DTO exposes component values, not weights; API-derived disclosure would break the FE-only scope).
- **Posture neutrality:** all posture labels render in neutral grayscale, identical type treatment, NO color coding (no green-contender/red-rebuilder), no accented/primary axis when heuristics are compared. Codex's current-state read: the shipped surface is mostly-neutral already — the RED targets the ABSENT contract (copy, markers, guards), not a styling teardown; neutrality gets pinned so it cannot regress.
- **Testability (the inc-3 kit):** stable data markers on posture elements (no dominance markers), a scoped CSS/source guard against posture-color rules, node-exact disclaimer exemption in any text scans, narrow-viewport containment. The market-overlay quarantine (the existing "Descriptive market signal, not a validated edge" banner) stays byte-stable and un-over-accented.
- Existing League Pulse suites stay green; no backend/contract change in group A.

## 2. The registry row (task-group B — the inc-3 pattern verbatim)

- `league_pulse` → `tier_1_candidate` with live preconditions = the two closed-set ids ONLY (`model_provenance_ok`, `capture_health_ok`); route evidence `/api/league/pulse` (mounted, OpenAPI-verified); producer artifacts = the three runtime inputs (`team_posture_latest.json`, `team_value_matrix_latest.json`, `league_opportunity_latest.json`).
- **Mitigation tripwire:** evidence path = the A-group FE test file; expectation carries a versioned `league_pulse_fe_mitigation_v1` id; the registry RED asserts path + token — activation impossible without the shipped contract.
- **Ratification pattern:** `ratified_by: "David"`, `ratified_date: null` until David stamps (the structural block); exact-set registry tests grow four → five in BOTH real-registry tripwires — the T4 post-GREEN surface set AND the T5 ratified-surface exact set (Codex R1 #4: naming both prevents the inc-3 closeout red from repeating).
- Existing four graduated surfaces byte-unchanged; post-GREEN set pinned.

## 3. Falsification seeds

1. Copy renders on initial load, exact text, above all panels; lane/panel DOM order pinned; narrow-viewport containment.
2. The copy's basis claim is TRUE via the exported `POSTURE_SIGNAL_WEIGHTS` constant: the RED source-reads the constant and asserts the FE basis text/TS mirror matches it (a heuristic change that breaks the copy's truthfulness fails the RED — copy and code contractually coupled, refactor-tolerant).
3. Posture-neutrality markers present; a posture-colored CSS rule fails the scoped guard; the market quarantine banner byte-stable.
4. Registry: absent before GREEN; `ratified_date: null` → not-graduated; stamped → `_limited`; each live-precondition degradation case; the mitigation-token tripwire; four existing surfaces unchanged; exact-set five.
5. Guard scoping (Codex R1 #3): the leakage guard targets INTENT/STRATEGY-CERTAINTY copy — never the posture enum words (`contender`/`rebuilding` are legitimate DTO values, labels, and disclaimer words; exempt exact copy, posture labels, partner evidence). The CSS guard targets posture-COLOR semantics instead: posture selectors paired with color/background/border or tone-implying class names fail.
6. Determinism; fixture-only committed tests; no gitignored-artifact dependencies.

## 4. Task plan

A1 (Codex RED: FE mitigation) → A2 (Claude GREEN) → B1 (Codex RED: registry row) → B2 (Claude GREEN + real-route smoke) → closeout → dual-CLEAR → David gates ship + the ratification stamp. Branch: `feature/league-pulse-graduation`.
