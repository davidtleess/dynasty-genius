# Conductor Track: 01-opponent-fragility-lens

**Status:** IN_PROGRESS  
**Owner:** Gemini (Maestro)  
**Phase:** 2 (Identity & League Context Foundation) — feature spike  
**Objective:** Surface an Opponent Fragility Lens — a pre-model context surface that flags league-mate biological debt, pick-liquidity constraints, and steel-manned counter-arguments without issuing trade instructions.

---

## 1. Specify (Requirements)

- **Input:** `resources/david_league_context.json` (David's data) + `resources/mock_league_rosters.json` (Opponent data).
- **Metric:** Fragility Index (Biological Debt Ratio + Pick Liquidity).
- **Surface:** An opponent fragility table showing the highest biological debt and liquidity-pressure signals in the league.
- **Guardrail:** Zero KTC leakage. Logic must use internal Engine A/B scores. No verdict, action, buy, sell, or hold language in any output.
- **Decision posture:** `decision_supported` remains `false` until live rosters, pick inventory, market overlay separation, and counter-arguments are verified.

---

## 2. Plan (Delegation)

### [ ] Task 1: League-Wide Fragility Audit (Codex)
- **Goal:** Score all 12 teams in the league.
- **Output:** `resources/league_fragility_report.json`.

### [ ] Task 2: Counter-Argument Engine (Claude)
- **Goal:** Generate mandatory steel-manned counter-arguments wired into each PVO.
- **Output:** `src/dynasty_genius/decision_logic/counter_arguments.py`.

### [ ] Task 3: Liquidity Tracking (Genie)
- **Goal:** Schema for opponent draft picks.
- **Output:** `resources/sql/create_gold_opponent_picks.sql`.

---

## 3. Implement (Milestones)

- [x] Milestone 1: Reconcile mock opponent rosters.
- [x] Milestone 2: Execute Fragility Audit logic.
- [x] Milestone 3: Integrate Counter-Arguments into the Roster Audit PVO.
- [ ] Milestone 4: Opponent fragility visualization in dashboard (signals only).
- [ ] Milestone 5: Replace mock league rosters with live Sleeper snapshot.

---

## 4. Validate (Gates)

- [x] Pre-commit hooks pass.
- [x] `league_fragility_report.json` contains no recommendation/verdict/action fields.
- [ ] Logic verification script returns neutral fragility signals with required-before-action caveats.
- [ ] No market data leakage detected.
- [ ] David reviews mock-to-live replacement before any opponent signal surfaces in dashboard.
