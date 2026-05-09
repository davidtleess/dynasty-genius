-- Dynasty Genius Silver Layer: Player Identity
-- Catalog: gen_alpha
-- Schema: silver
--
-- SCD Type 2 tracking for canonical player identities across sources.

CREATE SCHEMA IF NOT EXISTS gen_alpha.silver;

CREATE TABLE IF NOT EXISTS gen_alpha.silver.player_identity (
    -- Canonical ID
    dg_id STRING NOT NULL COMMENT 'Canonical Dynasty Genius ID (e.g. josh_allen_qb_1996).',
    
    -- Player Attributes
    full_name STRING NOT NULL COMMENT 'Full display name of the player.',
    position STRING NOT NULL COMMENT 'Positional grouping (QB, RB, WR, TE).',
    birth_date DATE COMMENT 'Verified birth date for age calculations.',
    nfl_team STRING COMMENT 'Current NFL team abbreviation.',
    jersey_number STRING COMMENT 'Current or last known jersey number.',
    
    -- Source IDs
    sleeper_id STRING COMMENT 'Sleeper platform player ID.',
    pff_id STRING COMMENT 'Pro Football Focus player ID.',
    pfr_id STRING COMMENT 'Pro Football Reference player ID.',
    playerprofiler_id STRING COMMENT 'PlayerProfiler player ID.',
    
    -- Verification Metadata
    verification_status STRING NOT NULL COMMENT 'PENDING, VERIFIED, or CONFLICT status of the identity mapping.',
    last_updated_ts TIMESTAMP COMMENT 'Timestamp of the last update to any source mapping.',
    
    -- SCD Type 2 tracking
    effective_from TIMESTAMP NOT NULL COMMENT 'Start of validity for this identity version.',
    effective_to TIMESTAMP COMMENT 'End of validity for this identity version (NULL if current).',
    is_current BOOLEAN NOT NULL COMMENT 'Flag indicating if this is the active identity record.'
)
USING DELTA
PARTITIONED BY (position)
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'dynasty_genius.layer' = 'silver'
);

ALTER TABLE gen_alpha.silver.player_identity
  ADD CONSTRAINT player_identity_position_chk
  CHECK (position IN ('QB', 'RB', 'WR', 'TE', 'FB', 'K', 'DST', 'IDP', 'OTHER'));

ALTER TABLE gen_alpha.silver.player_identity
  ADD CONSTRAINT player_identity_verification_status_chk
  CHECK (verification_status IN ('PENDING', 'VERIFIED', 'CONFLICT'));
