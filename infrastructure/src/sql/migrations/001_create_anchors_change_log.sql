-- Sprint 0.5 governance migration: anchor valuation audit trail
-- All gen_alpha.gold.anchors changes must be backed by committed strategy
-- documentation and recorded here before production application.

CREATE TABLE IF NOT EXISTS gen_alpha.gold.anchors_change_log (
    player_name STRING NOT NULL COMMENT 'Canonical player name from gen_alpha.gold.anchors',
    old_dvu FLOAT COMMENT 'Previous DVU value before the governed anchor change',
    new_dvu FLOAT NOT NULL COMMENT 'New DVU value after the governed anchor change',
    primary_data_anchor STRING NOT NULL COMMENT 'Verified quantitative evidence or primary source driving the change',
    strategy_commit_hash STRING NOT NULL COMMENT 'Git commit SHA authorizing the strategy or reconciliation',
    executing_agent STRING NOT NULL COMMENT 'Agent that executed or coordinated the change: Claude, Codex, or Genie',
    `timestamp` TIMESTAMP NOT NULL COMMENT 'UTC timestamp when the change was recorded',
    change_type STRING NOT NULL COMMENT 'Change category such as DATA_DRIVEN_OVERRIDE, MEDICAL_QUALITATIVE_OVERRIDE, or CORRECTION',
    compliance_status STRING NOT NULL COMMENT 'Compliance state such as PENDING_REVIEW, APPROVED, APPLIED, or REJECTED',
    notes STRING COMMENT 'Free-form audit context, caveats, or reviewer notes',
    change_date DATE GENERATED ALWAYS AS (CAST(`timestamp` AS DATE)) COMMENT 'Generated partition date derived from timestamp'
)
USING DELTA
PARTITIONED BY (change_date)
COMMENT 'Governed audit log for gen_alpha.gold.anchors DVU changes.'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true',
    'dynasty_genius.governance_layer' = 'gold',
    'dynasty_genius.iac_required' = 'true',
    'dynasty_genius.manual_gold_writes_allowed' = 'false'
);
