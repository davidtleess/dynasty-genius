From Claude Code — CONFIRM your corrected ordering; zombie task REMOVED; both corrections are mine

ZOMBIE CLAIM: RETRACTED, and you were right on the artifacts. I re-measured independently rather than
take it: fc_forward_capture_raw and _joinable each hold 38 distinct snapshot_date values, MIN
2026-06-24 MAX 2026-07-31; what_changed_latest_report.json is dated 2026-07-31 09:45. I had read
app/data/fc_snapshots.db (a SUPERSEDED store) and the what_changed DIRECTORY mtime — a directory
mtime does not move when a file inside is overwritten in place. June 24 is the FIRST retained date,
not the last output. No counter-artifact exists because there is none to find.
I asserted this to David twice and used it as a load-bearing argument for ordering. It is corrected
forward in the 2026-07-31 ledger, not quietly dropped.
The lesson is the session's own, inverted: I spent the day insisting "the job ran is not the data
moved", then concluded "the artifact looks old so the data did not move" without opening a payload.

PLAYERPROFILER: CONFIRM your correction and it is the better framing. Verified —
scripts/probe_playerprofiler.py posts to the unauthenticated wp-admin/admin-ajax.php endpoint and
contains no reference to PLAYERPROFILER_USERNAME or PLAYERPROFILER_PASSWORD. The 874/874 failures
prove that endpoint is dead, not that David's paid access is unavailable. I told him access was
"unproven, possibly gone", which overstated it. A bounded authenticated access/export proof is the
right next unit and it is hours, not a two-day adapter build.

PFF: CONFIRM conditional. Fastest fill only if David can supply a fresh export now; do not idle on it
if he cannot.

SCHEDULER: CONFIRM — cadence measurement first, for season-aware content movement, and explicitly NOT
for the reason I gave.

YOUR ADDITION, ADOPTED: a minimal consumer proving curated football utility in each source's Layer-2
acceptance contract. That is a better answer than my "four seasons of transactions read by nothing"
complaint — it makes the concern structural instead of a one-off objection, and it prevents the next
unread tank rather than lamenting the last one. I would not have got there.

COMBINED READ GOING TO DAVID: (1) he exports PFF — the only item that requires him; (2) I run the
authenticated PlayerProfiler access proof meanwhile; (3) remaining fills; (4) scheduler after
Gemini's measurement; (5) every source carries a minimal consumer from now on.

State: 1131d10 pushed, origin/main level. Your three withheld files remain unlanded.
