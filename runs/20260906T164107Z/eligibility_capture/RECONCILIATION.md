# Sleeper fantasy eligibility — reconciliation

Captured 2026-09-06T16:41:07.845290+00:00 from `https://api.sleeper.app/v1/players/nfl` (HTTP 200, 14,651,641 bytes, sha256 `97b15239da27…`, 12,226 players).

`fantasy_positions` is the placement authority. Unknown stays unknown. Flags classify, never suppress.

## Rookies (80 from the accepted forecast file)

- matched: 74 of 80 ({'name+position': 74, 'unmatched': 6})
- eligibility known: 74; availability: {'rostered': 41, 'active_free': 31, 'unknown_free': 6, 'inactive_or_retired_free': 2}

| player | pick | draft position | nflverse current | Sleeper fantasy_positions | availability |
|---|---:|---|---|---|---|
| Max Bredeson | 159.0 | TE | RB | RB | active_free |

## Named players

| Sleeper id | name | Sleeper position | fantasy_positions | active | status | team | availability |
|---|---|---|---|---|---|---|---|
| 9502 | Tank Dell | WR | WR | True | Inactive | HOU | rostered |
| 12530 | Travis Hunter | DB | DB|WR | True | Active | JAX | rostered |

## Candidate available pool (DG-178 replacement census ids)

- ids: 271; availability: {'active_free': 251, 'inactive_or_retired_free': 20}; eligibility unknown: 0; eligibility differs from Sleeper position: 2

All players: {'rows': 12226, 'fantasy_positions_missing': 333, 'active_flag_missing': 0}
