-- Opponent Fragility Lens
-- Purpose: dashboard context query for aging veteran production outliers.
--
-- Anti-Speed rule:
-- This query does not assume Davante Adams' or Tyreek Hill's 2025 production.
-- It only emits context signals when verified gold rows contain the age,
-- valuation, and production evidence. It does not issue trade instructions.

CREATE OR REPLACE VIEW gen_alpha.gold.opponent_fragility_lens AS
SELECT
  valuation_date,
  player_id,
  player_name,
  position,
  nfl_team,
  age_years,
  age_cliff_threshold,
  age_cliff_risk,
  age_cliff_signal,
  dynasty_trajectory,
  internal_valuation,
  ktc_market_value,
  ktc_market_updated_at,
  market_delta,
  market_lag_signal,
  market_context_signal,
  framework_flags,
  evidence_json,
  CASE
    WHEN feature_quality_status = 'INCOMPLETE_REQUIRED_FEATURES' THEN 'ANTI_SPEED_ABORT'
    WHEN market_lag_signal = 'MARKET_NOT_PRICED_DEPRECIATION' THEN 'market_not_priced_biological_depreciation'
    WHEN player_name = 'Davante Adams'
      AND position = 'WR'
      AND age_years >= 33.0
      AND array_contains(framework_flags, '2025_td_outlier')
      THEN 'verified_age_outlier_depreciation_signal'
    WHEN player_name = 'Tyreek Hill'
      AND position = 'WR'
      AND age_years >= 32.0
      AND (
        array_contains(framework_flags, '2025_production_outlier')
        OR array_contains(framework_flags, '2025_td_outlier')
      )
      THEN 'verified_age_outlier_depreciation_signal'
    WHEN age_cliff_risk >= 1.0
      AND dynasty_trajectory IN ('DEPRECIATING', 'CLIFF')
      AND market_delta < 0
      THEN 'age_cliff_market_delta_signal'
    ELSE 'no_current_fragility_signal'
  END AS fragility_context_signal,
  false AS decision_supported,
  array(
    'verify_live_roster_snapshot',
    'verify_pick_inventory',
    'review_counter_argument',
    'confirm_market_overlay_is_post_model_only'
  ) AS required_before_action
FROM gen_alpha.gold.roster_valuation_signals
WHERE feature_quality_status = 'READY_FOR_MODELING'
  AND (
    player_name IN ('Davante Adams', 'Tyreek Hill', 'Jonathan Taylor')
    OR age_cliff_signal = 'AGE_CLIFF_HIGH'
    OR market_context_signal IN (
      'AGE_CLIFF_MARKET_DELTA_SIGNAL',
      'AGING_ASSET_CONCENTRATION_SIGNAL'
    )
  );

GRANT SELECT ON VIEW gen_alpha.gold.opponent_fragility_lens TO `dg_agent_gold_readers`;
