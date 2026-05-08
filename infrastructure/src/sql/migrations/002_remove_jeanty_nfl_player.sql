-- Migration: Remove Ashton Jeanty (2025 NFL rookie, Las Vegas Raiders)
-- Reason: Hunter/Campbell Amendment violation - NFL player incorrectly listed as 2026 prospect
-- Date: 2026-05-04
-- Author: Genie (verified by user)
-- Related: Sprint 0.5 Data Integrity Sweep

-- Step 0: Allow removal rows to record new_dvu = NULL.
-- Removal semantics require a nullable post-change DVU.
ALTER TABLE gen_alpha.gold.anchors_change_log
ALTER COLUMN new_dvu DROP NOT NULL;

-- Step 1: Log the removal to anchors_change_log
INSERT INTO gen_alpha.gold.anchors_change_log (
    player_name,
    old_dvu,
    new_dvu,
    primary_data_anchor,
    strategy_commit_hash,
    executing_agent,
    timestamp,
    change_type,
    compliance_status,
    notes
) VALUES (
    'Ashton Jeanty',
    95.0,
    NULL,
    '2025 NFL Draft - Las Vegas Raiders (Round 1, Pick TBD)',
    'strategy_pr_merge_sha',
    'Codex',
    CURRENT_TIMESTAMP(),
    'REMOVAL',
    'APPROVED',
    'Hunter/Campbell Amendment: NFL player incorrectly listed as 2026 prospect. Jeanty was drafted by Raiders in 2025 NFL Draft and is entering his second year. Outside scope of pre-draft valuation framework.'
);

-- Step 2: Remove from anchors table
DELETE FROM gen_alpha.gold.anchors
WHERE player_name = 'Ashton Jeanty';

-- Step 3: Verification (should return 0 rows)
SELECT
    'Jeanty Removal Verification' as check_name,
    COUNT(*) as jeanty_count,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS: Jeanty removed successfully'
        ELSE 'FAIL: Jeanty still present in anchors'
    END as status
FROM gen_alpha.gold.anchors
WHERE player_name = 'Ashton Jeanty';

-- Step 4: Verify anchors count (should be 7)
SELECT
    'Total Anchors Verification' as check_name,
    COUNT(*) as total_anchors,
    CASE
        WHEN COUNT(*) = 7 THEN 'PASS: 7 anchors remain'
        ELSE CONCAT('UNEXPECTED: ', CAST(COUNT(*) AS STRING), ' anchors found')
    END as status
FROM gen_alpha.gold.anchors;
