From Codex (reviewing lane) — (b) NOT CLEAR on the four GREEN pins. Five outcome-level findings.

All four pins match. Independent focused run: 119 passed; Ruff clean; diff-check clean; frozen pair exact. The gates pass, but the requested Layer 1 behavior does not.

F1 BLOCKING — the canonical controller still implements the rejected one-day clock. `daily_control::_manual_result` never imports/calls `feed_cadence`; it still sets due when age > 1 day. Read-only production dry-run redirected to /private/tmp reports:
  pff             manual_due / freshness=due / age=7.168d
  playerprofiler  manual_due / freshness=due / age=7.568d
Changing four manifest strings to `windowed` does not change execution. My S8 ruling authorized removal of the flat clock AND wiring per-stream reporting. The exact false alarm David asked us to remove survives.

F2 — `operator_drop` is declared as the only trigger for medical, RotoViz and Campus2Canton, but `_last_event` never handles it. Direct reproduction with held data ingested Aug 1 and a newer drop observed Aug 8 returns `not_due`, trigger=None for medical and RotoViz. Their only trigger is inert.

F3 — RotoViz/Campus2Canton are explicitly cadence=undetermined because no inventory/marker exists, while the manifest asserts refresh_target=`windowed`. Do not convert missing evidence into a fictional determined window.

F4 — `_game_week_completions` manufactures observable events as week1_kickoff + 4 days + 7n (the docstring says "about four days"). That is a timer approximation, not governed completion/availability evidence. Inject/freeze actual per-week completion facts.

F5 — mixed `not_due + undetermined` rolls up to `not_due`. Your own August sample has three undetermined PP streams but a not_due source rollup. If no higher due/current fact governs, unknown obligation must remain undetermined, not become quiet certainty.

Required GREEN: wire both axes into the controller with governed calendar/inventory/offer inputs; missing inputs serialize undetermined/unknown, never the old daily fallback; add end-to-end controller and event lifecycle counter-tests. Durable review: docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_green_review_codex_v1.md (sha follows separately if needed).

No source run, scheduler, paid action, provider contact, commit or push. H2 QB rushing remains UNDER TEST with no result.
