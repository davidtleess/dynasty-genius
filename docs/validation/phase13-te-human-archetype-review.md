# Phase 13 TE Human Archetype Review

Date: 2026-05-16
Reviewer: David
Status: Calibration evidence only

## Purpose

This note records David's football-instinct calibration labels for selected TEs after the
Phase 13.3.1 snap-alignment rubric and residual validation artifact were generated.

These labels are not model inputs. They are review evidence for a future, separately approved
TE archetype feature bake-off.

## David Labels

### Clear Receiving Specialists

- Kyle Pitts
- Isaiah Likely
- Greg Dulcich

### Blocking Specialists

- Dawson Knox
- Jeremy Ruckert
- Darnell Washington

### Complete TEs

- Sam LaPorta
- T.J. Hockenson
- Dalton Schultz
- Trey McBride
- Cade Otton
- Jake Ferguson

## Interpretation

The review exposes a taxonomy problem in the first-pass rubric:

- The current `receiving_leaning` label is an alignment label, not a fantasy receiving-utility label.
- The current `ambiguous` label mixes true complete TEs with unclear role players.
- The next validation design should separate at least two axes:
  - `alignment_archetype`: detached / balanced / inline
  - `fantasy_role_archetype`: receiving_specialist / blocking_specialist / complete_te / unclear_role

## Current Rubric Conflict Examples

| Player | David Label | Current Step 0 Label | Conflict |
| --- | --- | --- | --- |
| Dawson Knox | blocking_specialist | receiving_leaning | Detached alignment without strong receiving utility. |
| Jeremy Ruckert | blocking_specialist | receiving_leaning | Detached threshold likely over-captures low-efficiency role players. |
| Darnell Washington | blocking_specialist | ambiguous | Inline threshold likely too strict for obvious blocking profiles. |
| Dalton Schultz | complete_te | ambiguous | `ambiguous` can represent a real two-way profile, not uncertainty. |
| Trey McBride | complete_te | ambiguous | Same: balanced alignment plus strong receiving efficiency should not be treated as unclear. |
| T.J. Hockenson | complete_te | ambiguous | Same: balanced alignment plus strong receiving efficiency should not be treated as unclear. |
| Cade Otton | complete_te | ambiguous | Human label says complete, but statistical efficiency is modest; useful review case. |
| Jake Ferguson | complete_te | ambiguous | Human label says complete; likely needs two-way role context rather than only YPRR. |

## Proposed Follow-Up

For Task 13.3.2, do not add the current single `archetype` field directly as a model feature.
Instead, run a bake-off of derived TE taxonomy candidates:

1. Snap-only alignment bucket: receiving / ambiguous / blocking.
2. Two-axis taxonomy: alignment bucket plus receiving utility flag from YPRR/TPRR.
3. Complete-TE detector: balanced alignment plus efficiency or target-volume support.
4. Conservative role-risk flag: detached by alignment but weak YPRR/TPRR.

Acceptance should require held-out improvement over the current TE baseline and no TE promotion
unless the normal promotion gates pass.

## Governance

- Diagnostic only: yes
- Model features changed: no
- TE promotion changed: no
- Market data used: no
- PFF grades used: no
- Player-level PFF rows emitted: no
