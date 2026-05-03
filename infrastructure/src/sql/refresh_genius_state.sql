-- Sovereign Unity Single Source of Truth (SSoT) Refresh
-- Combines anchors + efficiency_metrics + NFL production
-- Applies status classification and governance rules
-- Frequency: Hourly via Databricks Job

CREATE OR REPLACE TABLE gen_alpha.gold.genius_state AS
WITH base_state AS (
    SELECT 
        -- Player identity
        a.player_name,
        COALESCE(e.position, n.position) AS position,
        a.class_year,
        
        -- Status classification (NFL roster > age-based logic)
        CASE
            WHEN n.team IS NOT NULL AND n.snap_count > 0 THEN 'PRO_VETERAN'
            WHEN COALESCE(e.age, n.age) IS NULL OR COALESCE(e.age, n.age) < 20 THEN 'EARLY_PROSPECT'
            WHEN COALESCE(e.age, n.age) BETWEEN 20 AND 22 THEN 'DRAFT_ELIGIBLE'
            WHEN COALESCE(e.age, n.age) BETWEEN 23 AND 27 THEN 'PRIME_WINDOW'
            WHEN COALESCE(e.age, n.age) >= 28 THEN 'DECLINE_PHASE'
            ELSE 'UNKNOWN'
        END AS canonical_status,
        
        CASE WHEN n.team IS NOT NULL AND n.snap_count > 0 THEN TRUE ELSE FALSE END AS nfl_roster_verified,
        
        -- Core valuation metrics (DVU = Dynasty Value Unit)
        a.dvu_anchor,
        a.dominator_rating_target,
        a.ras_target,
        
        -- Efficiency metrics from silver layer
        e.efficiency_score,
        e.dominator_rating AS current_dominator,
        e.yprr,
        COALESCE(e.success_rate_vs_zone, n.success_rate_vs_zone) AS success_rate_vs_zone,
        COALESCE(e.success_rate_vs_man, n.success_rate_vs_man) AS success_rate_vs_man,
        
        -- Source tracking for 65:35 compliance
        COALESCE(e.data_source, n.data_source) AS primary_data_source,
        COALESCE(e.source_rank, n.source_rank) AS source_rank,
        
        -- Demographics
        COALESCE(e.age, n.age) AS age,
        
        -- NFL production (if available)
        n.team AS nfl_team,
        n.snap_count AS nfl_snap_count,
        
        -- Timestamps
        a.last_updated AS anchor_last_updated,
        CURRENT_TIMESTAMP() AS state_last_refresh
        
    FROM gen_alpha.gold.anchors a
    
    LEFT JOIN gen_alpha.silver.efficiency_metrics e
        ON a.player_name = e.player_name
    
    LEFT JOIN gen_alpha.bronze.nfl_production_2025 n
        ON a.player_name = n.player_name
),

-- Apply governance rules from gen_alpha.gold.governance_rules
governed_state AS (
    SELECT 
        bs.*,
        
        -- Apply RB age cliff rule (30% DVU reduction at age 28)
        CASE 
            WHEN bs.position = 'RB' 
                AND bs.age >= 28 
                AND EXISTS (
                    SELECT 1 FROM gen_alpha.gold.governance_rules 
                    WHERE rule_id = 'rb_age_cliff_28'
                )
            THEN bs.dvu_anchor * 0.70
            ELSE bs.dvu_anchor
        END AS dvu_governed
        
    FROM base_state bs
)

SELECT 
    player_name,
    position,
    canonical_status,
    nfl_roster_verified,
    dvu_governed AS dvu_anchor,  -- Use governed DVU
    dominator_rating_target,
    ras_target,
    class_year,
    efficiency_score,
    current_dominator,
    yprr,
    success_rate_vs_zone,
    success_rate_vs_man,
    primary_data_source,
    source_rank,
    age,
    nfl_team,
    nfl_snap_count,
    anchor_last_updated,
    state_last_refresh
FROM governed_state;

-- Refresh complete message
SELECT 
    'genius_state refresh completed' AS status,
    COUNT(*) AS total_rows,
    CURRENT_TIMESTAMP() AS refresh_timestamp
FROM gen_alpha.gold.genius_state;
