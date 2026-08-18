# Footballguys horizon context-clear handoff — Codex v1

Date: 2026-08-17  
Thread: `fbg-horizon-1`  
Purpose: durable cold-start state for the next context; no execution or authorization

## Current truth

- Exact field: `adp_sleeper-sf`.
- Retained object: SHA-256 `d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c`.
- Semantic state remains **`horizon=unknown`**. Phase C remains closed.
- David's pre-registered eligibility criterion is recorded verbatim in the 2026-08-17 ledger at 19:23 ET. It defines what would qualify; it does not establish the field's factual horizon.

## Closed review rounds

1. **Evidence v1: NOT CLEAR, finding `FBG-HZN-F1`; accepted by Claude.** All retained-byte facts reproduced, but the 10-label binary string block is non-exhaustive relative to 18 ADP fields, so label absence could not uniquely bind the field. Review: `fbg_horizon_evidence_review_codex_v1.md`, SHA-256 `bc35172583583d94f3a6ca2aeca8fc0ad0073697b5d13535630233021c31aed6`.
2. **Dynamic-trace protocol: CLEAR and accepted by Claude.** Direct provider-app selector behavior is an admissible binding-proof route; static decompilation/provider documentation is not mandatory. Review: `fbg_horizon_dynamic_trace_protocol_review_codex_v1.md`, exact SHA-256 `5c1d2b0c3bb0bfb9421e6d4b7024212dc223084b197b23b5e03efab1d5e661a4`.

## Next gate — David-scheduled captured execution

No extracted app exists. Extract the run bytes directly from the retained object, then:

1. Verify before and after: binary `d9bc9b2d…`, bundled `adp.csv` `1f7afcbf…`, version `2026i`; allow no refresh/resource replacement.
2. Visibly prove the displayed rows use the selected ADP source—explicit ascending ADP sort or visible numeric ADP values. An unspecified board order fails.
3. In one session with no picks and all other settings fixed, capture `Sleeper Dynasty` Superflex → 1QB → Superflex and reproduce both exact top-12 fingerprints. The SF and 1QB fingerprints are each unique among all 18 retained ADP fields; unique prefixes are 2 and 4, respectively; ranks 1–12 have no ties.
4. Prefer one continuous full-frame recording; retain hashes, timestamp/timezone, and David's witness record. Sleeper Redraft/no-data is corroboration only.
5. Fail closed on any mismatch, hidden sort, stale/non-applied setting, fallback, refresh/hash drift, or capture gap.

The resulting evidence returns to Codex for control-by-control review. Only after a passing evidence review may the packet ask David to adjudicate the semantic contract. A passing trace does not itself write semantic state. If David later adjudicates `dynasty_startup`, plan-v2 §0 still requires fresh startup-draft-vs-trade-price framing before Phase C opens.

## Boundaries and worktree state

- This session did not execute Draft Dominator, contact Footballguys, mutate the retained object or any store, write semantic state, adjudicate the horizon, open Phase C, change product code/tests/config, stage, commit, or push.
- Codex-created uncommitted artifacts for this round: this handoff; `fbg_horizon_dynamic_trace_protocol_review_codex_v1.md`; `fbg_horizon_dynamic_trace_protocol_reply_codex_v1.md`; `fbg_horizon_dynamic_trace_protocol_awareness_codex_v1.md`; plus Codex's earlier v1 review/wire artifacts. `AGENT_SYNC.md` and the 2026-08-17 ledger contain the live state.
- The worktree also contains substantial pre-existing user/peer changes across unrelated threads. Preserve them; do not infer ownership or include them in this horizon scope.
