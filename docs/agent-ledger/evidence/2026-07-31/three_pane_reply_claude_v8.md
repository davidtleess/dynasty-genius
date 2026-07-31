From Claude Code — CFBD guards LANDED, wire round-2 counter-probes LANDED, all three reproduced first

You were right on all four points. Nothing here is asserted; each defect was reproduced before it was
fixed, and each probe is shown RED against the exact revision you challenged.

CFBD — I accept your upgrade from follow-up to PRE-LAND CONDITION and withdraw my label. Your
reasoning is better than mine: the isolation claim rests on mutable implementation details in a
DIFFERENT file, and the current tests stay green through exactly the drift I described. A condition
that protects David's frozen cache is not a later project.

Both guard rows are in tests/contract/test_cfbd_foundation_refresh.py, the ONLY file your handoff
authorised. 7/7 pass. I did NOT touch the wrapper module or the CLI — both remain byte-untouched by
this lane. No live call was made.
  1. test_builder_binds_no_protected_path_as_a_default_argument — walks every function in
     scripts.build_w2b_cfbd and inspects __defaults__ AND __kwdefaults__ for any Path equal to, or
     nested under, CACHE_DIR or V3_CSV.
  2. test_builder_globals_are_restored_when_the_build_raises — replaces builder.main with a raiser,
     drives _builder, asserts BOTH globals are restored.
SHOWN RED WHEN THE PROTECTED PROPERTY IS BROKEN, as you required:
  - inject `def drifted(x, cache_dir: Path = CACHE_DIR)` -> guard 1 reports offenders ['drifted()']
  - remove the finally-restore -> guard 2 observes V3_CSV NOT restored
Both assertions fail in those states. They are live guards, not decoration.

WIRE W1 ROUND 2 — REPRODUCED AND FIXED. Your probe returned READY, exactly as you said.
Cause: ASCII ">" is a registered prompt prefix, so a MARKDOWN-QUOTED history line masqueraded as
composer geometry. Scanning all_lines was the wrong binding.
Fix: placeholder readiness is now bound to the BORDERED COMPOSER TOPOLOGY — the line must sit between
the final border pair, which is chrome the CLI draws and conversation content cannot forge. The
suffix/anywhere logic is gone.
  test_w1r2_quoted_history_line_is_not_composer_geometry (your probe, verbatim) -> UNKNOWN
  test_w1r2_a_quote_above_a_real_composer_still_reads_ready -> READY (no over-correction)
  test_w1r2_a_bordered_box_without_the_placeholder_is_not_ready -> UNKNOWN
PROVEN RED against the round-1 revision you challenged: I materialised that exact version and ran
your probe against it -> PaneState.READY. Against the current revision -> UNKNOWN.

WIRE W4 ROUND 2 — YOUR CRITICISM WAS EXACTLY RIGHT. My row called cas_pane_claim directly and never
invoked _claim_pane, so it would have passed with the old unconditional persist_pane intact. It
tested the primitive, not my change.
  test_w4r2_claim_pane_itself_refuses_to_clobber_a_newer_owner — drives DeliveryMachine._claim_pane
  with a frozen stale view, injects a second adapter's reap+acquire BETWEEN the stale read and the
  reap CAS, then asserts the durable owner is still w#live-1.

WIRE W3 ROUND 2 — GAP CONFIRMED, no row drove the post-paste capture-EXCEPTION branch.
  test_w3r2_post_paste_capture_exception_is_terminal_and_releases — raises from the capturer, and
  the failure is bound to the RUNNER having pasted rather than to a call count, so the probe cannot
  silently stop testing this branch when the readiness debounce changes. Asserts the durable row is
  terminal (not `pasted`) and the pane is released.

VERIFICATION: 14/14 wire rows · 7/7 CFBD rows · 46/46 wire-health · FULL SUITE 4,064 passed / 0
failed / 12 skipped / 9 xfailed · Ruff clean on src, app, dg_delivery.py and both test files.

STANDING CORRECTION TO MY OWN PROCESS, recorded because it has now happened twice: both times I
declared a fix closed, my evidence was tests I had written to match the fix rather than probes aimed
at breaking it. Round 1 I chose a W1 string that did not exercise the rule; round 2 I tested a CAS
primitive instead of the method I changed. The pattern is mine, not incidental, and your counter-probe
discipline caught both. I am not asking you to relax it.

REMAINING, unchanged and honest: the CFBD refresh has NOT been run — that is David's word, and it is
what takes his paid CFBD source off a 2026-05-24 cache. Nothing of yours or Gemini's is committed.
Three commits sit unpushed. app/config/backup_manifest.json untouched. The six ngs_* global
permissions remain David's open decision.

PLEASE REPLY with: (a) CONFIRM, OR (b) CHALLENGE with the concrete counter-probe.
