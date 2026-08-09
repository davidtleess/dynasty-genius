From Claude Code (implementing lane) — B21 GREEN ready for behavioural review

Packet: `docs/agent-ledger/evidence/2026-08-09/b21_schedules_green_claude_v1.md`

Built against your CLEARed pin. THE RED WAS NOT TOUCHED — it still recomputes to
`38fceec11f9a4d623b53dee986fb59efe96fbf12429e18a2950190c9eca9cb86`, byte-identical, including the
stale "gameday unmeasured" sentence you told me not to edit.

CHANGED FILES
  src/dynasty_genius/sources/schedules_capture.py (new, 798 lines)
    6da5666413ee08774aaafd049ba3129516d5fa1e40a2651d86e5e306c1da49ce
  scripts/run_schedules_capture.py (new, 94 lines)
    b1a051467ced866ef53ffb1f281f44957f296e876abcbaf01e77d888bfc42a04
  app/config/backup_manifest.json (one required entry added)
    31839b15391b5547dac1d57671992cd19cadfb6207d922663269fb8439c0b486

GATES
  Focused: 56 passed / 0 failed, true exit 0.
  Full suite: 5,014 passed / 15 failed / 12 skipped / 9 xfailed / ZERO collection errors (681s).
    All 15 failures are in tests/contract/test_governed_cadence_inputs_red.py — the other UNTRACKED
    withdrawn RED against a module that does not exist. Tracked-file failures: zero.
    Measured correction: the 08-08 handoff board's arithmetic implies 12 in that file. It collects
    15, and its mtime (08-08 16:20) predates that board and this session. The board figure was wrong.
  Ruff: clean on both new files; `ruff check src app` (the CI gate under 03) clean.
  Clean-tree sim: `git archive HEAD` + the four files overlaid, with app/data absent entirely →
    61 passed (b21 + backup anti-rot). NEGATIVE CONTROL: removing the new manifest entry inside the
    sim makes P2 fail there, so the sim is a real check rather than a vacuous green.

⚠ LANDING-ORDER HAZARD — the most important line in this message.
The manifest entry BREAKS THE DAILY BACKUP until the store exists and holds at least one file.
backup_irreplaceable_data.py:226-228 raises missing_required:<path> for an absent required path and
:256-257 raises directory_empty_required:<path> for an empty required directory. The store does not
exist on this machine yet and the LaunchAgent fires daily at 10:15. So backup_manifest.json must NOT
be committed before the first capture populates the store — the change set lands WITH the capture, or
the disaster floor fails on its next run. Nothing mechanical enforces this; a well-meant "commit the
code now, capture later" would break it.

THE DEFECT YOUR RED CAUGHT IN MY GREEN. E1[marker] failed on the first run and it was a real bug: my
rollback deleted files the attempt CREATED but never restored files it OVERWROTE, so a marker-boundary
failure left the rewritten index naming a vintage the publication had abandoned (vintage_count 2, not
1). Three of four boundaries passed while it was broken. Repaired with a journal that records prior
bytes for every touched path and restores by atomic replace — never in place, because raw links share
an inode with the content store and an in-place write would reach through the link and corrupt a
retained vintage.

DECISIONS TO CHALLENGE
  1. Content-addressed raw with hard links: raw/<check_id>.parquet links to content/<sha256>.parquet,
     so every check keeps its own addressable path (S3) while identical bytes are stored once.
     Measured on a two-check no-change sequence: 3 files, ONE payload on disk (du: 4 KB).
  2. Validation order is load-bearing: dtype/null → source times → scores → duplicates → identifier
     consistency.
  3. retrieved_at defaults to observed_at on direct record_offering (the import/replay path); every
     transport path takes it from the response and validates it.
  4. The failed-attempt audit is written OUTSIDE the publication transaction on purpose, so evidence
     that we tried survives the rollback of what we tried to write.

SELF-PROBE beyond the contracts, off-network: two-check no-change sequence (inode identity,
last_checked advanced, last_changed frozen, no partial artifacts); CLI happy path; CLI transport
failure over a POPULATED store (exit 1, prior marker byte-identical); and --summary, read-only.

NOT DONE, each a separate word: no live source call, no scheduler, no plist, no consumer rewiring
(run_realized_outcome_scoring.py still infers "final" from a populated score — that migration is the
separately sequenced ticket), nothing committed, nothing pushed.

PLEASE REPLY with: (a) behavioural CLEAR on the three changed artifacts with the checks you ran, OR
(b) specific findings with cited evidence. The first live capture remains David's word — unchanged,
escalated, and not claimed by this packet — and the commit must follow the capture for the manifest
reason above.
