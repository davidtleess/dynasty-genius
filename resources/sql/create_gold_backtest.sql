-- Dynasty Genius Gold Layer: Backtest History
-- Catalog: gen_alpha
-- Schema: gold
--
-- Historical record of model predictions vs actual performance.
-- Part of the "Trust Flywheel" foundation.

CREATE SCHEMA IF NOT EXISTS gen_alpha.gold;

CREATE TABLE IF NOT EXISTS gen_alpha.gold.backtest_history (
    dg_id STRING NOT NULL COMMENT 'Canonical Dynasty Genius ID (e.g. josh_allen_qb_1996).',
    prediction_date DATE NOT NULL COMMENT 'Date the prediction was generated.',
    predicted_value DOUBLE NOT NULL COMMENT 'The value or rank predicted by the model at that time.',
    actual_points_next_12m DOUBLE COMMENT 'Actual fantasy points scored by the player in the 12 months following prediction_date.',
    error_delta DOUBLE COMMENT 'Difference between predicted and actual (predicted_value - actual_points_next_12m).',
    
    -- Metadata
    ingest_ts TIMESTAMP NOT NULL COMMENT 'Timestamp of recording the backtest result.'
)
USING DELTA
PARTITIONED BY (prediction_date)
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'dynasty_genius.layer' = 'gold',
  'dynasty_genius.purpose' = 'trust_flywheel'
);
