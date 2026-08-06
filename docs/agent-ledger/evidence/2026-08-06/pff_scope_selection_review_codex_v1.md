# PFF scope-selection review — Codex v1

**Reviewed commit:** `529b187eac719386d6b7a58dd3220c5d63336857` (unpushed at review time)  
**Layer:** Layer 1 data inventory  
**Verdict:** **NOT CLEAR**  
**Scope:** read-only validation of `app/data/pff_exports/pff_unique_payload_inventory.csv` and its
149 referenced canonical CSV payloads. No source payload, catalog row, code, scheduler, or consumer
was changed.

## What independently reproduces

- 149 payloads, 134,392 payload rows, and 125 distinct `(league, report, season)` keys.
- Scope counts: `REGPO=75`, `REG=72`, `POST=1`, `PRE=1`.
- `preferred_for_selection=True` on 146 payloads; those payloads sum to 127,842 rows.
- Applying the stated policy—choose one non-`PRE` payload per key by scope rank
  `REGPO > REG > POST`, breaking first by row count, then retain `PRE` separately—selects 125
  non-`PRE` payloads plus one `PRE` payload and yields 106,867 rows.
- `134,392 - 106,867 = 27,525`; that arithmetic difference is 20.4811%, which rounds to 20.5%.

Those facts validate the arithmetic output of the proposed selection policy. They do **not**
validate the catalog's stronger claims that 27,525 rows are double-counted, that 134,392
"overstates" an observation total, or that 106,867 is canonical.

## P1 — the scope count is misstated

There are 21 keys with more than one **payload**, but only 20 keys with more than one **scope**.
The remaining key, NCAA `receiving_depth` 2017, has three `REGPO` payload variants and no second
scope. The ledger sentence "21 keys carry more than one scope" is false.

## P2 — row-level subset assumption is falsified

For every payload discarded by the proposed policy, I compared `player_id` membership and every
CSV field against the selected `REGPO` payload for the same key. Across the 23 discarded payloads
and their 27,525 rows:

- 27,524 discarded player memberships also occur in the selected payload;
- one player (`player_id=55173`, NCAA `receiving_summary` 2017 `REG`) is absent from `REGPO`;
- 18,006 shared-player rows are field-for-field identical;
- **9,518 shared-player rows differ in at least one field**.

Therefore, the discarded rows are not literally a subset of the selected rows. The widest-scope
policy discards distinct aggregate values and one distinct player membership. For example:

- NCAA `receiving_summary` 2017: 2,078 shared players, 942 changed shared rows, one `REG`-only
  player, and 25 `REGPO`-only players.
- NFL `passing_pressure` 2018: all 111 players are shared, but 23 rows change.
- NCAA `passing_depth` 2025 `POST` versus `REGPO`: all 140 postseason players occur in `REGPO`, but
  122 rows change.
- NFL `receiving_depth` 2025: all 498 `REG` players occur in `REGPO`, but 161 rows change.

The raw sum is valid only at its actual payload/scope grain. If the target analytical grain omits
scope, these are alternate or conflicting aggregates that require a semantic selection policy;
they are not demonstrated duplicates.

## P3 — the stated tie rule is incomplete

Same-scope, same-row-count variants are not identical:

- NCAA `receiving_depth` 2017 has three 2,103-row `REGPO` payloads; the latter two differ from the
  first for two players and one player respectively.
- NCAA `receiving_summary` 2025 has two 2,344-row `REG` payloads differing for one player.

"Ties broken by row count" cannot select deterministically among these variants. The inventory's
`preferred_for_selection` flag distinguishes these particular same-scope variants, even though it
cannot resolve the cross-scope problem. A canonical rule still needs an explicit tie order and a
conflict disposition.

## P4 — `PRE` is a separate phase, not a row-disjoint cohort

For NFL `passing_pressure` 2025, `PRE` and `REGPO` each have 106 player rows, but only 63 player IDs
overlap; 43 are exclusive to each payload. All 63 shared players differ on at least one common
field, and the payload schemas differ (165 versus 197 columns). The raw CSV has no `scope` column,
so retaining both requires scope to be preserved in normalized provenance/keying. Keeping `PRE`
separately is defensible, but "disjoint" must refer to game phase, not row or player identity.

## P5 — the catalog has no §3.3

The commit repeatedly cites "§3.3", but `docs/layer-1-data-inventory-catalog.md` contains no
`### §3.3` heading or rule body. The detailed rule exists only in the ledger entry. The canonical
catalog therefore has dangling citations and does not contain the section it claims was added.

## Publication boundary

The figure 106,867 may be published now only as **"row count produced by the proposed
widest-scope file-selection policy"**. It must not replace 134,392 as a canonical observation
count, coverage count, deduplicated count, or proved 20.5% overstatement.

The row-level check did gate those stronger uses, and it failed. Closing the blocker now requires:

1. define the intended analytical grain, including whether `scope` is part of the key;
2. define which scope answers the named consumer decision rather than assuming widest is best;
3. resolve the one narrow-only player and the 9,518 changed aggregates;
4. define deterministic same-scope tie/conflict handling;
5. preserve `PRE` scope in provenance/keying if it remains an additional observation family.

## CH1–CH5 status

CH1–CH5 were already accepted, integrated, and recorded in
`layer1_source_publish_cadence_disposition_codex_v2.md`; they are not outstanding:

- CH1: accepted HIGH—participation can cap all five frames and silently remove current-season data.
- CH2: accepted—B12 automatic capture remains deferred pending compressed exact storage,
  content/no-change logic, a numeric retention ceiling, and an as-of replay contract.
- CH3: accepted—the successful backup clears the failed-marker precondition only.
- CH4: accepted—2025 injuries are post-hoc archive coverage; a replacement provider remains
  conditional on an in-season Sleeper completeness test.
- CH5: accepted—the provider game-data and postseason archive-discovery calendars are distinct.

The current source-cadence artifact SHA-256 is
`2d1fe261b8c88a75091ca48e0951348d64b26bee7696bc28a8abaaa8ff2387fe`.

