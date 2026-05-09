-- Alpha Divergence Weekly Report
-- Purpose: Gold-facing report for players where internal value is more than
-- 15% below Silver market consensus.
--
-- These are context signals: the market remains above the internal model.

CREATE OR REPLACE VIEW gen_alpha.gold.alpha_divergence_weekly_report AS
SELECT
  valuation_date,
  player_id,
  player_name,
  position,
  dynasty_trajectory,
  gold_asset_tier_status,
  qual_dominant_override,
  qual_rationale,
  gold_internal_valuation,
  silver_market_value,
  silver_market_rank,
  silver_consensus_tier,
  gold_vs_silver_market_delta,
  CASE
    WHEN silver_market_value IS NULL OR silver_market_value = 0 THEN NULL
    ELSE (silver_market_value - gold_internal_valuation) / silver_market_value
  END AS internal_discount_to_market_pct,
  alpha_divergence_signal,
  audit_signal,
  framework_flags,
  gold_evidence_json,
  market_evidence_json,
  calculated_at
FROM gen_alpha.gold.model_accuracy_dashboard
WHERE alpha_divergence_signal = 'INTERNAL_BELOW_MARKET_DEPRECIATION_SIGNAL'
  AND silver_market_value IS NOT NULL
  AND silver_market_value > 0
  AND (silver_market_value - gold_internal_valuation) / silver_market_value >= 0.15;

GRANT SELECT ON VIEW gen_alpha.gold.alpha_divergence_weekly_report TO `dg_agent_gold_readers`;
