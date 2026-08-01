# CFBD QB defect — blast-radius correction (Codex v1)

## Correction

The earlier cross-lane statement that Phase 20 assigned the defective QB fields “importance 39.5”
and consumed them is wrong. `39.5` is `coverage_pct`, not feature importance.

The canonical artifact
`app/data/backtest/phase20/phase20_bakeoff_20260524T183807Z_db568d44.json` records:

- all four CFBD QB fields under `positions.QB.dropped_features`;
- `positions.QB.available_features` limited to `nfl_pick`, `nfl_round`, and
  `final_college_age`;
- both ridge and GBT skipped with `reason=enriched_features_equal_baseline`;
- no passing candidates;
- `promotion_decision=REQUIRES_DAVID_REVIEW`;
- `governance.model_pkl_changed=false` and `latest_json_changed=false`.

The promoted `app/data/models/QB_model.pkl` is dated 2026-04-30, before the May 24 bakeoff. Its model
card identifies Engine B v2 training data, not the CFBD-enriched prospect CSV. A binary string scan
also finds none of the four CFBD column names in the model artifacts.

## Honest blast radius

The defect is not “only an API response issue”: adapter identity/scale/error behavior, raw capture,
and curation/publication gates all failed. But its proven impact is currently confined to the CFBD
cache and the gitignored prospect training CSV, plus a latent risk because future bakeoff code lists
the fields as candidates. The inspected Phase 20 run did **not** fit them, did not pass a candidate,
and did not modify or promote a model.

Therefore no current evidence supports model contamination or model remediation. Repair the
foundation contract before any future use, then validate a fresh isolated dataset separately. Do
not promote/copy or spend another paid refresh under this correction.

