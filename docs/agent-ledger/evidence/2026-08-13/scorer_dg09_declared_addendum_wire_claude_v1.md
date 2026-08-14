From Claude (implementing lane) — TW0813-SCORER-1 ADDENDUM to the round-2 request: DG-09 CLOSED by David's word; declared-date measurements supersede the 06-28 candidate numbers [w#scorer-wire-1]

David's word (Tower relay TW0813-DG09-DECLARED, verbatim): "the frozen set is 2026-08-05". The declaration is written and loader-verified:
- app/config/realized_outcome_frozen_predictions.json — SHA-256 77544b3b02850ceee1658806508af6e1af739fdf4cb0d756107195d6bb8bfce8 (required fields + audit context incl. his verbatim word and measurements-at-declaration).
- Measured on the DECLARED date (sqlite ro, rerunnable): source model_pvo; 501 captured predictions with non-null projection_2y; 11,708 capture_incomplete; 12,209 snapshot rows total; 5-key join 501/501; crosswalk gsis coverage 501/501, zero unresolved.
- _default_prediction_loader(2026, 1) returns 501 rows end-to-end with no network; season 2027 raises FrozenPredictionSetUndeclared.

Round-2 consequence for your review: framing v2 §2's denominators (583/503/80, missing_feature_row) were measured on the 06-28 CANDIDATE. The declared 08-05 date measures differently (501 captured; capture_incomplete only — no missing_feature_row rows on that date). Proposed contract shape, open to your challenge: B1's denominator/exclusion contracts bind to the DECLARED capture through the declaration file at runtime — the RED fixes the CONTRACT (denominator = all model-supported rows on the declared date; named per-status exclusion counts; util selection), never a hardcoded candidate-date count. Treat this addendum as part of the v2 review scope.

Also for your record: Tower's flag that the 2026-08-12 daily capture is MISSING from the store is independently verified (dates 08-03..11 then 13). Tracked as a separate layer-1 health item; not blocking this cycle.

PLEASE REPLY with your round-2 verdict on framing v2 (e31a583c…) + this addendum: (a) explicit CLEAR with enumerated checks and your RED-authorship position, OR (b) concrete round-2 findings.
