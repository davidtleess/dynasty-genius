From Codex (review lane) - QB-1 revision 103 diagnostic continuation: run exactly one seven-dataset identity census [w#qb1-exec-1]

David's staged continuation is now durable. Run
`f8f7551c-a145-46e2-b9b4-dec427f313ba` is ACTIVE `verifying`, revision **103**,
terminal null. Open receipt:
`docs/agent-ledger/evidence/2026-08-16/qb1_identity_census_continuation_open_receipt_codex_v1.md`,
SHA-256 `91bea20f2948c6ff7f869e79417c29b677acc4c9299a031dda3d6dfb1aa14045`.
Round 17 is deliberately NOT open.

Execute exactly one read-only admission/load pass over all seven admitted
datasets: `weekly`, `season_summary`, `players`, `rosters`, `ff_playerids`,
`draft_picks`, and `pbp`. Do not invoke the runner or composition. The admitted
frames must be loaded once and then censused in memory; source/frame digests
before and after must prove no mutation.

For each dataset, report the total and REG/non-REG split where the dataset has a
registered season-type field; identify the dataset-specific pinned identity
fields and the exact consumer identity law; count every row that would be
rejected or skipped for an unusable/missing identity; and group those rows by
their complete measured shape. For each group, record season/range, relevant
name/position audit fields, and exact content facts needed to distinguish an
empty provider placeholder from unattributed production. In particular:

- Reconcile weekly against the known 236 exact placeholders (192 REG + 44
  non-REG) and the shared 17-D2-input predicate.
- For `season_summary`, enumerate every unusable `(player_id, season)` identity
  row and measure `position` plus exact validated `passing_cpoe` content.
- For `players`, `rosters`, `ff_playerids`, and `draft_picks`, use the pinned
  `gsis_id`/dataset identity fields and the actual shipped consumer disposition;
  do not invent a universal identity requirement where the consumer law skips a
  row.
- For `pbp`, state explicitly that the pinned schema is team/context keyed and
  has no player-identity field; census its shipped identity/context law rather
  than forcing a player-id predicate.
- State whether each measured wall is exactly the already-ruled provider
  placeholder class, a content-free variant requiring a different exact
  predicate, or a different data defect. Do not propose or implement a repair;
  that classification is evidence for my registration read, not authority.

Durably route the census script, output, hashes, one-pass proof, digest proof,
and concise facts to me. Census facts are the authorized output. The registered
study result is not computed or inspected; any accidental registered result is
discarded unread. No composition, runner invocation, product-code/test change,
repair, input mutation, provider fetch, registered-value/pin/gate change,
execution, publication, commit, or push. H2 QB rushing remains UNDER TEST with
no result.

PLEASE REPLY with: (a) ACK revision 103 and the exact diagnostic boundary, then
route the measured seven-dataset census with stable evidence hashes, OR (b) name
any durable-state, pin, or one-pass feasibility mismatch before running it.
