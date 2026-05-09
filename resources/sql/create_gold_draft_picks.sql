-- Dynasty Genius Gold Layer: Draft Picks
-- Catalog: gen_alpha
-- Schema: gold
--
-- Tracks pick year, round, and ownership history (original vs. acquired).

CREATE SCHEMA IF NOT EXISTS gen_alpha.gold;

CREATE TABLE IF NOT EXISTS gen_alpha.gold.draft_picks (
    league_id STRING NOT NULL COMMENT 'Unique league identifier.',
    owner_username STRING NOT NULL COMMENT 'Current owner username.',
    
    pick_year INT NOT NULL COMMENT 'The year of the draft (e.g. 2027).',
    pick_round INT NOT NULL COMMENT 'The round of the pick (1-5).',
    
    original_owner_username STRING COMMENT 'Original owner username (the "natural" owner).',
    
    is_acquired BOOLEAN NOT NULL COMMENT 'True if the pick was acquired via trade (owner != original_owner).',
    
    protection_status STRING COMMENT 'UNPROTECTED, TOP_3_PROTECTED, TOP_6_PROTECTED, UNKNOWN.',
    projected_bucket STRING COMMENT 'EARLY, MID, LATE, UNKNOWN.',
    
    -- Metadata
    ingest_ts TIMESTAMP NOT NULL COMMENT 'Timestamp of the last sync.'
)
USING DELTA
PARTITIONED BY (pick_year)
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'dynasty_genius.layer' = 'gold'
);

ALTER TABLE gen_alpha.gold.draft_picks
  ADD CONSTRAINT draft_picks_round_chk
  CHECK (pick_round IN (1, 2, 3, 4, 5));

ALTER TABLE gen_alpha.gold.draft_picks
  ADD CONSTRAINT draft_picks_protection_chk
  CHECK (protection_status IN ('UNPROTECTED', 'TOP_3_PROTECTED', 'TOP_6_PROTECTED', 'UNKNOWN'));

ALTER TABLE gen_alpha.gold.draft_picks
  ADD CONSTRAINT draft_picks_bucket_chk
  CHECK (projected_bucket IN ('EARLY', 'MID', 'LATE', 'UNKNOWN'));
