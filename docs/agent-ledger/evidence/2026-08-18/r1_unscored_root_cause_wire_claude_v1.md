From Claude (write lane) — AWARENESS: the 115 unscored players are a feature-store gap, not a model gap [w#r1-unscored]

No action requested. Facts only, so nobody re-derives this a fourth time. Nothing is implemented and
no work is opened; next action is David's.

David asked why the model has no opinion on players we hold years of data for. It does. The scores
are destroyed downstream of a degraded feature store.

Measured chain, each step reproduced against the served artifact and the runtime feature CSV:

1. app/data/features_runtime/engine_b_features_runtime.csv holds feature seasons 2018, 2019, 2020,
   2021, 2022, 2023, 2025. 2024 is absent entirely.
2. The 2025 rows are a partial season. Garrett Wilson: 2022 games_t=17, 2023 games_t=17, no 2024
   row, 2025 games_t=7.
3. games_t < ENGINE_B_MIN_GAMES_T routes off Engine B to the dead-window blend
   (pvo_assembler.py:394-425).
4. The blend needs an Engine A prior; Engine A needs draft capital; nfl_draft_round is None for
   every active player (the same absence recorded in 05 section 4).
5. No Engine A means dynasty_value_score = None (pvo_assembler.py:458-465). projection_2y is
   untouched by that path and survives.

Three independent counts agree on 115: 2025 feature rows with games_t < 8 = 115; served rows with
dynasty_value_score None AND a present projection_2y = 115; Studio's 1-7 game band = 115 of 583,
stable across eleven days.

So every one of the 115 already has a projection. Garrett Wilson 11.255 PPG, Braelon Allen 4.899
PPG. Both render blank because only the COMPOSITE died.

This is the downstream half of the health defect fixed today in 62768d0. feature_refresh's own
stream_provenance records participation loaded_empty (ValueError) and pbp, player_stats and
snap_counts all on 2025 cache, with only rosters live - and it graded fresh on
embedded_timestamp_fresh until this afternoon. Those degraded inputs built this store.

R2 is confirmed separate and is an identity failure. Tank Dell (sleeper_id 9502) has dg_player_id
None in the served artifact, so he joins to nothing: zero rows in the model capture at capture_date
2026-08-18, while the market capture carries him at 1204 rank 76. He cannot be graded by the
realized-outcome scorer at all.

Two distinct causes render one blank column and the surface does not distinguish them: no opinion
(Wilson, Allen - no score exists) versus opinion withheld (Jeanty 75.3, Rasheen Ali 20.7 - score
exists, the Roster Audit gate suppresses actives by design, which Studio verified as deliberate).

Correction on my own record: I earlier accepted games_t=7 as a fact about Garrett Wilson. It is a
fact about our pipeline.

Candidate fix, not opened: rebuild the feature store from ff_opportunity (47,282 weekly rows,
2018-2025, already on disk), with surfacing points per game as an independent guard so a projection
is never invisible again.

Durable record: docs/agent-ledger/2026-08-18.md, entry 21:0x ET. [w#r1-unscored]
