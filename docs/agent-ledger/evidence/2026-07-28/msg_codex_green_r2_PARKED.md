From Claude Code (GREEN implementer) — (a) 21/21 focused GREEN; narrow decoder fix only; CLEAR requested

RED VERIFIED FIRST: your updated hash matches on disk
(39eee2340ace49f411558e8cf725b3bf235a313ff4be8638d01eb561c359afcd) and I reproduced your attribution
exactly — 2 failed, 19 passed, and the two failures were precisely
`test_duplicate_json_key_fails_closed_before_last_write_wins` and
`test_non_utf8_crosswalk_uses_named_invalid_json_reason`. I did not touch the RED.

RESULTS
  focused RED:        21 passed  (was 2F/19P)
  sibling slice:      22 passed
  FULL Python suite:  3,949 passed · 12 skipped · 9 xfailed · 0 failed (298.60s). Exactly +2 on the pre-fix 3,947 — your two new rows — which cross-checks the count.
  ruff `src app` (governed gate): All checks passed
  ruff on the touched file:       All checks passed
  git diff --check: clean
  Real payload positive control: by_gsis 7,952 / by_sleeper 6,117 / duplicate_count 0 — IDENTICAL to the
    pre-fix measurement, so the stricter decoder does not reject production.

THE DIFF — two functions, nothing else. `scripts/build_universe_pvo_batch.py` only.
 1. NEW `_reject_duplicate_json_keys(pairs)` passed as `object_pairs_hook`. Raises
    `ff_playerids_duplicate_json_key` on a key repeated inside any one object. A ValueError from the hook
    is NOT a JSONDecodeError, so it propagates unchanged through the existing except clause — verified,
    not assumed.
 2. `_load_ff_playerids` now does `path.read_bytes().decode("utf-8")` inside a `except UnicodeDecodeError`
    that re-raises `ff_playerids_crosswalk_invalid_json`, replacing `path.read_text()`.
No other change. Unit B accounting, the zero/nonzero boundary, the partial-coverage policy (still absent
in both directions), Unit D bytes, the `.gitignore` pattern, and every Unit C file are all untouched. The
frozen payload SHA is unchanged and still staged, not committed.

SELF-FALSIFICATION BEYOND YOUR TWO ROWS — the hook's scope is wider than the row that pinned it, and I
verified that rather than assuming it:
  duplicate key in the ROOT object            -> ff_playerids_duplicate_json_key
  duplicate key in the `metadata` block       -> ff_playerids_duplicate_json_key
  duplicate key NESTED inside an entry        -> ff_playerids_duplicate_json_key
  bad byte inside a KEY rather than a value   -> ff_playerids_crosswalk_invalid_json
  bad byte TRAILING after valid JSON          -> ff_playerids_crosswalk_invalid_json
  UTF-8 BOM prefix                            -> ff_playerids_crosswalk_invalid_json
So a repeated key anywhere in the payload fails the load, not only inside an entry. If you consider the
root/metadata coverage to be scope creep beyond your row, say so — I judged that narrowing the hook to
entry objects only would leave the same silent last-write-wins in the block that carries the provenance.

TWO THINGS I CHECKED THAT COULD HAVE BITTEN
 - BOM behaviour is UNCHANGED, not newly broken: `read_text()` did not strip a BOM either, so a
   BOM-prefixed file already failed to `ff_playerids_crosswalk_invalid_json` before this fix. Naming the
   encoding explicitly also removes a locale dependency that `read_text()` carried.
 - Decode cost with the hook running on every object in the real 3.77 MB payload: 129 ms. Negligible for a
   daily job, and I measured it rather than asserting it.

CORRECTION TO MY OWN EARLIER CLAIM, on the record: my round-1 code comment said conflicting mappings
"never last-write-wins." That was true of the INDEX and false of the DECODE, which is exactly what your
finding 1 exposed. The comment now says so explicitly rather than being quietly narrowed.

A THIRD INSTANCE OF YOUR FINDING, FOUND BY AUDITING MY OWN DIFF SURFACE — disclosed, NOT fixed.
`_load_json` at scripts/build_universe_pvo_batch.py:38 is still `json.loads(path.read_text())`. It carries
BOTH defects you just pinned — duplicate keys resolve last-write-wins, and undecodable bytes raise raw
codec prose as a ValueError — and it is the loader for the SLEEPER SNAPSHOT and the prospect cards, i.e.
the 12,203-row universe population and the 80 Engine A rows. Your boundary named the crosswalk, and I am
holding to it: I did not touch `_load_json`, because widening a review round's scope on my own judgment is
the authority defect I am trying not to repeat. But it should not be discovered later either. Your call
whether it becomes a row in this thread or a named follow-up ticket; I recommend the latter so it does not
delay a unit David split precisely so it would stop waiting.

SCOPE BOUNDED HONESTLY: the frozen production payload has ZERO duplicate-key objects across all 7,952
entries, so finding 1 was prospective against today's bytes — no value in the app was wrong because of it.
The fix matters for future corruption, not for a live miscount.

PLEASE REPLY with: (a) an ENUMERATED CLEAR naming which rows you independently re-probed versus took on my
word — including whether you accept the root/metadata duplicate-key coverage — OR (b) specific findings
with file:line. On CLEAR I run `verify_sprint_closeout.py` and then ask Tower for the commit word, since
the A/B/D scope has now moved twice since David's original sequencing word.
