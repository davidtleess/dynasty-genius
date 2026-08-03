# Mutation-testing pilot — COMPLETE

**Lane:** Claude Code · **Date:** 2026-08-03 · **Status:** **COMPLETE — terminal census, two rounds**
**Authorized by:** David, *"i want this work completed - in full - production grade - commited and
pushed; this session not next."*
**Supersedes:** `evidence/2026-08-02/mutation_pilot_artifact_claude_v1.md` (status
`PARTIALLY COMPLETE`, no counts, deferred to a future session). That deferral is withdrawn.

## Result

| round | mutants | KILLED | SURVIVED | INCOMPETENT | TIMEOUT | empty diffs |
| :-- | --: | --: | --: | --: | --: | --: |
| 1 — as the guards stood | 12 | **10** | **2** | 0 | 0 | 0 |
| 2 — after writing tests for both survivors | 12 | **12** | **0** | 0 | 0 | 0 |

Both survivors were **real coverage holes in load-bearing code**. That is the whole return on this
pilot, and it is why an N of 12 was still worth running.

## Environment and target identity

- Python 3.14, project venv. Engine: **cosmic-ray 8.4.6** (pinned in `requirements-dev.txt`).
- Target module: `src/dynasty_genius/nflverse_usage.py`.
- Base commit: `a7794e9`, with the session's uncommitted work applied as a patch in a **real
  detached git worktree** (`git worktree add --detach`).
- Import resolution verified to the worktree copy, not the main checkout, before any run.

## Selection — a complete census, not a sample

Rather than sample a large module, the pilot takes **every mutant cosmic-ray generates for three
named era-critical functions**:

| function | why it is load-bearing | mutants |
| :-- | :-- | --: |
| `StreamEra.matches` | era resolution — the guard the 2025 `date_modified`/`season_type` swap defeated | 7 |
| `UsageStore.stored_columns` | the era-column union that was silently dropping columns | 4 |
| `_projection_fingerprint` | folds into capture identity | 1 |

**12 of 1,047.** Complete over those three functions; it says nothing about the other 1,035, and no
statistical quality claim is made or implied at this N.

## Runner (published, because survival rates are unreadable without it)

```
pytest -q -x -p no:randomly \
  tests/contract/test_nflverse_injuries_red.py \
  tests/contract/test_nflverse_usage_ingestion_red.py \
  tests/contract/test_nflverse_schema_era_replay.py \
  tests/contract/test_ingestion_properties_red.py
```

Baseline green in the worktree before exec: **116 passed in 24.21s**.

## Round 1 — full per-mutant census

```
outcome    diff  function                  operator                                  line:col
SURVIVED    356  _projection_fingerprint   core/ReplaceTrueWithFalse                 764:38
KILLED      404  matches                   core/ReplaceComparisonOperator_Eq_Gt      195:25
KILLED      405  matches                   core/ReplaceComparisonOperator_Eq_GtE     195:25
KILLED      405  matches                   core/ReplaceComparisonOperator_Eq_Is      195:25
KILLED      409  matches                   core/ReplaceComparisonOperator_Eq_IsNot   195:25
KILLED      404  matches                   core/ReplaceComparisonOperator_Eq_Lt      195:25
SURVIVED    405  matches                   core/ReplaceComparisonOperator_Eq_LtE     195:25
KILLED      405  matches                   core/ReplaceComparisonOperator_Eq_NotEq   195:25
KILLED      436  stored_columns            core/ZeroIterationForLoop                 249:19
KILLED      457  stored_columns            core/ZeroIterationForLoop                 250:26
KILLED      521  stored_columns            core/AddNot                               251:19
KILLED      495  stored_columns            core/AddNot                               254:40
```

### Survivor 1 — `matches`: `==` → `<=` — an exact-resolver / error-taxonomy gap

`available == set(self.columns)` became `available <= set(self.columns)`. For sets that is
**subset**, so the mutant still refuses an **additive** column — which is all the B1 positive
control ever exercised. Nothing pinned the other half of the declared contract: that a **missing**
column also refuses. The class docstring promises *"EXACT column-set equality"* and only half of
that promise was tested.

**Scope correction — Codex's, and it materially narrows my first claim.** I initially wrote that a
truncated fetch "would silently match the era and be normalized against a shape it does not have."
**That was wrong.** Codex traced the actual mutant path and required the correction before CLEAR.
I then measured it exhaustively rather than accept either account: driving **all 16** single-column
truncations of the revisioned era through `normalize_rows` with `matches` replaced by subset
matching gives **zero acceptances** —

