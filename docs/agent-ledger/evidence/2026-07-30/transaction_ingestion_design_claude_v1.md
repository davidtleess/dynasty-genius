# League transaction ingestion — design note (build from this; not for review)

**Claude Code, 2026-07-30. David's word 20:31: "go - build transaction ingestion". Layer 1.**
One page by instruction. Review happens on the code, once, when it is green.

## The hole

Sleeper's `/league/{id}/transactions/{leg}` has never been called in this product's history. No
transaction has ever been ingested or persisted anywhere. Layer 4 (context — manager behaviour, per
the 2026-07-30 order) has no substrate.

## Acceptance (David's words)

Every add, drop, waiver claim and trade, with dates, players resolved to our identities rather than
raw Sleeper ids, refreshing without anyone typing a command.

## What the live endpoint actually returns — measured, not assumed

Probed 2026-07-30 against league `1314363401744416768`: **67 transactions, all in leg 1**
(season `2026`, `season_type` `pre` — off-season moves land in leg 1). Five facts the contract must
handle, each observed in the captured fixture:

1. **`type` has FOUR values here, not three** — `free_agent` 34 · `waiver` 24 · `trade` 7 ·
   **`commissioner` 2**. Commissioner moves are real roster changes and are ingested and labelled,
   not discarded as unknown.
2. **`adds` / `drops` are `null`, not `{}`**, whenever a side is empty. Every reader must be null-safe.
3. **`status` includes `failed`** (a rejected waiver claim). A failed claim is a real *behaviour*
   signal but did not change a roster. It is stored with its status and never silently counted as
   something that happened.
4. **Trades carry `draft_picks`** with `round`/`season`/`owner_id`/`previous_owner_id`, and a
   `waiver_budget` array for FAAB. Pick movement is part of "what a manager did".
5. **`created` / `status_updated` are epoch milliseconds**; `settings.waiver_bid` carries FAAB.

## Design

**Adapter** `src/dynasty_genius/league_transactions.py`, the one adapter for this source (01 §Source
Adapter Rules): fetch → **write the raw snapshot before parsing** → normalize → store → status marker.

**Two tables, append-only SQLite** at `app/data/league_transactions.db`, mirroring
`model_forward_capture_store`:

- `league_transaction` — one row per transaction: ids, `leg`, `type`, `status`, ISO-UTC `created_at`
  / `status_updated_at`, `creator_user_id`, `roster_ids`, `waiver_bid`, and the **raw JSON preserved**.
- `league_transaction_movement` — one row per moved asset: `asset_type` `player`|`pick`, `action`
  `add`|`drop`|`pick_acquire`, `roster_id`, the **manager** (`owner_user_id` + `display_name`), and
  for players `sleeper_player_id`, `player_key`, `player_name`, `position`, `team`,
  `identity_status`. Every movement carries its parent `transaction_status`.

**Identity** resolves against the existing league snapshot — the product's live identity surface —
using the existing `sleeper:<id>` key form. Unresolved ids are **kept, labelled `unresolved`, and
counted**, never dropped (01 §Identity Resolution). **Zero resolutions refuses the run**, following
the identity-crosswalk hardening precedent.

**Idempotent by `transaction_id`**: re-ingesting the same leg changes no row count. This is what
makes a scheduler safe to add later.

## Boundaries held

No plist, no scheduler, no change to any existing producer, no analysis, no UI, no trade-partner-score
rewiring. The capture is **callable** (`scripts/run_league_transaction_capture.py`) so a scheduler can
be added on a later word. League id via the existing `DYNASTY_SLEEPER_LEAGUE_ID` env convention; no
new config, no secrets.

**Backup-manifest coverage is deliberately DEFERRED (David, 2026-07-30).** The manifest is read from
disk at run time, so an entry present only in a working tree was already live to the next scheduled
backup — and that run is his clean baseline. This store is rebuildable from the public Sleeper API in
seconds; the baseline is not rebuildable at all. The entry returns when a scheduler word lands and the
store begins accruing history the API no longer serves. Both guards stay armed meanwhile: the
manifest-coverage anti-rot test catches a present-but-uncovered store, and this thread's contract test
fails if the entry reappears without that decision.
