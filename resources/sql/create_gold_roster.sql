-- Dynasty Genius Gold Layer: Roster
-- Catalog: gen_alpha
-- Schema: gold
--
-- Denormalized roster state joining identity with league ownership.

CREATE SCHEMA IF NOT EXISTS gen_alpha.gold;

CREATE TABLE IF NOT EXISTS gen_alpha.gold.roster (
    league_id STRING NOT NULL COMMENT 'Unique league identifier.',
    roster_id INT NOT NULL COMMENT 'Roster index within the league.',
    owner_id STRING NOT NULL COMMENT 'Unique owner/manager identifier.',
    
    -- Joined from silver.player_identity
    dg_id STRING NOT NULL COMMENT 'Canonical Dynasty Genius ID (e.g. josh_allen_qb_1996).',
    player_name STRING NOT NULL COMMENT 'Full display name of the player.',
    position STRING NOT NULL COMMENT 'Positional grouping (QB, RB, WR, TE).',
    nfl_team STRING COMMENT 'Current NFL team abbreviation.',
    
    -- Roster Context
    roster_status STRING NOT NULL COMMENT 'STARTER, BENCH, IR, TAXI, or WATCHLIST.',
    
    -- Metadata
    ingest_ts TIMESTAMP NOT NULL COMMENT 'Timestamp of the last roster sync.'
)
USING DELTA
PARTITIONED BY (league_id)
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'dynasty_genius.layer' = 'gold'
);

ALTER TABLE gen_alpha.gold.roster
  ADD CONSTRAINT roster_status_chk
  CHECK (roster_status IN ('STARTER', 'BENCH', 'IR', 'TAXI', 'WATCHLIST'));

ALTER TABLE gen_alpha.gold.roster
  ADD CONSTRAINT roster_position_chk
  CHECK (position IN ('QB', 'RB', 'WR', 'TE', 'FB', 'K', 'DST', 'IDP', 'OTHER'));
