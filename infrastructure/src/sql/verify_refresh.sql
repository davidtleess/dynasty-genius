-- Verification Query: Genius State Refresh
-- Validates that the refresh completed successfully
-- Checks row counts, status distribution, and data quality

SELECT 
    COUNT(*) as total_players,
    COUNT(CASE WHEN canonical_status = 'PRO_VETERAN' THEN 1 END) as pro_veterans,
    COUNT(CASE WHEN canonical_status = 'DRAFT_ELIGIBLE' THEN 1 END) as draft_eligible,
    COUNT(CASE WHEN canonical_status = 'EARLY_PROSPECT' THEN 1 END) as early_prospects,
    COUNT(CASE WHEN dvu_anchor IS NULL THEN 1 END) as missing_dvu,
    MAX(state_last_refresh) as last_refresh_timestamp,
    CURRENT_TIMESTAMP() as verification_timestamp
FROM gen_alpha.gold.genius_state;

-- Hard fail if the SSoT contains duplicate player rows.
-- This protects aggregate DVU calculations from upstream join fanout.
SELECT
    assert_true(
        COUNT(*) = 0,
        'gen_alpha.gold.genius_state contains duplicate player_name rows'
    ) AS duplicate_player_guardrail
FROM (
    SELECT player_name
    FROM gen_alpha.gold.genius_state
    GROUP BY player_name
    HAVING COUNT(*) > 1
);
