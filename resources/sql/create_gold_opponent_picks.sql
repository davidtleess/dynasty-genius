-- Dynasty Genius Gold Layer: Opponent Picks
-- Catalog: gen_alpha
-- Schema: gold
--
-- Tracks pick assets owned by opponents, joined with prospect identity.
-- Part of the opponent fragility lens track.

CREATE SCHEMA IF NOT EXISTS gen_alpha.gold;

CREATE TABLE IF NOT EXISTS gen_alpha.gold.opponent_picks (
    league_id STRING NOT NULL COMMENT 'Unique league identifier.',
    owner_id STRING NOT NULL COMMENT 'Unique owner/manager identifier of the opponent.',
    owner_display_name STRING COMMENT 'Display name of the opponent.',
    
    -- Pick Details
    pick_year INT NOT NULL COMMENT 'The year of the draft (e.g. 2027).',
    pick_round INT NOT NULL COMMENT 'The round of the pick (1-5).',
    pick_slot INT COMMENT 'The specific pick slot (1-12) if known/projected.',
    
    -- Identity Join (Joined from silver.player_identity)
    -- This represents the prospect identified or projected for this pick slot.
    dg_id STRING COMMENT 'Canonical Dynasty Genius ID of the projected or assigned prospect.',
    
    -- Context
    is_acquired BOOLEAN NOT NULL COMMENT 'True if the opponent acquired this pick via trade.',
    original_owner_id STRING COMMENT 'Original owner identifier.',
    
    -- Metadata
    ingest_ts TIMESTAMP NOT NULL COMMENT 'Timestamp of recording this pick state.'
)
USING DELTA
PARTITIONED BY (pick_year)
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'dynasty_genius.layer' = 'gold'
);

ALTER TABLE gen_alpha.gold.opponent_picks
  ADD CONSTRAINT opponent_picks_round_chk
  CHECK (pick_round IN (1, 2, 3, 4, 5));
