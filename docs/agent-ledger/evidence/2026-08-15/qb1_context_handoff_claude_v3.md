# TW14-QB1-1 — CONTEXT HANDOFF v3 (Claude write lane, 2026-08-15 ~07:4x ET)

**Why this exists:** David's word: "youre nearly out of context." Clean stop at the
natural seam — all round-8 analytical work is COMPLETE; only mechanical routing remains.
A fresh session reading THIS FILE plus the cited pins continues without conversation
memory. Supersedes `2026-08-14/qb1_context_handoff_claude_v2.md` (that resume completed:
rounds 5–7 all closed; the Judge STOP, the Option-1 reconciliation, and rounds 6–8 all
happened after it).

## David's words in force (verbatim, all standing)

1. **"run the study when codex clears the review"** — re-affirmed repeatedly. Execution
   fires ON Codex's explicit CLEAR of the current round, no further word needed. The
   RULING on the registered result remains his separate word.
2. **"one more bounded round - open round 8 per your sanctioned mechanism, claude
   implements your four R7 smallest corrections, execution only on your clear"** —
   embedded in the round-8 record by Codex's transition (revision 40→41).
3. **"run it through codex when the suite is green"** — the standing routing sequence.
4. **"wake codex when it's routed"** — after routing, verify the request SUBMITTED and
   Codex's pane is actively reviewing; if idle, pass the wake to Tower's session citing
   this word (Tower carried the prior "wake codex").
5. Standing: scorer `17cfc1e` push = his separate keystroke; no push of anything;
   publication of QB-1 results is his personal ruling; H2 QB rushing **UNDER TEST**
   with no result until execution AND his ruling.

## Where the cycle stands (exact)

- **Run `f8f7551c…`, ACTIVE, green-review ROUND 8 OPEN** (opened 11:08:20Z by Codex's
  `qb1_round8_open_codex_v1.mjs`, pin `18397142…`, revision 41). Round-8 scope: the
  three files below. Rounds 1–7 closed; Judge STOP (revision 23) is history; the
  non-applying verdict reads ADJUDICATION_REQUIRED/PHASE_ROUND_CAP by design (ratified
  counters preserved; David's direct exception is the round's authority).
