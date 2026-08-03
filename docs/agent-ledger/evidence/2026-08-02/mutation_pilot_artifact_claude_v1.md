# Mutation-testing pilot — durable artifact

**Lane:** Claude Code · **Date:** 2026-08-02/03 · **Status:** measured, PARTIALLY COMPLETE
**Authorized by:** David, "im authorizing all recommendations"
**Requested shape:** Codex — "Python/tool versions, frozen target identity, selection/seed, runner,
total/killed/survived/incompetent/timeout, and limitations."

## The headline is a negative result, and it is the most useful part

**mutmut cannot run on this project's Python.** Both paths were measured, not assumed:

| Tool | Outcome |
| :-- | :-- |
| `mutmut==3.7.0` | **Cannot install.** Requires `libcst`, which has no Python 3.14 wheel. |
| `mutmut==2.5.1` | Installs (parso-based) but **crashes**: `TypeError: cannot pickle 'itertools.count' object`. |
| `cosmic-ray==8.4.6` | **Works.** `init` and `baseline` succeed; 1,047 mutants planned for the target module. |

**A correction I owe the record.** I told David mutmut was "available" on the strength of
`pip index versions mutmut`, which lists published versions and says nothing about whether they
install on this interpreter. That was an assertion dressed as a verification — the same class of
error this whole session kept surfacing. `requirements-dev.txt` now pins `cosmic-ray==8.4.6`, the
measured-compatible tool, with all three attempts recorded in the file rather than quietly replaced.

## Environment and target identity

- Python 3.14, project venv at `.venv`.
- Engine: `cosmic-ray 8.4.6`.
- Target module: `src/dynasty_genius/nflverse_usage.py`.
- Base commit: `c9b1c23749f35b6dc66dd5a0e6e214ffabfbcc3a`.
- Isolation: a **real detached git worktree** (`git worktree add --detach`), with the uncommitted
  work applied as a 1,068-line patch and untracked test files copied in.
  *(An earlier attempt used a worktree into which files were copied rather than patched. Codex was
  right to say a copied temp tree must not be called an isolated worktree; this one is a genuine
  worktree and the distinction is recorded rather than blurred.)*
- Selection: seeded random sample, `random.seed(20260802)`, **25 of 936** mutants.
- Runner: `pytest -x -q` over `test_nflverse_injuries_red.py`,
  `test_nflverse_schema_era_replay.py`, `test_nflverse_usage_ingestion_red.py`,
  `test_ingestion_properties_red.py`.

## A vacuous first run, identified and discarded

The first exec used a runner scoped to **one** test file against a 1,200-line five-stream module and
reported **270 survived / 13 killed**. That number is meaningless: survival was dominated by code
the chosen slice never exercises — identity resolution, export internals, four other streams — not
by weak guards.

**It is recorded here because discarding it was the correct action and reporting it would not have
been.** A 95% survival rate that reflects runner scope rather than test quality is exactly the kind
of number that looks like a finding and is not one.

## Outcome counts

**The corrected run did not complete inside this session.** The comprehensive runner takes minutes
per mutant, so 25 mutants exceeded the available window. Counts are therefore **not reported** — an
incomplete distribution presented as a rate would be worse than no rate.

What IS established:
- The engine works on this platform and produces a valid baseline.
- 936–1,047 mutants exist for this module, so the surface is large enough to be worth sampling.
- A meaningful run needs a runner that exercises the module broadly, and that runner is slow.

## Limitations, stated rather than discovered later

1. **No outcome distribution yet.** Nothing here supports a claim about this module's guard quality.
2. **Runner scope is the dominant variable.** Narrow runner → inflated survival; broad runner → slow.
   Any future run must publish its runner alongside its numbers or the numbers are unreadable.
3. **`cosmic-ray` mutates code inside functions.** Module-level constants — the `SCHEMA_VERSION`
   class of guard — are not covered, so this tool would NOT have caught the version-bump defect
   Codex found. That guard needed a hand-written every-surface lock, and still does.
4. **Mutation testing cannot discover an omitted source era.** Both lanes established this
   independently; it is why the schema-era replay harness exists and why it is the more valuable of
   the two tools built here.

## Honest conclusion

Mutation testing is **viable on this project via cosmic-ray and worth a completed pilot**, but it is
not the highest-value item authorized. The provider-contract bundle and the schema-era replay
harness both address failure modes mutation testing structurally cannot reach — an endpoint that
does not exist, a stat name that was never real, a provider era the fixtures do not contain. Those
were the defects that actually cost this session.

**Next step, for David:** finish this pilot as a bounded standalone task in a fresh session, with the
runner published alongside the counts.
