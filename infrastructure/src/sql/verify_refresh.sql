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
