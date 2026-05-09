-- Step 0.8 mock market consensus seed.
-- Dev/test only. This lets the Model Accuracy Dashboard render Ryan Williams
-- without treating consensus as verified live market data.

INSERT INTO gen_alpha.silver.market_consensus_values (
  asset_id,
  player_name,
  position,
  draft_class,
  source,
  market_value,
  market_rank,
  consensus_tier_label,
  consensus_updated_at,
  feature_quality_status,
  evidence_json
)
VALUES (
  'mock-ryan-williams',
  'Ryan Williams',
  'WR',
  2027,
  'mock_market_consensus',
  8800.0,
  3,
  'ANCHOR',
  current_timestamp(),
  'READY_FOR_MODELING',
  '{"source":"mock_step_0_8","purpose":"Model Accuracy Dashboard test row; replace with KTC/DynastyNerds consensus"}'
),
(
  'mock-arch-manning',
  'Arch Manning',
  'QB',
  2026,
  'mock_market_consensus',
  9500.0,
  1,
  'ANCHOR',
  current_timestamp(),
  'READY_FOR_MODELING',
  '{"source":"mock_step_0_8","dg_id":"arch_manning_qb_2005"}'
),
(
  'mock-jeremiah-smith',
  'Jeremiah Smith',
  'WR',
  2027,
  'mock_market_consensus',
  9200.0,
  2,
  'ANCHOR',
  current_timestamp(),
  'READY_FOR_MODELING',
  '{"source":"mock_step_0_8","dg_id":"jeremiah_smith_wr_2005"}'
),
(
  'mock-nico-iamaleava',
  'Nico Iamaleava',
  'QB',
  2026,
  'mock_market_consensus',
  8500.0,
  4,
  'READY',
  current_timestamp(),
  'READY_FOR_MODELING',
  '{"source":"mock_step_0_8","dg_id":"nico_iamaleava_qb_2004"}'
);
