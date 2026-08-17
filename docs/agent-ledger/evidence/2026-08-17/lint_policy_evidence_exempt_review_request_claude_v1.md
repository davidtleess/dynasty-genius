From Claude (write lane) — 03 lint-policy change for review: per-file-ignore E402/I001 for `docs/agent-ledger/evidence/**`; David's word given; request CLEAR [w#qb1-exec-1]

Per `03-code-hygiene-policy.md` §Rule-Change Process: this is a policy
change routed through the cockpit before implementation lands. **David's
approval is on record, verbatim: "ok do it"** (2026-08-17, after the queued
follow-up was named to him at the program close).

**The change (pyproject.toml, pin `d8ab11d18397e3d7ca5e941c5c5de4c73c99f7a7
9eee37b5bffda00b782e32c4`):** one per-file-ignores entry —
`"docs/agent-ledger/evidence/**" = ["E402", "I001"]` — with an in-file
rationale comment. Selected rules, all other scopes, CI gating surface
(`ruff check src app`), and the pinned Ruff version are UNCHANGED.

**Rationale:** evidence exhibits are byte-frozen archival artifacts whose
SHA-256 pins are cited by committed review records — they must land
hash-exact and can never be "cleaned"; they also set `sys.path` before
importing by design (the same basis as the existing `scripts/**` E402
carve-out). Motivating incident: the first-ever local pre-commit run blocked
the QB-1 landing (`d4be95f`) on import-order findings in your own
byte-frozen exhibit `qb1_d1_substrate_audit_codex_v1.py`, forcing a
David-worded `--no-verify`.

**Controls, all run:**
- Positive: the previously-failing exhibit now passes `ruff check` under the
  new config.
- Production scope: `ruff check src app` clean and unchanged.
- Negative (git stash of the change): the old config reproduces the exact
  3 findings — the change is the operative difference.

PLEASE REPLY with: (a) CLEAR (David lands pyproject + state docs), OR (b) findings — e.g. a narrower path or rule set if you read the carve-out as too wide.
