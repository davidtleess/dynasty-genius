-- Model Accuracy Dashboard
-- Purpose: retrospective audit surface for qualitative overrides and market-consensus drift.
--
-- Required upstream Silver table:
--   gen_alpha.silver.market_consensus_values
--
-- This view is intentionally read-only and Gold-exposed. Agent readers do not receive
-- direct access to Silver market tables.

CREATE TABLE IF NOT EXISTS gen_alpha.silver.market_consensus_values (
  asset_id STRING COMMENT 'Player/prospect id when available.',
  player_name STRING NOT NULL,
  position STRING,
  draft_class INT,
  source STRING NOT NULL COMMENT 'KTC, DynastyNerds, mock_market_consensus, or other approved source.',
  market_value DOUBLE,
  market_rank INT,
  consensus_tier_label STRING COMMENT 'Market tier label such as ANCHOR, TIER_1, TIER_2, CONDITIONAL_TIER_2.',
  consensus_updated_at TIMESTAMP NOT NULL,
  feature_quality_status STRING NOT NULL COMMENT 'READY_FOR_MODELING or INCOMPLETE_REQUIRED_FEATURES.',
  evidence_json STRING COMMENT 'Serialized source trace; never include secrets.'
)
USING DELTA
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'dynasty_genius.layer' = 'silver',
  'dynasty_genius.security' = 'no_agent_direct_access'
);

ALTER TABLE gen_alpha.silver.market_consensus_values
  ADD CONSTRAINT market_consensus_feature_quality_chk
  CHECK (feature_quality_status IN ('READY_FOR_MODELING', 'INCOMPLETE_REQUIRED_FEATURES'));

CREATE OR REPLACE VIEW gen_alpha.gold.model_accuracy_dashboard AS
WITH latest_market AS (
  SELECT
    asset_id,
    player_name,
    position,
    draft_class,
    source AS market_source,
    market_value AS silver_market_value,
    market_rank AS silver_market_rank,
    consensus_tier_label AS silver_consensus_tier,
    consensus_updated_at,
    feature_quality_status AS market_feature_quality_status,
    evidence_json AS market_evidence_json,
    row_number() OVER (
      PARTITION BY coalesce(asset_id, lower(trim(player_name)))
      ORDER BY consensus_updated_at DESC
    ) AS market_row_number
  FROM gen_alpha.silver.market_consensus_values
),
joined AS (
  SELECT
    g.valuation_date,
    g.player_id,
    g.player_name,
    g.position,
    g.dynasty_trajectory,
    g.asset_tier_status AS gold_asset_tier_status,
    g.asset_tier_basis,
    g.qual_dominant_override,
    g.qual_rationale,
    g.internal_valuation AS gold_internal_valuation,
    g.ktc_market_value AS gold_ktc_market_value,
    g.market_delta AS gold_market_delta,
    m.market_source,
    m.silver_market_value,
    m.silver_market_rank,
    m.silver_consensus_tier,
    m.consensus_updated_at,
    CASE
      WHEN m.silver_market_value IS NULL THEN NULL
      ELSE g.internal_valuation - m.silver_market_value
    END AS gold_vs_silver_market_delta,
    CASE
      WHEN g.feature_quality_status = 'INCOMPLETE_REQUIRED_FEATURES' THEN 'ANTI_SPEED_ABORT_GOLD_INCOMPLETE'
      WHEN m.market_feature_quality_status = 'INCOMPLETE_REQUIRED_FEATURES' THEN 'ANTI_SPEED_ABORT_MARKET_INCOMPLETE'
      WHEN m.silver_market_value IS NULL THEN 'MARKET_CONSENSUS_MISSING'
      WHEN g.internal_valuation < m.silver_market_value
        AND g.asset_tier_status IN ('CONDITIONAL_TIER_2', 'DEPRECIATION_WATCH')
        THEN 'INTERNAL_BELOW_MARKET_DEPRECIATION_SIGNAL'
      WHEN g.internal_valuation > m.silver_market_value
        THEN 'INTERNAL_ABOVE_MARKET_SIGNAL'
      ELSE 'NO_ALPHA_DIVERGENCE'
    END AS alpha_divergence_signal,
    CASE
      WHEN g.feature_quality_status = 'INCOMPLETE_REQUIRED_FEATURES' THEN 'ANTI_SPEED_ABORT_GOLD_INCOMPLETE'
      WHEN m.market_feature_quality_status = 'INCOMPLETE_REQUIRED_FEATURES' THEN 'ANTI_SPEED_ABORT_MARKET_INCOMPLETE'
      WHEN m.silver_market_value IS NULL THEN 'MARKET_CONSENSUS_MISSING'
      WHEN g.qual_dominant_override THEN 'QUAL_OVERRIDE_ACTIVE'
      WHEN g.asset_tier_status <> m.silver_consensus_tier THEN 'TIER_DISAGREEMENT'
      ELSE 'MODEL_MARKET_ALIGNED'
    END AS audit_signal,
    g.framework_flags,
    g.evidence_json AS gold_evidence_json,
    m.market_evidence_json,
    g.source_version,
    g.calculated_at
  FROM gen_alpha.gold.roster_valuation_signals g
  LEFT JOIN latest_market m
    ON m.market_row_number = 1
   AND (
     (m.asset_id IS NOT NULL AND m.asset_id = g.player_id)
     OR lower(trim(m.player_name)) = lower(trim(g.player_name))
   )
)
SELECT *
FROM joined
WHERE qual_dominant_override = true
   OR lower(player_name) = 'ryan williams'
   OR alpha_divergence_signal IN ('INTERNAL_BELOW_MARKET_DEPRECIATION_SIGNAL', 'INTERNAL_ABOVE_MARKET_SIGNAL')
   OR audit_signal IN ('QUAL_OVERRIDE_ACTIVE', 'TIER_DISAGREEMENT', 'MARKET_CONSENSUS_MISSING');

GRANT SELECT ON VIEW gen_alpha.gold.model_accuracy_dashboard TO `dg_agent_gold_readers`;
