From Claude Code (independent builder review) — CFBD wrapper: CLEAR on all five criteria, with ONE named gap and no live refresh run

Reviewed: src/dynasty_genius/capture/cfbd_foundation_refresh.py (239), scripts/run_cfbd_foundation_refresh.py (88),
tests/contract/test_cfbd_foundation_refresh.py (158). 5/5 its tests pass. NO live refresh was run.

CRITERION 1 — wrapper around the ONE existing adapter: PASS, and I checked the mechanism rather than
the intent. `_builder` imports scripts.build_w2b_cfbd and calls its main(); no CFBD HTTP is
reimplemented. Isolation is achieved by monkeypatching two module globals (V3_CSV, CACHE_DIR) and
restoring in `finally`.
I verified the monkeypatch ACTUALLY isolates, because it only works if every path is computed from
those globals at CALL time. Traced every write site in build_w2b_cfbd.py:
  cache writes  — 139, 153, 167, 181, 218, 239 all build `CACHE_DIR / ...` at call time
  QB stats      — 1017 passes CACHE_DIR positionally at call time (not a default argument)
  curated CSV   — 877 read / 1057 write, both via V3_CSV
No module-level derived path and no default-argument capture. Isolation HOLDS today.

CRITERION 2 — cache/input immutability: PASS. Input is copied to a staging path; input_sha256 is
taken before the builder and re-checked after, refusing publish on mutation ("CFBD builder mutated
the source input"). Raw runs land at an immutable per-run path that refuses to overwrite. Publishes
are atomic (tmp + os.replace). An exclusive O_EXCL lock refuses concurrent runs. Staging is removed
in `finally`.

CRITERION 3 — degraded-row and <99% identity fail-closed: PASS, and fail-closed in the right
direction. `w2b_cfbd_degraded != "0"` counts missing/None as degraded, so an absent column fails
rather than passes. Coverage below MIN_IDENTITY_COVERAGE=0.99 refuses. Required columns and a
populated CFBD provenance source column are both enforced. Zero-row output refuses. Invalid raw JSON
refuses.

CRITERION 4 — no-op/status semantics: PASS, and it draws the distinction David has been burned by
all week. A no-op is decided on CONTENT (raw_content_sha256 + curated_sha256 vs the previous
manifest), not on the job having run. On no-op it writes status_latest.json with
last_changed_at = the PREVIOUS captured_at and does NOT advance manifest_latest.json or create a raw
run. That is "the job ran" and "the data moved" kept apart, correctly.

CRITERION 5 — no live refresh during review: HELD. I ran none. --preflight is genuinely read-only
(prints readiness, returns; no fetch, no write) and the action group is required=True, so there is
no accidental default execution.

THE ONE GAP — ISOLATION IS CORRECT BUT UNGUARDED. Criterion 1 passes on a property of a DIFFERENT
file: that build_w2b_cfbd.py never binds CACHE_DIR/V3_CSV at import or as a default argument. Nothing
enforces that. A future edit of the form `def f(..., cache_dir: Path = CACHE_DIR)` would silently
defeat the monkeypatch and write into app/data/cfbd_cache/ — the directory David is explicitly
protecting for the pre-registered run — with every existing test still green, because none of them
exercise the real builder.
Not a blocker for landing; the code is correct as it stands. But it is the one place where "isolated"
is an assumption rather than a locked contract.
PROPOSED GUARD, not written into your file without your word: a contract row asserting that no
callable in build_w2b_cfbd has CACHE_DIR or V3_CSV captured as a default-argument value, plus a row
asserting the wrapper restores both globals when the builder RAISES. Both are cheap and static, and
neither needs a live call. Say the word and I will add them — as a separate file of mine, or hand
you the rows for yours, your choice.

TWO SMALLER OBSERVATIONS, neither blocking:
1. `_builder` calls main(force_fetch=True), so every --execute run pays full live API cost and can
   never be a cheap content check. Intended for a refresh, but it means the no-op detection in
   Criterion 4 can only be reached AFTER a full paid fetch. Worth knowing before it is scheduled.
2. The monkeypatch is not concurrency-safe against another in-process import of the builder. The
   O_EXCL lock covers separate runs against the same source_root, which is the realistic case.

VERDICT: CLEAR to land the three CFBD files as-is, on David's word. The gap above is a follow-up, not
a condition — I am not holding your work for a guard I could add myself.

FOR DAVID, the reason this matters: CFBD is a PAID subscription he named on his 2026-07-25 list, and
it is the only one of his six that is connected. Its cache last moved 2026-05-24. This wrapper is
what takes it off a two-month-old snapshot without touching the protected directory.

PLEASE REPLY with: (a) CONFIRM and tell me where to put the two guard rows, OR (b) CHALLENGE with the
concrete technical reason.
