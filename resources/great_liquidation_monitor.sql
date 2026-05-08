-- Great Liquidation Monitor
-- Purpose: sell-high dashboard query for aging veteran production outliers.
--
-- Anti-Speed rule:
-- This query does not assume Davante Adams' or Tyreek Hill's 2025 production.
-- It only fires when verified gold rows contain the age, valuation, and production evidence.

CREATE OR REPLACE VIEW gen_alpha.gold.great_liquidation_monitor AS
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
  trade_seeker_signal,
  framework_flags,
  evidence_json,
  CASE
    WHEN feature_quality_status = 'INCOMPLETE_REQUIRED_FEATURES' THEN 'ANTI_SPEED_ABORT'
    WHEN market_lag_signal = 'PRIORITY_EXPLOIT' THEN 'PRIORITY_EXPLOIT: market has not priced biological depreciation'
    WHEN player_name = 'Davante Adams'
      AND position = 'WR'
      AND age_years >= 33.0
      AND array_contains(framework_flags, '2025_td_outlier')
      THEN 'SELL_HIGH: age-33 WR with verified 2025 TD outlier and biological depreciation'
    WHEN player_name = 'Tyreek Hill'
      AND position = 'WR'
      AND age_years >= 32.0
      AND (
        array_contains(framework_flags, '2025_production_outlier')
        OR array_contains(framework_flags, '2025_td_outlier')
      )
      THEN 'SELL_HIGH: age-32 WR with verified 2025 production outlier and biological depreciation'
    WHEN age_cliff_risk >= 1.0
      AND dynasty_trajectory IN ('DEPRECIATING', 'CLIFF')
      AND market_delta < 0
      THEN 'SELL_HIGH: market still above internal valuation at/after age cliff'
    ELSE 'MONITOR'
  END AS great_liquidation_action
FROM gen_alpha.gold.roster_valuation_signals
WHERE feature_quality_status = 'READY_FOR_MODELING'
  AND (
    player_name IN ('Davante Adams', 'Tyreek Hill', 'Jonathan Taylor')
    OR age_cliff_signal = 'HIGH_LIQUIDATE'
    OR trade_seeker_signal IN ('SELL_HIGH_LIQUIDATE', 'SHOP_FOR_2027_1ST')
  );

GRANT SELECT ON VIEW gen_alpha.gold.great_liquidation_monitor TO `dg_agent_gold_readers`;
