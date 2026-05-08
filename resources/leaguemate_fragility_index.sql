-- Leaguemate Fragility Index
-- Purpose: rank opposing rosters by probability of their 2027 1st landing in
-- Tier 1/2 target zones.
--
-- Anti-Speed posture:
-- - Uses only Gold valuation rows.
-- - Uses Silver pick inventory for draft-capital ownership context.
-- - Blocks decision-grade output when roster/player rows are incomplete.
-- - Supports mock rows but labels them through source_version.

CREATE TABLE IF NOT EXISTS gen_alpha.silver.leaguemate_pick_inventory (
  league_id STRING NOT NULL,
  owner_username STRING NOT NULL,
  season INT NOT NULL,
  round INT NOT NULL,
  original_owner_username STRING,
  pick_year INT NOT NULL,
  pick_label STRING,
  protection_status STRING COMMENT 'UNPROTECTED, TOP_3_PROTECTED, TOP_6_PROTECTED, UNKNOWN.',
  projected_bucket STRING COMMENT 'EARLY, MID, LATE, UNKNOWN.',
  inventory_source STRING NOT NULL,
  verified_at TIMESTAMP NOT NULL,
  feature_quality_status STRING NOT NULL COMMENT 'READY_FOR_MODELING or INCOMPLETE_REQUIRED_FEATURES.',
  evidence_json STRING COMMENT 'Serialized source trace; never include secrets.'
)
USING DELTA
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'dynasty_genius.layer' = 'silver',
  'dynasty_genius.security' = 'no_agent_direct_access'
);

ALTER TABLE gen_alpha.silver.leaguemate_pick_inventory
  ADD CONSTRAINT leaguemate_pick_inventory_round_chk
  CHECK (round IN (1, 2, 3, 4, 5));

ALTER TABLE gen_alpha.silver.leaguemate_pick_inventory
  ADD CONSTRAINT leaguemate_pick_inventory_protection_chk
  CHECK (protection_status IN ('UNPROTECTED', 'TOP_3_PROTECTED', 'TOP_6_PROTECTED', 'UNKNOWN'));

ALTER TABLE gen_alpha.silver.leaguemate_pick_inventory
  ADD CONSTRAINT leaguemate_pick_inventory_feature_quality_chk
  CHECK (feature_quality_status IN ('READY_FOR_MODELING', 'INCOMPLETE_REQUIRED_FEATURES'));

