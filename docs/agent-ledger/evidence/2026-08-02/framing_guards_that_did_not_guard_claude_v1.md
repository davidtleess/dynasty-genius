# Framing — guards that didn't guard

**Lane:** Claude Code · **Status:** v1, opened on David's word 2026-08-02, awaiting Codex challenge
**Layer served: `governance`** — this governs how we verify, not what we build.

**Layers 1-2 dependency check.** Not applicable as a dependency: this thread is about the
*verification discipline* applied at every layer, and its evidence is drawn from layer-1 work
completed the same session. Stated explicitly so its absence is not read as an omission (`05` §3).

---

## 1. The concrete situation

On 2026-08-01/02 the cockpit ran a full layer-1 cycle: a defect found, repaired, adversarially
reviewed, cleared, committed, pushed, CI-green, then run against live data.

**Codex raised 44 findings on my work across that session. I rejected none.**

That number alone is not the finding — an independent reviewer earning its cost is the system
working. The finding is the **shape** of what it caught. Nearly every one was not bad logic but a
**guard that passed while guarding nothing**:

| Guard | What it appeared to prove | What it actually proved |
| :-- | :-- | :-- |
| `test_stored_rows_equal_source_rows` | rows survive storage | two in-memory list lengths matched; **nothing was stored** |
| `SCHEMA_VERSION` bumped v2 → v3 | artifacts are distinguishable | nothing asserted it; reverting to v2 left every test green |
| `--summary` "read-only, full stop" | the command cannot write | a docstring said so; the code ran `CREATE TABLE` |
| G1 identity test | every feature family is bound | `sack_rate` was never asserted; the team route could empty silently |
| mock routers after an endpoint fix | the adapter is exercised | routers matched the OLD path; `sack_rate` became `None` in every test, all green |
| `integer_columns` declaration | `week`/`season` export as numbers | declared at cast time, not at **construction** time |
| `stored_columns` | every declared column persists | era-specific columns had nowhere to land and were dropped by `row.get()` |
| content hash | idempotence is provable | hashes the **rows**, not the **schema**; a widened column stayed NULL |

Every row of that table passed a green suite. Several passed an *adversarial review* too.

**The moment this serves:** David asks "is X verified?" and the answer means something.

## 2. Why this is a distinct failure class

These are not bugs in features. They are bugs in **evidence**. That makes them uniquely expensive:

- A feature bug announces itself. A guard bug is **silent by construction** — its whole job is to
  stay quiet.
- A guard bug **licenses everything downstream of it.** A green suite is why a commit is authorised,
  why a CLEAR is issued, why a David-facing claim gets made.
- They **accumulate**. Nothing prunes a test that stopped testing.

The session produced a compact example of the compounding: the CFBD QB adapter had been calling a
**Swagger docs page** instead of an API route since Stage 2, and `sacksAllowed` was never a CFBD
field. Both were invisible for months because a `try/except` turned every failure into `[]` — a
guard that converted evidence of breakage into evidence of absence. The tests that "covered" that
adapter passed the entire time.

## 3. Candidate falsification seeds

A proposal here is worth nothing unless it can itself be falsified, so seeds first:

1. **Positive control.** A guard is only proven when it has been observed to FAIL. Break the thing,
   watch the test go red, restore. Used four times this session (`sack_rate` route, `full_name`
   fallback, v3 revert, endpoint revert) and it worked every time.
2. **In-memory assertions cannot close a persistence claim.** A test whose name says "stored" must
   read back from the store.
3. **A declaration must be asserted somewhere or it is decoration** (the v3 case).
4. **A promise in prose is not a guarantee.** "Read-only" enforced by `mode=ro` is a guarantee;
   enforced by a docstring is a hope.
5. **Registry growth must re-examine every consumer.** `_bind` silently dropped new fields twice;
   `build_streams()` turned a read-only command into a writer. Same shape, three occurrences.
6. **A mock repointed after a production change must be re-verified**, or the test now exercises a
   path production no longer takes.
7. **Idempotence proofs must cover the shape, not only the content.**

## 4. Overclaim check

This thread proposes **no product change, no model change, and no David-facing surface.** It cannot
move `decision_supported`, promote a feature, or alter a football claim. Its only output is
verification discipline. It must not become a ceremony that slows delivery without catching
anything — seed 1 is the test of whether it earns its keep.

## 5. What I am NOT proposing

- Not a new governance document. `02` already carries falsification discipline; if anything lands it
  should sharpen what exists rather than add a fifth thing to read.
- Not a blanket rule that every test needs a positive control — that would be ceremony. The
  candidate scope is guards over **persistence, immutability, declared-vs-actual, and shared
  registries**, which is where all eight rows above sit.
- Not a claim that review caught everything. Four defects this session were found by **running the
  code**, not by any review — which is itself evidence that offline review has a ceiling.

## 6. Open questions for the challenge round

1. Is "positive control" the right primitive, or is it a special case of something better?
2. Should this attach to `02` §Falsification (which already exists and is already binding), or stay
   a checklist the lanes apply without amending governance?
3. Is the registry-growth failure a special case, or the general one with the others as instances?
4. What is the honest cost? Four positive controls this session took minutes — but a rule that
   demands one everywhere would be the box-tick `05` §3 warns about.

**Nothing is implemented. No RED opens on this framing until Codex challenges it and I answer.**
