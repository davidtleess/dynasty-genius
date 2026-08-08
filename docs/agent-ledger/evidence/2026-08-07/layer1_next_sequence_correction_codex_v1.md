From Codex (reviewing lane) [w#l1-next-sequence-correction-1] — (b) DISSENT from the literal sequence; corrected sequence preserves David's objective

Three measured facts make the relayed sequence stale:

1. `scripts/run_layer1_daily_control.py --execute` is not the reviewed invocation. Execution is the default; the safe narrowed rerun is `.venv/bin/python3.14 scripts/run_layer1_daily_control.py --only nflverse_usage_capture`.
2. `sleeper_transactions` already executed successfully at 22:28–22:34 ET and is current. Re-running it now is an unnecessary second public pull and cannot recover events that aged out before the successful capture.
3. The bounded contracts persistence question is answered by the live run: `contracts` materialized with 48,511 rows plus its snapshot ledger row. The remaining concrete defect is export publication, not persistence. That export repair is currently in GREEN testing and is not yet review-CLEAR.

Correct sequence: finish the exact GREEN gates with an unmasked pytest exit; Codex reviews; after CLEAR rerun **only** `nflverse_usage_capture`; verify the ready marker advances and contracts is present in the complete export; reconcile catalog/board/ledger; explicit-path commit and push. PlayerProfiler remains tracked as `manual_download`; no subscriber export exists to ingest now, and this is not authority to request or contact anyone.

This dissent is technical and bounded. It does not dissent from David's Layer 1 completion objective.

QB rushing remains a registered hypothesis under test with no result.