CREATE OR REPLACE VIEW gen_alpha.gold.leaguemate_fragility_index AS
WITH roster_assets AS (
  SELECT
    valuation_date,
    coalesce(roster_status, 'UNKNOWN') AS roster_status,
    source_version,
    player_id,
    player_name,
    position,
    age_years,
    age_cliff_risk,
    dynasty_trajectory,
    internal_valuation,
    ktc_market_value,
    market_delta,
    feature_quality_status,
    framework_flags,
    calculated_at,
    CASE
      WHEN evidence_json LIKE '%owner_username%' THEN get_json_object(evidence_json, '$.owner_username')
      ELSE NULL
    END AS owner_username,
    CASE
      WHEN evidence_json LIKE '%league_id%' THEN get_json_object(evidence_json, '$.league_id')
      ELSE NULL
    END AS league_id
  FROM gen_alpha.gold.roster_valuation_signals
),
normalized AS (
  SELECT
    valuation_date,
    coalesce(owner_username, 'UNKNOWN_OWNER') AS owner_username,
    coalesce(league_id, 'UNKNOWN_LEAGUE') AS league_id,
    source_version,
    player_id,
    player_name,
    position,
    age_years,
    age_cliff_risk,
    dynasty_trajectory,
    internal_valuation,
    feature_quality_status,
    framework_flags,
    CASE
      WHEN feature_quality_status = 'INCOMPLETE_REQUIRED_FEATURES' THEN 1 ELSE 0
    END AS incomplete_asset,
    CASE
      WHEN age_cliff_risk >= 1.0 THEN 1 ELSE 0
    END AS cliff_asset,
    CASE
      WHEN age_cliff_risk >= 0.67 THEN 1 ELSE 0
    END AS high_biological_debt_asset,
    CASE
      WHEN dynasty_trajectory IN ('DEPRECIATING', 'CLIFF') THEN 1 ELSE 0
    END AS depreciating_asset,
    CASE
      WHEN age_cliff_risk >= 0.67 OR dynasty_trajectory IN ('DEPRECIATING', 'CLIFF')
        THEN coalesce(internal_valuation, 0.0)
      ELSE 0.0
    END AS biological_debt_value
  FROM roster_assets
),
owner_rollup AS (
  SELECT
    valuation_date,
    league_id,
    owner_username,
    max(source_version) AS source_version,
    count(*) AS roster_asset_count,
    sum(incomplete_asset) AS incomplete_asset_count,
    sum(cliff_asset) AS cliff_asset_count,
    sum(high_biological_debt_asset) AS high_biological_debt_asset_count,
    sum(depreciating_asset) AS depreciating_asset_count,
    sum(coalesce(internal_valuation, 0.0)) AS total_internal_roster_value,
    sum(biological_debt_value) AS biological_debt_value,
    avg(age_cliff_risk) AS avg_age_cliff_risk,
    collect_list(
      CASE
        WHEN age_cliff_risk >= 0.67 OR dynasty_trajectory IN ('DEPRECIATING', 'CLIFF')
          THEN player_name
        ELSE NULL
      END
    ) AS biological_debt_players
  FROM normalized
  GROUP BY valuation_date, league_id, owner_username
),
pick_inventory AS (
  SELECT
    league_id,
    owner_username,
    max(CASE
      WHEN pick_year = 2027
        AND round = 1
        AND coalesce(original_owner_username, owner_username) = owner_username
        THEN 1 ELSE 0
    END) AS has_own_2027_1st,
    max(CASE
      WHEN pick_year = 2027
        AND round = 1
        AND coalesce(original_owner_username, owner_username) = owner_username
        AND protection_status = 'UNPROTECTED'
        THEN 1 ELSE 0
    END) AS has_unprotected_own_2027_1st,
    max(CASE
      WHEN pick_year = 2026 AND round = 2 THEN 1 ELSE 0
    END) AS has_2026_2nd,
    max(CASE
      WHEN pick_year = 2027 AND round = 2 THEN 1 ELSE 0
    END) AS has_2027_2nd,
    sum(CASE
      WHEN feature_quality_status = 'INCOMPLETE_REQUIRED_FEATURES' THEN 1 ELSE 0
    END) AS incomplete_pick_rows,
    max(verified_at) AS pick_inventory_verified_at
  FROM gen_alpha.silver.leaguemate_pick_inventory
  GROUP BY league_id, owner_username
),
scored AS (
  SELECT
    owner_rollup.*,
    coalesce(pick_inventory.has_own_2027_1st, 0) AS has_own_2027_1st,
    coalesce(pick_inventory.has_unprotected_own_2027_1st, 0) AS has_unprotected_own_2027_1st,
    coalesce(pick_inventory.has_2026_2nd, 0) AS has_2026_2nd,
    coalesce(pick_inventory.has_2027_2nd, 0) AS has_2027_2nd,
    coalesce(pick_inventory.incomplete_pick_rows, 0) AS incomplete_pick_rows,
    pick_inventory.pick_inventory_verified_at,
    CASE
      WHEN roster_asset_count = 0 THEN NULL
      ELSE biological_debt_value / greatest(total_internal_roster_value, 1.0)
    END AS biological_debt_ratio,
    CASE
      WHEN incomplete_asset_count > 0 OR coalesce(pick_inventory.incomplete_pick_rows, 0) > 0 THEN NULL
      ELSE least(
        1.0,
        greatest(
          0.0,
          (coalesce(avg_age_cliff_risk, 0.0) * 0.35)
          + (coalesce(biological_debt_value / greatest(total_internal_roster_value, 1.0), 0.0) * 0.45)
          + (least(coalesce(cliff_asset_count, 0), 4) / 4.0 * 0.15)
          + (coalesce(pick_inventory.has_unprotected_own_2027_1st, 0) * 0.05)
        )
      )
    END AS fragility_score
  FROM owner_rollup
  LEFT JOIN pick_inventory
    ON pick_inventory.league_id = owner_rollup.league_id
   AND pick_inventory.owner_username = owner_rollup.owner_username
)
SELECT
  valuation_date,
  league_id,
  owner_username,
  source_version,
  roster_asset_count,
  incomplete_asset_count,
  cliff_asset_count,
  high_biological_debt_asset_count,
  depreciating_asset_count,
  has_own_2027_1st,
  has_unprotected_own_2027_1st,
  has_2026_2nd,
  has_2027_2nd,
  CASE
    WHEN has_2026_2nd = 0 AND has_2027_2nd = 0 THEN 'HIGH_NO_SECOND_ROUND_ESCAPE_HATCH'
    WHEN has_2026_2nd = 0 OR has_2027_2nd = 0 THEN 'MEDIUM_LIMITED_ESCAPE_HATCH'
    ELSE 'LOW'
  END AS liquidity_risk,
  total_internal_roster_value,
  biological_debt_value,
  biological_debt_ratio,
  avg_age_cliff_risk,
  fragility_score,
  CASE
    WHEN incomplete_asset_count > 0 OR incomplete_pick_rows > 0 THEN 'ANTI_SPEED_ABORT_INCOMPLETE_ROSTER_OR_PICKS'
    WHEN has_own_2027_1st = 0 THEN 'NO_OWN_2027_1ST_TO_ACQUIRE'
    WHEN fragility_score >= 0.75 AND has_unprotected_own_2027_1st = 1 THEN 'TIER_1_SMITH_SAYIN_ELIGIBLE_TOP_3'
    WHEN fragility_score >= 0.55 AND has_own_2027_1st = 1 THEN 'TIER_2_MANNING_MOORE_ELIGIBLE_TOP_6'
    WHEN fragility_score >= 0.35 THEN 'TIER_3_LATE_2027_1ST'
    ELSE 'LOW_FRAGILITY_CONTENDER_PICK'
  END AS projected_2027_pick_tier,
  CASE
    WHEN incomplete_asset_count > 0 OR incomplete_pick_rows > 0 THEN 'NO_ACTION'
    WHEN has_own_2027_1st = 0 THEN 'NO_TARGET_PICK'
    WHEN fragility_score >= 0.75 AND has_unprotected_own_2027_1st = 1 THEN 'ACQUIRE_UNPROTECTED_2027_1ST_AGGRESSIVELY'
    WHEN fragility_score >= 0.55 AND has_own_2027_1st = 1 THEN 'ACQUIRE_2027_1ST_SELECTIVELY'
    WHEN fragility_score >= 0.35 THEN 'REQUIRE_KICKER_FOR_LATE_1ST'
    ELSE 'DO_NOT_OVERPAY_FOR_CONTENDER_1ST'
  END AS acquisition_action,
  filter(biological_debt_players, player -> player IS NOT NULL) AS biological_debt_players
FROM scored;

GRANT SELECT ON VIEW gen_alpha.gold.leaguemate_fragility_index TO `dg_agent_gold_readers`;
