# Design Spec: 2026 Rookie Board (Phase 1: Verified Signals)

**Version:** 1.1.0  
**Status:** Approved  
**Date:** 2026-05-09  
**Target:** May 11th Dynasty Rookie Draft

## Mission
Provide high-signal Best Player Available (BPA) context for David's 2026 Dynasty Rookie Draft. The system must move from "Mock" to "Verified" NFL draft capital (via `nfl_data_py`) to ensure Engine A (PROSPECT_C/D) produces accurate internal value signals.

## 1. Data Contracts

### 1.1 Verified Prospect Manifest (`resources/prospect_identity_2026.json`)
Primary source of truth for the 2026 class. Replaces all mock 2026 data.

```json
{
  "source": "nfl_data_py_verified_nfl_draft",
  "players": [
    {
      "dg_id": "fernando_mendoza_qb_2003",
      "full_name": "Fernando Mendoza",
      "position": "QB",
      "nfl_team": "LVR",
      "pick": 1,
      "round": 1,
      "birth_date": "2003-10-01",
      "sleeper_id": "12345",
      "verification_status": "VERIFIED_NFL_DRAFT"
    }
  ]
}
```

### 1.2 Market Overlay (Phase 2 - Non-Blocking)
The "Lookalike Market" (50+ Sleeper leagues) or external ADP (DynastyNerds/FantasyCalc) is a follow-on feature. The board will ship with `market_overlay: null` for the May 11th draft start.

## 2. Coordination Contract (Gemini & Claude)

### Gemini Tasks (Backend & Data)
1. **NFL Draft Ingestion:** Fetch April 2026 results via `nfl_data_py` and enrich with `dg_id` and birth dates.
2. **PVO Wiring:** Update `pvo_assembler.py` to join this manifest into the Rookie Board pipeline.
3. **Data Verification:** Ensure `sleeper_id` values are accurate for live availability tracking.

### Claude Tasks (UI & Integration)
1. **Rookie Board UI:** Build a dedicated surface (`rookie_board.html`) separate from the Roster Audit.
2. **Divergence Visuals (Phase 2):** When market data is added, show neutral divergence (e.g., "Market is +4 spots higher"). No directive "Buy/Sell/Draft" labels.
3. **8-Hour Steelman:** Ensure the `counter_argument` field is prominent to prevent slow-draft tunnel vision.
4. **Availability Sync:** Use `sleeper_id` to filter out players already drafted in David's league.

## 3. Decision Logic: Signal-Only Posture
All output must carry the `PROSPECT_C/D` model grade. The board surfaces **Signals**, not **Decisions**.

- **Internal BPA Score:** A 0-100 normalization of Engine A's PPG forecast.
- **Contextual Caveats:** Explicitly state the limits of Engine A (no usage data, pre-training draft-capital only).

## 4. Governance & Constraints
- **Banned Language:** No reintroduction of "Confidence," "Draft Target," or "Verdict" fields.
- **No Leakage:** Ensure zero market-derived inputs enter the `Engine A` scoring logic.
- **Neutrality:** The system empowers David to decide; it does not issue instructions.