| outcome under the `<=` mutant | count |
| :-- | --: |
| `nflverse_heterogeneous_batch` | 15 |
| `nflverse_ambiguous_era` (dropping `date_modified` — the only deletion leaving a subset of *both* eras) | 1 |
| **accepted / normalized / stored** | **0** |

The pipeline was **already fail-closed** for truncation. What the mutant changes is *which* guard
refuses and under *which name*: the resolver calls a subset a known era instead of issuing
`nflverse_unknown_era`. That is an **error-taxonomy and observability** defect, not data loss.

*(Codex's own mechanism moved across its two messages — first `nflverse_schema_drift` via the
`missing` gate, then `nflverse_heterogeneous_batch` via the all-record exact-shape loop. The
exhaustive run above shows `heterogeneous_batch` for 15 of 16 and `ambiguous_era` for the
remaining one. Its **governing conclusion — no silent data loss — is correct**, which is the part
that changes what may be claimed.)*

**Kept and closed by** `test_an_era_refuses_a_TRUNCATED_column_set_not_only_an_additive_one`, which
asserts refusal for every single-column deletion. Codex agrees the test earns its place: a
documented exactness contract deserves a direct lock at the resolver rather than resting on
downstream guards that happen to catch the consequence.

### Survivor 2 — `_projection_fingerprint`: `sort_keys=True` → `False`

The fingerprint folds into capture identity. Without sorted keys the digest depends on the order
the payload dict literal happens to be written in, so a later edit that merely **reordered those
lines** would silently change the identity of every capture, with nothing failing.

**Closed by** `test_the_projection_fingerprint_is_pinned_to_a_golden_digest`, pinning the injuries
projection to `cb0d7df32ec14d115161577561f48a33795a5ba2ec15b9a6e71173ae8458285a` — making key
order load-bearing instead of incidental.

## The vacuous first run, and the correction I owe the record

The first exec of this session reported **12/12 SURVIVED**. I flagged it as suspicious — 12/12
survival is the signature of a harness that is not mutating — and hand-applied the line-195
`==`→`!=` mutation, which the suite **killed** (1 failed). Since `init` enumerated correctly and
`apply_mutation` produced exactly the intended change, I concluded that **`cosmic-ray exec` was
broken on Python 3.14** and told David the tool's output could not be trusted.

**That conclusion was wrong, and Codex proved it.** The defect was mine. My selection step deleted
1,035 rows from `mutation_specs` but left all 1,047 parent rows in `work_items`; `WorkDB`
reconstructs those orphans as `WorkItem(mutations=())`, so `exec` ran **mutation-free baselines**
and recorded each green run as SURVIVED with an empty diff.

Two lessons, both already-familiar shapes:

1. **`diff == ""` on every result was the tell, and I read past it.** A mutation result with no
   diff is not a survivor; it is evidence that nothing was mutated. I had that field in hand.
2. **I blamed the tool before auditing my own manipulation of its state.** The same error as
   "`pip index versions` proves installability" and "`init` + `baseline` succeed means the tool
   works" — verifying a component and generalizing to the whole.

**Repair (Codex's, executed verbatim):** discard all results, delete parent `work_items` with no
surviving `mutation_spec`, then positively assert `work_items == 12`, `mutation_specs == 12`,
orphans `== 0`, results `== 0` before exec; restore the source byte-for-byte; run once.

**Post-run acceptance, now enforced on both rounds:** exactly 12 results, **every** result
`length(diff) > 0`, outcomes summing to 12. Round 1 and round 2 both satisfy it. The internal
consistency check: round 1 reports the `Eq_NotEq` mutant **KILLED**, matching the hand-verification
exactly — the agreement that was absent from the vacuous run.

## Limitations, stated rather than discovered later

1. **Scope.** 12 of 1,047 mutants, complete over three named functions only. Nothing here supports
   a claim about the module's overall guard quality.
2. **Runner scope is the dominant variable.** Narrow runner → inflated survival. This runner is
   published above; any future run must publish its own or its numbers are unreadable.
3. **cosmic-ray mutates code inside functions.** Module-level constants — the `SCHEMA_VERSION`
   class of guard — are not covered, so this tool would **not** have caught the version-bump defect
   Codex found. That guard needed a hand-written every-surface lock, and still does.
4. **Mutation testing cannot discover an omitted source era.** Both lanes established this
   independently; it is why the schema-era replay harness exists and remains the more valuable of
   the two tools built here.
5. **A session-DB filter is part of the harness.** Round 1's false result came from filtering, not
   from mutating. Any future bounded run must assert the orphan-parent invariant before exec.
