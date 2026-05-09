-- Step 1.0 mock leaguemate fragility seed.
-- Dev/test only. Seeds Gold valuation rows with owner metadata and Silver pick inventory.

INSERT INTO gen_alpha.silver.leaguemate_pick_inventory (
  league_id,
  owner_username,
  season,
  round,
  original_owner_username,
  pick_year,
  pick_label,
  protection_status,
  projected_bucket,
  inventory_source,
  verified_at,
  feature_quality_status,
  evidence_json
)
VALUES
('mock-productive-struggle-league', 'fragile_tanker', 2026, 1, 'fragile_tanker', 2027, 'fragile_tanker_2027_1st', 'UNPROTECTED', 'EARLY', 'mock_step_1_0', current_timestamp(), 'READY_FOR_MODELING', '{"source":"mock_step_1_0"}'),
('mock-productive-struggle-league', 'fragile_tanker', 2026, 3, 'fragile_tanker', 2027, 'fragile_tanker_2027_3rd', 'UNPROTECTED', 'UNKNOWN', 'mock_step_1_0', current_timestamp(), 'READY_FOR_MODELING', '{"source":"mock_step_1_0"}'),
('mock-productive-struggle-league', 'aging_contender', 2026, 1, 'aging_contender', 2027, 'aging_contender_2027_1st', 'UNPROTECTED', 'MID', 'mock_step_1_0', current_timestamp(), 'READY_FOR_MODELING', '{"source":"mock_step_1_0"}'),
('mock-productive-struggle-league', 'aging_contender', 2026, 2, 'aging_contender', 2026, 'aging_contender_2026_2nd', 'UNPROTECTED', 'UNKNOWN', 'mock_step_1_0', current_timestamp(), 'READY_FOR_MODELING', '{"source":"mock_step_1_0"}'),
('mock-productive-struggle-league', 'stable_contender', 2026, 1, 'stable_contender', 2027, 'stable_contender_2027_1st', 'UNPROTECTED', 'LATE', 'mock_step_1_0', current_timestamp(), 'READY_FOR_MODELING', '{"source":"mock_step_1_0"}'),
('mock-productive-struggle-league', 'stable_contender', 2026, 2, 'stable_contender', 2026, 'stable_contender_2026_2nd', 'UNPROTECTED', 'UNKNOWN', 'mock_step_1_0', current_timestamp(), 'READY_FOR_MODELING', '{"source":"mock_step_1_0"}'),
('mock-productive-struggle-league', 'stable_contender', 2026, 2, 'stable_contender', 2027, 'stable_contender_2027_2nd', 'UNPROTECTED', 'UNKNOWN', 'mock_step_1_0', current_timestamp(), 'READY_FOR_MODELING', '{"source":"mock_step_1_0"}');

INSERT INTO gen_alpha.gold.roster_valuation (
  valuation_id,
  valuation_date,
  player_id,
  player_name,
  position,
  nfl_team,
  roster_status,
  age_years,
  dynasty_trajectory,
  asset_tier_status,
  asset_tier_basis,
  qual_dominant_override,
  qual_rationale,
  internal_valuation,
  ktc_market_value,
  ktc_market_updated_at,
  feature_quality_status,
  framework_flags,
  evidence_json,
  source_version,
  calculated_at
)
VALUES
('mock-fragile-tanker-davante-adams', DATE '2026-05-03', 'mock-fragile-adams', 'Davante Adams', 'WR', 'LAR', 'STARTER', 33.0, 'CLIFF', 'DEPRECIATION_WATCH', 'Mock leaguemate aging WR cliff asset.', false, NULL, 2800.0, 4300.0, current_timestamp(), 'READY_FOR_MODELING', array('age_cliff', '2025_td_outlier'), '{"league_id":"mock-productive-struggle-league","owner_username":"fragile_tanker","source":"mock_step_1_0"}', 'mock_step_1_0', current_timestamp()),
('mock-fragile-tanker-tyreek-hill', DATE '2026-05-03', 'mock-fragile-hill', 'Tyreek Hill', 'WR', 'FA', 'BENCH', 32.0, 'CLIFF', 'DEPRECIATION_WATCH', 'Mock leaguemate distressed WR cliff asset.', false, NULL, 900.0, 1900.0, current_timestamp(), 'READY_FOR_MODELING', array('nfl_free_agent', 'medical_clearance_gate'), '{"league_id":"mock-productive-struggle-league","owner_username":"fragile_tanker","source":"mock_step_1_0"}', 'mock_step_1_0', current_timestamp()),
('mock-fragile-tanker-aging-rb', DATE '2026-05-03', 'mock-fragile-rb', 'Aging RB Anchor', 'RB', 'FA', 'STARTER', 27.5, 'CLIFF', 'DEPRECIATION_WATCH', 'Mock leaguemate aging RB cliff asset.', false, NULL, 3900.0, 5100.0, current_timestamp(), 'READY_FOR_MODELING', array('age_cliff'), '{"league_id":"mock-productive-struggle-league","owner_username":"fragile_tanker","source":"mock_step_1_0"}', 'mock_step_1_0', current_timestamp()),
('mock-aging-contender-wr', DATE '2026-05-03', 'mock-aging-wr', 'Aging WR Producer', 'WR', 'FA', 'STARTER', 29.0, 'DEPRECIATING', 'UNASSIGNED', 'Mock leaguemate depreciating WR.', false, NULL, 3600.0, 4000.0, current_timestamp(), 'READY_FOR_MODELING', array('approaching_age_cliff'), '{"league_id":"mock-productive-struggle-league","owner_username":"aging_contender","source":"mock_step_1_0"}', 'mock_step_1_0', current_timestamp()),
('mock-aging-contender-qb', DATE '2026-05-03', 'mock-aging-qb', 'Aging QB Producer', 'QB', 'FA', 'STARTER', 34.0, 'DEPRECIATING', 'UNASSIGNED', 'Mock leaguemate aging QB.', false, NULL, 4700.0, 4500.0, current_timestamp(), 'READY_FOR_MODELING', array('age_cliff'), '{"league_id":"mock-productive-struggle-league","owner_username":"aging_contender","source":"mock_step_1_0"}', 'mock_step_1_0', current_timestamp()),
('mock-stable-contender-wr', DATE '2026-05-03', 'mock-stable-wr', 'Stable Prime WR', 'WR', 'FA', 'STARTER', 25.0, 'PEAK', 'UNASSIGNED', 'Mock leaguemate prime WR.', false, NULL, 6100.0, 6000.0, current_timestamp(), 'READY_FOR_MODELING', array(), '{"league_id":"mock-productive-struggle-league","owner_username":"stable_contender","source":"mock_step_1_0"}', 'mock_step_1_0', current_timestamp());
