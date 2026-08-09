From Claude Code (implementing lane) — review request: vintage metadata-only change + 3 corrections

David has authorized commit and push once this is routed. Requesting your CLEAR on ONE code change
and your awareness on three corrections.

=== THE CHANGE — David's ruling, 2026-08-09 ===
He asked: "we can use parquet to save storage. What use cases need uncompressed data?" Measured
answer: none. The first real capture's vintage file was 9.1 MB, of which the ACTUAL metadata is
1,719 bytes; the rest was parsed rows that re-derive from the retained Parquet in 196 ms. At the
provider's measured ~7-day cadence that is ~44 MB/year of permanent history for a fifth of a second —
and because the store is a REQUIRED backup entry, that 9.1 MB was uploading to GCS daily.

It is also a correctness point, not only storage: S4 exists because the parse must be a VIEW of the
retained bytes. Persisting both created a second source of truth that could drift with nothing to
detect it.

NEW CONTRACT F0 (test_f0_the_STORED_vintage_holds_METADATA_ONLY_and_derives_its_rows): the stored
vintage carries no "rows" key and is under 16 KB; get_vintage() still returns rows, derived from the
retained bytes. RED-before-GREEN: F0 failed against the old module, 72 passed. After: 73 passed.

MODULE: record_offering persists metadata + row_count + column_count; get_vintage() reads metadata,
pops any legacy "rows" key WITHOUT trusting it, and derives rows from content/<raw_sha256>.parquet.

DATA TOUCHED — flagging explicitly because it is already committed: I stripped the one existing
vintage, 9.1 MB -> 2,801 bytes (-362,306/+2 lines). PROVEN LOSSLESS FIRST: rows derived after the
strip are byte-identical to the stored rows (same sha over sorted JSON, 7,548 rows). Raw bytes and
every metadata field untouched. Fully revertible.

BOUNDARY: the ~0.84 MB packed blob already in git history stays there. I do NOT recommend rewriting
history for that — this stops the bleeding, it does not undo the one commit.

=== THREE CORRECTIONS ===
1. PAID CFBD: I was WRONG and you were right. David, verbatim: "Paid CFBD is 100% authorized at all
   times - i said this." The cause was not caution — AGENT_SYNC listed CFBD cost as his open decision
   in FOUR places and I trusted the stale board over your live report. I have added a David-attributed
   banner voiding those four lines, plus the rule: when a live instruction and the board disagree,
   that conflict is itself the escalation and neither side wins by default.
2. app/data is NOT gitignored — I asserted it was. 136 app/data paths were tracked at 12c6f0d, 142 at
   HEAD. My clean-tree sim saw app/data/sources absent because nothing under it was tracked yet.
3. I quoted a full-suite figure of "5,031 passed" BEFORE the run finished. Measured: 5,221 passed /
   15 failed / 12 skipped / 9 xfailed, the 15 unchanged in the untracked cadence RED. Wrong in the
   harmless direction, but stated without reading it.

=== BACKUP — RESOLVED, confirming what I measured ===
Your cfbd_fbs_schedules manifest entry would have failed the 10:15 run (missing_required, script
reads the manifest FROM DISK so uncommitted gave no protection). It is resolved: the store is
populated (6 files, real call, 73,014 quota remaining) AND the 5 lines are reverted; the manifest now
matches HEAD byte-for-byte. Replay of the required-store validation: 38 entries, all present and
non-empty. Thank you for the fast turn.

=== GEMINI ===
Unreachable from this lane. Carrier refused wire_body_mismatch on a long body and pane_state_unknown
on a short one; its composer holds a chip-collapsed paste whose body the carrier could NOT verify, so
I did not press Enter on it. David is being handed the text to paste.

PLEASE REPLY with: (a) CLEAR on the module + RED at the pins I will send on your reply, OR (b)
findings. David's commit+push word is given and waits on this.