- **All four R7 blockers are IMPLEMENTED** per Codex's smallest corrections: G1 the
  gate reconstructs the canonical payload (production's own `contrast_status` mapping)
  and INVOKES the shipped `evaluate_power_and_status`, requiring exact equality of
  status (+ H5 ni_met/flags), with the below-floor special case; G2 closed margin-leaf
  schemas (computed = three non-null outputs; unavailable = named state + three nulls;
  production converts present-but-null leaves to unavailable), per-contrast exclusion
  flags, and EXACT two-sided reconciliation (evaluable + structured excluded rows ==
  fold-metric presence; exclusion rows carry test_season + closed-vocabulary reasons);
  G3 boundary rows bound to the trailing window (shared ARCHETYPE_WINDOW_SEASONS),
  positive-int qualifying games, the `abs(yards−400) ≤ games` relation, and recomputed
  gate/flip booleans (out-of-boundary seasons contribute identically to all three
  shifted classifications — that's why flips are decidable from boundary rows alone);
  G4 case lanes conditioned on the case's fold (h5 only in registered H5 folds).
- **Two production-truth corrections were caught by the G4 end-to-end arbiter and
  fixed** (excluded_folds structured shape; present-but-null margin leaves) — recorded
  in the 07:xx ledger entries, not smoothed.

## Round-8 boundary pins (measured at handoff; Ruff import-sort safe-fix applied)

- `src/dynasty_genius/eval/qb_validation/execution.py` `913225f529a0c63a30b4ee6b025c3d1ac408a5d6107be15b8a65dc80d83e9f37`
- `scripts/run_qb1_study.py` `ef7a8244d5b141eaa7280f37b269531089f5eeeb6649b230b09fcbe50bde86eb`
- `tests/contract/test_qb1_green_correction_contracts.py` `513ed1bd255c9c62368bcb68f8cacfbfdc3284aa5c9df3a0c8a36affd46b9b58`
- UNCHANGED: `status.py` `67651821…` · `__init__.py` `d8876020…` · execution RED
  `5d3bc660…` · program RED `7e950792…` · ratchet `25c4ffde…` · reinforcement
  `db351f8c…` · frozen wire pair `b3247ec8…`/`fd924eb1…`.

## Census at handoff (all measured this tree)

Correction contracts **91/91** (79 + 12 R8 mutants incl. all nine Codex round-7 probe
rows + positive controls for honest exclusion/unavailable/flip paths) · frozen bundle +
reinforcement **555/555** · Codex round-7 probe **FAILS 9/9** · all carried probes
(r2–r6) **FAIL 23/23** · Ruff clean (one I001 import-sort safe-fixed post-pin — the
pins above are POST-fix) · **FULL SUITE MEASURED GREEN at these exact pins before the
session closed** (David's word "wait for the suite then record the tally"): **6,093
passed / 15 failed / 12 skipped in 12:17** + touched-file sanity 121/121 + strict
compile clean; the 15 verified BY NAME (the standing untracked
`test_governed_cadence_inputs_red.py` alone reproduces exactly 15; never commit it) —
**zero tracked failures**. Ledgered in the 07:4x addendum. The fresh session may cite
this measured tally and proceed DIRECTLY to the resume sequence's step 3 (routing);
re-running the suite is optional belt-and-braces, and Codex re-runs during review
regardless.

## Resume sequence (fresh session, after bootstrap)

1. Verify this file's pins on disk; verify run state (round 8 open, ACTIVE).
2. Run the full suite + strict compile (above). Green = zero tracked failures.
3. On green, per David's standing words: write the round-8 review request (mirror
   `2026-08-15/qb1_green_round7_review_request_claude_v1.md`'s shape: pins, the four
   fixes vs Codex's smallest corrections, census, the two production-truth corrections
   disclosed, CLEAR→execution fork), ledger it, send to Codex `dynasty:1.2` via
   `scripts/tmux_msg.py send --message-file`, POSITIVELY verify submission in its
   transcript (Wire Rule; one sanctioned submit-retry on a byte-verified own strand),
   and **wake Codex if idle** (word 4 above — via Tower's session if needed).
4. **On Codex's round-8 CLEAR:** record reviewer-clear + round-close via the verbs
   (`node ~/dg-cockpit/autonomy/core/bin/dg-autonomy.mjs`), then EXECUTE on David's
   standing word: `.venv/bin/python3.14 scripts/run_qb1_study.py` (deterministic,
   seeds 20260716, publishes atomically under the frozen root; every failure a named
   metric-free artifact). Then assemble the REGISTERED readout for David — registered
   vocabulary only, `decision_supported=False` recursively, H2's registered result
   presented FOR HIS RULING, never as an established finding.
5. **On a round-8 BLOCKER:** no further round exists on any standing word — the run
   re-parks for DAVID directly (the Judge's one ruling is spent; one gate, one ruling).
6. Gates throughout: no push · no provider calls (substrate complete on disk) ·
   registered values immutable · commits only via gate paths.

## Uncommitted session record

Everything after scorer commit `17cfc1e` (HEAD, 1 ahead) remains deliberately
uncommitted: all QB-1 product/test edits, the full evidence chain (rounds 5–8 requests,
verdicts, probes, wires, repair + transition scripts, three handoffs), ledgers, the
`.mcp.json` magic-entry removal (David's keystroke), and the archived run records
(`run.claude-qb1-STOP-r5.json.bak`, `run.claude-qb1-remediation-falsestart-970233e6.json.bak`).
Do not discard the tree; the next gate commit carries the cycle.
