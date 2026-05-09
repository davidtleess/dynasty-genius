-- Dynasty Genius Gold Layer: roster valuation analytics
-- Catalog: gen_alpha
-- Schema: gold
--
-- Security posture:
-- - Gold is the only analytics layer exposed to Claude/MCP agent readers.
-- - Agent readers receive SELECT only.
-- - No secrets or gateway environment variables are persisted in bronze, silver, or gold.

CREATE SCHEMA IF NOT EXISTS gen_alpha.gold;

CREATE TABLE IF NOT EXISTS gen_alpha.gold.roster_valuation (
  valuation_id STRING NOT NULL COMMENT 'Stable valuation row id, generally sha2(player_id|valuation_date|source_version).',
  valuation_date DATE NOT NULL COMMENT 'Date the valuation snapshot was calculated.',
  player_id STRING NOT NULL,
  player_name STRING NOT NULL,
  position STRING NOT NULL COMMENT 'One of RB, WR, TE, QB, or another roster position when retained for completeness.',
  nfl_team STRING,
  roster_status STRING COMMENT 'Roster context such as STARTER, BENCH, TAXI, IR, WATCHLIST.',

  age_years DOUBLE NOT NULL COMMENT 'Verified age as of valuation_date. Must come from primary/verified source data.',
  age_cliff_threshold DOUBLE GENERATED ALWAYS AS (
    CASE position
      WHEN 'RB' THEN 26.0
      WHEN 'WR' THEN 28.0
      WHEN 'TE' THEN 30.0
      WHEN 'QB' THEN 33.0
      ELSE NULL
    END
  ) COMMENT 'Framework Protocol 4 age-cliff threshold by position.',
  age_cliff_risk DOUBLE GENERATED ALWAYS AS (
    CASE
      WHEN position NOT IN ('RB', 'WR', 'TE', 'QB') THEN NULL
      WHEN age_years IS NULL THEN NULL
      ELSE LEAST(
        1.0,
        GREATEST(
          0.0,
          (
            age_years - (
              CASE position
                WHEN 'RB' THEN 26.0
                WHEN 'WR' THEN 28.0
                WHEN 'TE' THEN 30.0
                WHEN 'QB' THEN 33.0
              END - 3.0
            )
          ) / 3.0
        )
      )
    END
  ) COMMENT 'Calculated 0.0-1.0 risk based on proximity to positional age cliff. Risk reaches 1.0 at the cliff.',

  dynasty_trajectory STRING NOT NULL COMMENT 'APPRECIATING, DEPRECIATING, PEAK, or CLIFF.',
  asset_tier_status STRING COMMENT 'Strategic tier such as ANCHOR, CO_ANCHOR, CONDITIONAL_TIER_2, DEPRECIATION_WATCH, or UNASSIGNED.',
  asset_tier_basis STRING COMMENT 'Short explanation for strategic tier status. Must be evidence-backed; never narrative-only.',
  qual_dominant_override BOOLEAN NOT NULL DEFAULT false COMMENT 'True when human qualitative judgment intentionally overrides or re-tiers the model baseline.',
  qual_rationale STRING COMMENT 'Required rationale for qual_dominant_override; used for retrospective alpha/noise audits.',

  internal_valuation DOUBLE NOT NULL COMMENT 'Dynasty Genius internal valuation score.',
  ktc_market_value DOUBLE COMMENT 'KeepTradeCut market signal from verified scrape/snapshot.',
  ktc_market_updated_at TIMESTAMP COMMENT 'Timestamp of the KTC market signal snapshot used for market_delta.',
  market_delta DOUBLE GENERATED ALWAYS AS (
    internal_valuation - ktc_market_value
  ) COMMENT 'Internal valuation minus KTC market value. Positive means internal model is above market.',

  feature_quality_status STRING NOT NULL COMMENT 'READY_FOR_MODELING or INCOMPLETE_REQUIRED_FEATURES.',
  framework_flags ARRAY<STRING> COMMENT 'Framework warnings such as age_cliff, poor_year_1_usage, low_yprr, or market_inversion.',
  evidence_json STRING COMMENT 'Serialized source trace for valuation inputs; never include secrets.',
  source_version STRING NOT NULL,
  calculated_at TIMESTAMP NOT NULL
)
USING DELTA
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'dynasty_genius.layer' = 'gold',
  'dynasty_genius.security' = 'read_only_agent_surface'
);

ALTER TABLE gen_alpha.gold.roster_valuation
  ADD CONSTRAINT roster_valuation_position_chk
  CHECK (position IN ('RB', 'WR', 'TE', 'QB', 'OTHER'));

ALTER TABLE gen_alpha.gold.roster_valuation
  ADD CONSTRAINT roster_valuation_dynasty_trajectory_chk
  CHECK (dynasty_trajectory IN ('APPRECIATING', 'DEPRECIATING', 'PEAK', 'CLIFF'));

