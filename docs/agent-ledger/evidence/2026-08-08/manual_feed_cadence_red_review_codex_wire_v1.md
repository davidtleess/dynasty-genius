From Codex — NOT CLEAR on RED f7565ff. Eight blocking findings; full artifact: docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_red_review_codex_v1.md

F1 Split axes. One exclusive state conflates cadence obligation with coverage quality. Medical can be both inadequate and not_due; do not make one erase the other. Pin cadence current/due/not_due and coverage adequate/unknown/inadequate, both serialized. The docstring also says four states while S1 requires five.
F2 S2 is vacuous: len(set)>=1 always passes. Require disagreement and expected roster state, backed by an injected event after the held vintage.
F3 source_offers is an unproven oracle. Require observed_at plus provenance; neither vendor has a governed push signal.
F4 newest_season cannot prove completeness. Add covered-seasons and the 2023+2026-but-missing-2024/25 counter-case.
F5 S6b self-certifies: GREEN can add vendor_push to its own allowed set. Pin the ontology. Policies need multiple triggers, not singular trigger.
F6 No PFF cadence behavior is tested. Add NFL/FBS event-availability windows and completed-history correction-only cases. Do not encode universal Tuesday; Sep 16 2026 is Wednesday anyway.
F7 Grades have no standing obligation because there is no authorized consumer, not because diagnostic evidence can never merit refresh. Pin consumer_authorized; model use stays forbidden and raw retention stays true.
F8 S8 can pass by changing daily to None while the controller reports no streams. Pin report serialization and source aggregation from authorized per-stream results.

Also reject duplicate policy definitions structurally; do not invent RotoViz/C2C stream detail before inventory. Focused RED reproduced 17 failed, true exit 1; ruff clean. No GREEN yet. H2 rushing remains under test and unrelated.
