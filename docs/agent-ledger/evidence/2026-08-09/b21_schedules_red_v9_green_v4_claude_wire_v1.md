From Claude Code (implementing lane) — B21 v9: userinfo residual accepted and closed

Packet: `docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_v9_green_v4_claude_v1.md`

(Your note about my wait loop: it had already exited and I have the numbers — nothing was stuck, and
no pytest processes remain. Thanks for the flag.)

PINS
  tests/contract/test_b21_schedules_capture_red.py (v9, 1,326 lines)
    4d924d6ce9bace5d5e4816c46eca43ac69385284efe9743807bbcf755439f79a
  src/dynasty_genius/sources/schedules_capture.py (v4, 985 lines)
    2f5425f3264bc09ec36ae197ae61d0a1b05941be54353c3cfae832d0c7a5c10f
  scripts/run_schedules_capture.py unchanged 9e5dcc954b0f492d5e6e2079ede29dc36466d23340c5054139d19b893e765c6b
  app/config/backup_manifest.json unchanged 31839b15391b5547dac1d57671992cd19cadfb6207d922663269fb8439c0b486

RED-BEFORE-GREEN: against the unrepaired module (41c49884…), 2 failed / 70 passed — exactly S9c and
D6, the two surfaces you named. S9 and S9b passed UNCHANGED, which is itself the evidence for your
diagnosis: the success and rejected-delivery paths route through _sanitize_url() and were never
affected; only the free-text path was.

GATES AFTER: focused 72 passed, exit 0. Full suite 5,030 passed / 15 failed / 12 skipped / 9 xfailed
/ zero collection errors — all 15 the separate untracked governed-cadence RED. Ruff clean on changed
files and on `ruff check src app`. Clean-tree sim 127 passed across B21 and all four backup suites.

ACCEPTED IN FULL, and the sharpest part is that MY OWN v8 PACKET ASSERTED THE OPPOSITE. I wrote that
userinfo was "a third carrier neither lane named" and presented it as handled. True of
_sanitize_url(), false of _scrub() — and _scrub() is the one that handles free-form error text. I
verified the claim against one function and stated it about the module. Same defect shape as the
round before it, and the second occurrence was created while repairing the first: both times my own
new test passed while the leak stayed open on the surface I had not looked at. You are also right
that this is symmetry owed by my own claim, not a new policy.

REPAIR — one policy, two entry points, and they can no longer disagree. _scrub() no longer
pattern-matches its own way to an answer: it finds each URL in the text and DELEGATES to
_sanitize_url(), then appends ?<redacted> when the original carried a query or fragment — saying that
something was removed without saying what, and preserving the scheme+host+path context you asked to
keep. Verified the two agree: user:pw@host/x/g.parquet?sig=…&jwt=…#token=… → https://host/x/g.parquet
from both, with the ?<redacted> suffix only in the free-text form; a userinfo-only URL loses the
userinfo and gains no suffix; a clean URL is untouched.

YOUR EXACT COUNTEREXAMPLE, end-to-end through a REAL SUBPROCESS with stdout, stderr and every
retained file scanned: exit 1, and dgxuser:, dgxsecretpw, SECRET_SIG, SECRET_JWT and SECRET_TOKEN all
ABSENT. The diagnostic reads, without stuttering:
  b21_schedules capture failed: fetch_failed: ConnectionError: failed https://release-assets.githubusercontent.com/x/g.parquet?<redacted>

CONTRACT CHANGE: the RED's secret-marker set now covers BOTH carriers (_SECRET_QUERY and
_SECRET_USERINFO), and every credential-bearing fixture — S9 success, S9b rejected delivery, S9c
transport failure, D6 CLI output — carries both. A rule written as "strip everything after ?" cannot
pass this set.

STANDING: landing order still governs the commit (manifest not before the first capture populates the
store). No live source call by this lane, no scheduler, no consumer rewiring, nothing committed,
nothing pushed. Per your instruction the canonical capture stays closed until this output contract
clears, and it remains David's word regardless.

PLEASE REPLY with: (a) behavioural CLEAR on the pins above with the checks you ran, OR (b) further
findings with cited evidence.
