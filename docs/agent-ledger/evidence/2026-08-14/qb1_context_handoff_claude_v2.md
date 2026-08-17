# TW14-QB1-1 — CONTEXT HANDOFF v2 (Claude write lane, 2026-08-14 ~20:2x ET)

**Why this exists:** David's word, verbatim: "you're out of context." Clean stop taken at
the cap-round wait — the next action is verdict-contingent and everything needed is on
disk. A fresh session reading THIS FILE plus the cited pins continues without any
conversation memory. Supersedes `qb1_context_handoff_claude_v1.md` (that resume completed:
its round-2 correction, and rounds 2→5, all happened today after it).

## David's words in force (verbatim, all standing)

1. **"run the study when codex clears the review"** — re-affirmed twice ("I pressed enter
   on codex - run the study when it clears" · "run the study when it clears"). Execution
   fires ON Codex's green-review CLEAR, no further word needed. The RULING on the
   registered result remains his separate word.
2. **"continue"** — his disposition of the three-failed-reviews BLOCKED terminal; he
   archived that run BY HIS OWN KEYSTROKE to
   `…/dg-autonomy/run.claude-qb1-BLOCKED-after-r3.json.bak`.
3. Standing: scorer `17cfc1e` push = his separate keystroke. No push of anything. H2 QB
   rushing **UNDER TEST** with no result until execution AND his ruling.

## Where the cycle stands (exact)

- **GREEN-review ROUND 5 OF 5 — THE CAP ROUND — is WITH CODEX**, request delivered and
  transcript-verified (`qb1_green_round5_review_request_claude_v1.md`, `090d5df4…`).
  **The verdict had NOT returned when this handoff was written — check first** (see
  resume sequence).
- **The fork:** CLEAR → execute immediately on David's standing word (below). BLOCKER →
  NO round 6 — the counters route to **the Judge** (pane 2.3; charter
  `~/.claude/agents/judge.md`); SHIP ships the ruled content, STOP parks for David; David
  outranks every ruling.
- **Cap state is mechanically real** (R4-G2 repaired per Codex's instruction via the
  committed `qb1_cap_state_repair_claude_v1.py`, `2c88697e…`): the continuation run
  (id `f8f7551c…`, goal cites David's "continue") holds framing/1 + green-review/1–4
  CLOSED and green-review/5 OPEN. Loop verbs: `node
  ~/dg-cockpit/autonomy/core/bin/dg-autonomy.mjs <verb>` (findings recorded BEFORE cycle
  messages; reviewer-clear + round-close on a CLEAR; the `verdict` verb computes
  ADJUDICATION_REQUIRED on a capped BLOCKER).
- **Review history:** 5 rounds, ~34 accepted findings (7 r1 · 7 r2 · 6 r3 · 3 r4 + the
  framing rounds), ZERO disputed. All four Codex probes fully flipped (r1 12/13 by
  design; r2 4/4; r3 5/5; r4 4/4). Codex disclosed (its lane) one Studio-wall read
  traversal in round 4 — recorded, results discarded.

## Round-5 boundary pins (all verified at write time)

- `execution.py` `12ed99057185ab3fa87ca9255b541d5f64735894d783043d3c8668a6baccb8ab`
- `scripts/run_qb1_study.py` `e457d647656f5b1059d751f0835a2dac7de749f3a5a213c72df14286ccf4cca7`
- `tests/contract/test_qb1_green_correction_contracts.py` `2e16956cfc3c6e8ca17b01996baddcf082c5100911e329e1124a8eb94e2d2022` (52/52)
- `status.py` `67651821…` · `__init__.py` `d8876020…` · amended execution RED
  `5d3bc660…` (the ONE Codex-sanctioned amendment; removing its 8 added lines
  reconstructs `4e6d7dc5…`) · program RED `7e95079…` · inference ratchet `25c4ffde…` ·
  reinforcement `db351f8c…`
- F25 frozen set: the five paths/hashes in `scripts/run_qb1_study.py::F25_FROZEN_SET`
  (Codex-measured, test-pinned) · crosswalk `app/data/identity/_runs/ff_playerids_20260516.json`
  `8ed4b675…f593` · D1 substrate 17 snapshots under the frozen raw root · frozen wire
  pair `b3247ec8…`/`fd924eb1…` untouched.

## Census (measured, final tree)

Frozen bundle 211/211 · reinforcement 344/344 · contracts 52/52 · full suite **6,054
passed / 15 failed / 12 skipped / 0 collection errors** — the 15 verified BY NAME as
exactly the standing UNTRACKED `test_governed_cadence_inputs_red.py` (never commit it) ·
Ruff + strict compile clean.

## Resume sequence (fresh session, after bootstrap)

1. **Check for Codex's round-5 verdict FIRST**: newest `qb1_execution_green_review_codex_v5*`
   in `docs/agent-ledger/evidence/2026-08-14/` (or the run state's round-5
   reviewerVerdict). Verify this handoff's pins before acting on anything.
2. **If CLEAR:** record reviewer-clear + round-close via the verbs; then EXECUTE on
   David's standing word: `.venv/bin/python3.14 scripts/run_qb1_study.py` (deterministic,
   seeds 20260716; every stage re-verifies pin `37065566…`; publishes atomically to
   `app/data/backtest/qb_validation/qb_validation_report.json`; every failure is a named
   metric-free artifact). Then assemble the REGISTERED readout for David — statuses in
   the registered vocabulary only, `decision_supported=False` recursively, H2's
   registered result presented FOR HIS RULING, never as an established finding. Expected
   honest possibilities include `unsupported_power`/`not_separable` anywhere; H5
   c11–c14 likely `unsupported_power` by the registered identity rule (advisory).
3. **If BLOCKER:** no round 6. Run the `verdict` verb; ADJUDICATION_REQUIRED routes to
   the Judge (pane 2.3). The Judge rules SHIP or STOP; disputes about the ruling go to
   David, never back to the Judge.
4. Gates unchanged throughout: no push · no provider calls (substrate complete on disk) ·
   registered values immutable · commit only via gate paths (a SHIP ruling authorizes
   exactly the ruled commit).

## Uncommitted session record

Everything after scorer commit `17cfc1e` (HEAD, 1 ahead of origin) remains on disk
UNCOMMITTED by design: all QB-1 product/test edits, the full evidence chain (requests,
verdicts, probes, wires, the cap repair script, both handoffs), today's ledger, the
substrate (gitignored). Do not discard the tree; the next gate commit carries the cycle.
