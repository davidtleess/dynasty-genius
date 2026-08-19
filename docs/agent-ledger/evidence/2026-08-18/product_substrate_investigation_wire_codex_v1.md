From Codex (investigation lane) — RESULT: the 115 blanks are NOT a missing-2024/partial-2025 feature-store failure [w#product-investigation]

Critical reversal: do not rebuild Engine B from ff_opportunity as R1. The evidence refutes the premise.

1. 2024 is absent from the runtime OUTPUT by design (`apply_inference_partition`; ratified BUILD-4 spec), but its data is used before the partition. Garrett Wilson's 2025 `ppg_t_minus_1=14.817647` exactly matches his 17-game 2024 PPG in the independent Aug-14 weekly snapshot.
2. All 505/505 runtime 2025 rows match that separate snapshot on `games_t`; Wilson's seven games and 14.214 PPG match exactly. This is complete-season data, not a partial-season store.
3. The two 115 counts overlap for 114 players, not 115. Nick Kallerup is the feature-side identity orphan. Bo Melton is the served-side replacement: 13-game WR feature, but stale crosswalk wins as CB and prevents DVS. Exactly one position mismatch across all 503 joined Engine B rows.
4. Actual R1 cause: the 114 low-game served rows receive projection but the bridge asks for an Engine A rookie prior the active builder never supplies. 85/114 have 3+ years of experience; 38 have 7+. The no-prior branch then falsely writes `dvs_engine=A` and “Engine A prospect score used as prior”; API reports `modeled` with no degradation.
5. Additional hidden cohort: 108 players have 1–3 source games and are removed before inference by the four-game floor. 99 map into the served universe, four are rostered, none has projection or DVS.
6. Engine B includes postseason. In the 505 inference IDs: 162 postseason participants, 160 changed PPG, mean absolute delta 0.412, and six cross the eight-game gate only through postseason. This is conditional on David's intended PPG definition; the current decision record does not settle REG-only vs all-game.
7. Health provenance is also wrong: participation is labeled `loaded_empty` although WR/TE route features are >99% populated and candidate/prior drift is zero. Retry is described as cache without cache-path evidence.

Rerun decision: QB-1 does NOT need rerun because of tonight. It used a separate pinned seven-dataset root with 2024/2025 present and REG-only labels; report remains decision_supported=false. Engine A also unaffected. PVO should be reassembled only after an authorized state/bridge decision. Engine B + P90/replacement/xVAR/calibration and dependent findings need rerun only if David rules REG-only PPG.

Product conclusion: R1 is points-first presentation and honest state semantics before modeling. Surface existing PPG with unit/horizon/game basis; distinguish projection available/composite unavailable, withheld, pre-model, identity unresolved, and source degraded. Do not inject current age into a rookie model for veterans.

Full ranked, cited report with queries, costs, direct answers to all six questions, caveats, and rerun matrix:
- docs/agent-ledger/evidence/2026-08-18/product_substrate_investigation_codex_v1.md
- portable verified report: product_substrate_investigation_codex_v1.html

No product code changed. Please ACK receipt and correct the durable 21:0x diagnosis before any R1 feature-store rebuild is opened. [w#product-investigation]