ALTER TABLE gen_alpha.gold.roster_valuation
  ADD CONSTRAINT roster_valuation_asset_tier_status_chk
  CHECK (
    asset_tier_status IS NULL
    OR asset_tier_status IN (
      'ANCHOR',
      'CO_ANCHOR',
      'CONDITIONAL_TIER_2',
      'DEPRECIATION_WATCH',
      'UNASSIGNED'
    )
  );

ALTER TABLE gen_alpha.gold.roster_valuation
  ADD CONSTRAINT roster_valuation_qual_override_chk
  CHECK (
    qual_dominant_override = false
    OR (qual_dominant_override = true AND qual_rationale IS NOT NULL AND length(trim(qual_rationale)) > 0)
  );

ALTER TABLE gen_alpha.gold.roster_valuation
  ADD CONSTRAINT roster_valuation_feature_quality_chk
  CHECK (feature_quality_status IN ('READY_FOR_MODELING', 'INCOMPLETE_REQUIRED_FEATURES'));

ALTER TABLE gen_alpha.gold.roster_valuation
  ADD CONSTRAINT roster_valuation_age_cliff_risk_chk
  CHECK (age_cliff_risk IS NULL OR (age_cliff_risk >= 0.0 AND age_cliff_risk <= 1.0));

-- Least-privilege MCP / Claude agent access.
-- Create the principal/group in the Databricks account workspace first if needed.
GRANT USE CATALOG ON CATALOG gen_alpha TO `dg_agent_gold_readers`;
GRANT USE SCHEMA ON SCHEMA gen_alpha.gold TO `dg_agent_gold_readers`;
GRANT SELECT ON TABLE gen_alpha.gold.roster_valuation TO `dg_agent_gold_readers`;

CREATE OR REPLACE VIEW gen_alpha.gold.roster_valuation_signals AS
SELECT
  valuation_id,
  valuation_date,
  player_id,
  player_name,
  position,
  nfl_team,
  roster_status,
  age_years,
  age_cliff_threshold,
  age_cliff_risk,
  CASE
    WHEN feature_quality_status = 'INCOMPLETE_REQUIRED_FEATURES' THEN 'ANTI_SPEED_ABORT'
    WHEN age_cliff_risk >= 1.0 THEN 'AGE_CLIFF_HIGH'
    WHEN age_cliff_risk >= 0.67 THEN 'HIGH'
    WHEN age_cliff_risk >= 0.34 THEN 'MEDIUM'
    WHEN age_cliff_risk IS NULL THEN 'UNKNOWN'
    ELSE 'LOW'
  END AS age_cliff_signal,
  dynasty_trajectory,
  asset_tier_status,
  asset_tier_basis,
  qual_dominant_override,
  qual_rationale,
  internal_valuation,
  ktc_market_value,
  ktc_market_updated_at,
  market_delta,
  CASE
    WHEN feature_quality_status = 'INCOMPLETE_REQUIRED_FEATURES' THEN 'ANTI_SPEED_ABORT'
    WHEN ktc_market_value IS NULL THEN 'KTC_MISSING'
    WHEN ktc_market_updated_at IS NOT NULL AND ktc_market_updated_at < calculated_at - INTERVAL 7 DAYS THEN 'MARKET_STALE'
    WHEN age_cliff_risk >= 1.0
      AND dynasty_trajectory IN ('DEPRECIATING', 'CLIFF')
      AND market_delta < 0
      THEN 'MARKET_NOT_PRICED_DEPRECIATION'
    ELSE 'NO_MARKET_LAG'
  END AS market_lag_signal,
  CASE
    WHEN feature_quality_status = 'INCOMPLETE_REQUIRED_FEATURES' THEN 'ANTI_SPEED_ABORT'
    WHEN asset_tier_status = 'CONDITIONAL_TIER_2' THEN 'WATCH_ONLY_CONDITIONAL_TIER_2'
    WHEN age_cliff_risk >= 1.0
      AND dynasty_trajectory IN ('DEPRECIATING', 'CLIFF')
      AND market_delta < 0
      THEN 'AGE_AND_MARKET_DIVERGENCE_SIGNAL'
    WHEN age_cliff_risk >= 1.0 AND market_delta < 0 THEN 'AGE_CLIFF_MARKET_DELTA_SIGNAL'
    WHEN age_cliff_risk >= 0.67 AND dynasty_trajectory IN ('DEPRECIATING', 'CLIFF') THEN 'AGING_ASSET_CONCENTRATION_SIGNAL'
    WHEN market_delta > 0 THEN 'MARKET_ABOVE_INTERNAL_SIGNAL'
    WHEN market_delta < 0 THEN 'MARKET_OVERVALUED'
    ELSE 'NO_CURRENT_SIGNAL'
  END AS market_context_signal,
  feature_quality_status,
  framework_flags,
  evidence_json,
  source_version,
  calculated_at
FROM gen_alpha.gold.roster_valuation;

GRANT SELECT ON VIEW gen_alpha.gold.roster_valuation_signals TO `dg_agent_gold_readers`;
