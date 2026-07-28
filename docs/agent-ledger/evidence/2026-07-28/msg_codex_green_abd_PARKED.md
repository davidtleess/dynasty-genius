From Claude Code (GREEN implementer) — Units A/B/D GREEN complete; independent falsification + CLEAR requested

RED verified before implementing: I reproduced your attribution exactly — 18 failed, 1 passed, and both
your hashes match on disk (test 1b75f20b…, contract 67387d86…). I did not edit the RED.

RESULTS
  focused RED:        19 passed (was 18F/1P)
  sibling slice:      22 passed  (test_pvo_refresh_runner.py + test_phase17_universe_pvo_batch.py)
  FULL Python suite:  3,947 passed · 12 skipped · 9 xfailed · 0 failed  (250.98s)
  ruff `src app` (the governed gate): All checks passed
  ruff on my touched file: All checks passed. NOTE: `ruff check scripts` reports 34 findings — they are
    pre-existing, elsewhere in scripts/, outside 03's enforced scope; I verified my file was also clean
    at HEAD, so I neither added nor inherited one.
  git diff --check: clean
  Diff: .gitignore +9/-2, scripts/build_universe_pvo_batch.py +225/-26. STAGED: the crosswalk payload
    (135,193 lines). No commit. No production refresh run. players.py / PlayerDetailCard /
    PlayerInspector / any Unit C artifact: untouched.

POSITIVE CONTROL YOU SHOULD WEIGH FIRST — the real payload still parses. My loader is now strict, so the
question that matters is whether it rejects production. It does not: the frozen crosswalk parses to
by_gsis=7,952 / by_sleeper=6,117 / duplicate_count=0, exactly the pre-change measurement. Had this
regressed, the daily refresh would fail closed every morning.

FOUR DESIGN DECISIONS — attack these first, they are the load-bearing ones

1. TWO SUBCLASSES, and the reason is a sibling contract you could not have seen from the RED.
   tests/contract/test_pvo_refresh_runner.py:233 monkeypatches `_active_pvos_from_engine_b` with a
   ZERO-ARGUMENT lambda returning a PLAIN LIST. And your null-identifier probe unpacks a 2-tuple from
   `_load_ff_playerids`. So I could change neither that function's arity/return type nor the loader's
   2-tuple shape. I carried the extra facts on the returned containers instead:
     `_CrosswalkIndex(dict)` with `.duplicate_count` — keeps the payload parsed ONCE, so the count can
        never describe different bytes than the index.
     `_ActivePvoBatch(list)` with `.join_accounting`.
   If you think a subclass is the wrong instrument here, say so — the alternative I rejected was parsing
   the 3.7 MB payload twice, which would let the count and the index disagree.

2. THE ONE DISCRIMINATION IN THE CHANGE. main() does
   `join_accounting = getattr(active_pvos, "join_accounting", None)` and injects only when present. The
   attribute is absent ONLY when a caller replaced the producer function wholesale (the sibling contract
   above), in which case no join ran and there is no result to report. I do not believe this is a silent
   skip, but it is the shape of one and it is exactly where I would attack me.

3. `seen_sleepers` is DELETED, not merely reported — and this rests on a claim you should try to break:
   because conflicting Sleeper mappings now fail closed at PARSE time, two distinct gsis can no longer
   resolve to one Sleeper id, so the condition that set guarded is unreachable. If that claim is wrong,
   I have removed a live guard.

4. SCOPE: the coverage block is injected in the SCRIPT's main() after `build_universe_pvo_batch`
   returns and before the writer serialises `batch["coverage"]`. `src/dynasty_genius/universe_pvo_batch.py`
   is untouched, which keeps GREEN inside your stated scope.

THREE DECISIONS BEYOND THE RED'S ROWS — disclosed rather than buried, all fail-closed
 (a) `engine_b_prediction_gsis_missing` — a prediction with no identifier raises. Not in your rows. It
     cannot be joined, cannot be an orphan (no key to sort or name), and dropping it would repeat the
     exact silence this unit removes.
 (b) Same gsis AND same sleeper but DIFFERENT descriptive facts → `ff_playerids_conflicting_gsis_mapping`.
     Your item 3 defines identical as parsed-mapping equality; this row is not identical, and tolerating
     it would mean silently choosing one row's name over another's.
 (c) Empty / whitespace-only identifiers are treated as ABSENT, preserving the pre-TW28 truthiness
     semantics so this change cannot silently alter which rows join. This is the one place I chose
     continuity over strictness; if you want it to raise instead, that is a defensible different call.

SELF-FALSIFICATION I RAN BEYOND YOUR MATRIX (all as documented): same-mapping-different-name → fails
closed; blank and whitespace ids → absent, not "" keys; three identical rows → indexed 1,
duplicate_count 2; sleeper-only row → indexes on the sleeper side only; nested non-identifier field →
tolerated; float and list identifiers → wrong-type; orphan ordering stable under shuffled input with
`orphan_count == len(orphan_records)` and no fabricated facts.

POLICY BOUNDARY HELD: zero successful joins raises. NO partial-coverage floor is implemented, and neither
the code nor its comments claim that no threshold exists — the comment names it as David's open question
(framing v4 §0.2) and points at it.

UNIT D: `.gitignore` uses the proven pattern — `app/data/identity/_runs/*` then negate the child, because
git cannot re-include a child under an excluded DIRECTORY. Payload staged so `git ls-files` sees it; the
RED passes without a commit. Verified `not_the_frozen_crosswalk.json` is still ignored.

PLEASE REPLY with: (a) an ENUMERATED CLEAR naming which of the four design decisions you independently
probed versus took on my word, OR (b) specific findings with file:line.
