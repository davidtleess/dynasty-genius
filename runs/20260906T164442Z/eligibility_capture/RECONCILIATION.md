# Sleeper fantasy eligibility — reconciliation

Captured 2026-09-06T16:41:07.845290+00:00 from `https://api.sleeper.app/v1/players/nfl` (HTTP reused, 14,651,641 bytes, sha256 `97b15239da27…`, 12,226 players).

`fantasy_positions` is the placement authority. Unknown stays unknown. Flags classify, never suppress.

## Rookies (80 from the accepted forecast file)

- matched: 80 of 80 ({'name+position': 79, 'last_name+team+position+rookie': 1})
- eligibility known: 80; availability: {'rostered': 45, 'active_free': 33, 'inactive_free': 2}

| player | pick | draft position | nflverse current | Sleeper fantasy_positions | availability |
|---|---:|---|---|---|---|
| Max Bredeson | 159.0 | TE | RB | RB | active_free |

## Named players

| Sleeper id | name | Sleeper position | fantasy_positions | active | status | team | availability |
|---|---|---|---|---|---|---|---|
| 9502 | Tank Dell | WR | WR | True | Inactive | HOU | rostered |
| 12530 | Travis Hunter | DB | DB|WR | True | Active | JAX | rostered |

## Candidate available pool (DG-178 replacement census ids)

- ids: 271; availability: {'active_free': 251, 'inactive_free': 20}; eligibility unknown: 0; eligibility differs from Sleeper position: 2

All players: {'rows': 12226, 'fantasy_positions_missing': 333, 'active_flag_missing': 0}
