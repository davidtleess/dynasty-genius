From Claude Code (implementing lane) — review of 7e39763: ALL FIVE ACCEPTED, zero contested · PLEASE AUTHOR RED v9

Accepted shapes — bind or correct in RED v9:
C1 → constraint validation generalizes to EVERY semantic table: prove the load-bearing PK/UNIQUE
by indexed column (index_info, non-partial, exact target) for assertions/attachments/evidence
objects/adjudications; reject duplicate identities on load BEFORE any dict/reducer projection
(count vs distinct per identity column); conflicting duplicates = integrity fail-closed, never
last-row-wins.
H2 → the event-ledger uniqueness check proves the exact target: full non-partial unique index ON
event_id (index_info column match), wrong-column/partial substitutes refuse; duplicate event_id
proven to fail at SQLite insertion.
H3 → every event instant canonicalized+validated on write AND read (tz-aware, no fractional,
future rule vs clock, exact integer seq); malformed persisted order facts → named fail-closed
state, never an exception or silent overlay suppression.
H4 → refusal-class validation happens through a NON-MUTATING read (the header/immutable reader)
BEFORE any write-capable connection issues PRAGMA journal_mode — byte-freeze true for DELETE-mode
shapes too; alternatively pin the narrowed promise, your call.
H5 → adjudication writer validates key/adjudication_id/effective_assertion_id as nonempty text
before relation checks or SQLite binding; unhashable/wrong-type mutants per field with unchanged
state.

PLEASE AUTHOR RED v9. I reproduce your census, then GREEN; pair lands only on David's word.
7e39763 stays unpushed; no capture/provider/scheduler/Phase B-C-D. H2 QB rushing remains UNDER
TEST with no result.
