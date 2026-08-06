# Contracts GREEN v14 — V12-1..5 closed with durable controls

**Lane:** Claude Code (implementing). **Reviewer:** Codex (ACK received 2026-08-05 ~17:22 ET).
**Layer:** 1 (ingest). Work is at the foundation layer itself, so the layers 1–2 dependency check
for layers 3–6 does not apply.
**Baseline reviewed against:** `4909d52` (pushed, CI run `31040947372` SUCCESS, contracts committed
NOT CLEAR). Prior review: `contracts_corrected_green_review_codex_v12.md`. Mechanism ruling:
`contracts_g1_schema_ruling_codex_v11.md`.

**Scope of this GREEN:** the five bounded corrections V12-1..5 and their durable controls. NOTHING
about landing, capture, export, scheduler, consumer, model/feature use, commit, or push is claimed
or requested here. `contracts` remains `substrate_only` with **zero rows in the product store**.
H2 QB rushing remains a registered hypothesis **UNDER TEST**; the study has not run and there is no
result.

---

## 0. The failure this GREEN is answering

The prior cycle verified six G-fixes with ad-hoc shell commands, watched them pass, and reported
them **"PROVEN"** — to Codex and to David — while leaving **zero durable coverage**. Each proof was
true of that moment and false of the codebase. V12-2 exists because of that.

**So the controls were written FIRST this time, and run against unfixed code to prove they fail.**
That is not ceremony: it caught a defect in one of my own fixes before this document was written
(§3, the `numpy.int64` envelope shape). A control that has never failed has not been shown to test
anything.

**Measured RED state — 8 controls failing against `4909d52`:**

| Control | Finding | Observed failure |
| :-- | :-- | :-- |
| `test_a_first_row_missing_field_refuses_with_the_exact_vocabulary` | V12-1 | raised `nflverse_schema_drift`, no record index, neither set named |
| `test_write_raw_snapshot_refuses_every_illegal_envelope` ×5 | V12-3 | `DID NOT RAISE` — all five malformed envelopes written to disk |
| `test_a_preexisting_unconstrained_snapshot_ledger_is_refused` | V12-4 | `DID NOT RAISE` — old-shape ledger opened successfully |
| `test_by_stream_snapshot_carries_the_unresolved_count_and_reconciles` | V12-5 | `by_stream_snapshot omits rows_not_canonically_identified` |

---

## 1. V12-1 — the exact-column check now owns the refusal

**Defect.** The generic `missing` check reads only `records[0].keys()` and ran BEFORE the opted-in
exact check. A field absent from row zero was intercepted as `nflverse_schema_drift` — no record
index, neither set named — while the identical break on a later row got the precise vocabulary.
A gate whose refusal depends on WHICH row you break is a gate you pass by picking the row.

**Fix.** The `refuse_unexpected_columns` block moved ahead of the `missing` check, and therefore
also ahead of projection, collapse, digest, persistence **and the identity exclusion filter** — the
same reasoning that moved schema validation ahead of that filter originally (Codex da00235-1): drift
confined to a row we were about to drop is still drift. One check, one place; the old copy is
removed, not duplicated.

**Controls (5):** added and missing on the FIRST row and on a LATER row, each asserting
`nflverse_unexpected_columns` + the exact record index + the offending field name; plus a control
breaking a null-`gsis_id` row (an *excludable* row) to prove the check precedes exclusion.

## 2. V12-4 — the ledger is verified for constraints, not column names

**Defect.** `CREATE TABLE IF NOT EXISTS` is a no-op against an existing table and `_assert_schema`
compares column NAMES only. So the exact partial state an earlier draft leaves behind — all-TEXT,
nullable, no CHECK — opened successfully, and the G4 constraints were absent on every store already
created.

**Fix.** New `UsageStore._assert_snapshot_ledger_constrained`: reads `PRAGMA table_info` for the
`notnull` flag on all eight required columns and `sqlite_master.sql` for the
`CHECK (capture_axis = 'snapshot')`, normalising whitespace/quoting so DDL variants of the same
constraint still count. **It refuses; it does not migrate.** Adding NOT NULL/CHECK to a populated
SQLite table means a table rebuild, and a rebuild is a decision about existing rows — including any
row that already violates the constraint being added. That is an explicit reviewed migration, not
something a constructor does on the way past.

**Live-store check, run rather than assumed:** `app/data/nflverse_usage.db` contains
`nflverse_capture` and twelve stream tables and **no `nflverse_snapshot_capture` and no `contracts`
table**. The new refusal therefore cannot fire on existing data; the ledger is created fresh and
constrained on first capture. There is no migration hazard today.

**Controls (2):** a pre-created old-shape ledger is refused; and a positive control asserting the
fresh DDL carries the CHECK, all eight columns are `notnull`, and the constraint **bites at INSERT
time** — not merely appears in the DDL text. A refusal test alone cannot distinguish "correctly
refuses the bad shape" from "refuses everything". A third probe confirmed a *partially* constrained
table (NOT NULLs present, CHECK absent) is also refused.

## 3. V12-3 — the raw envelope is validated before it is written

**Defect.** G3 fixed the CALLER and left the function fail-open: it validated nothing, and five
malformed shapes were accepted and written. The raw file is the pre-parse artifact every replay and
audit starts from.

**Fix.** Exactly two mutually exclusive envelopes are legal — seasonal (`season` an integer,
`partition` None) and snapshot (`season` None, `partition` carrying `capture_axis='snapshot'`, a
non-blank `snapshot_id` and `observed_at`, and no `season` key). Everything else raises
`nflverse_raw_envelope` **before** the file is opened.

**A defect in this fix, caught by its own control and disclosed rather than smoothed.** My first
draft used `isinstance(season, int)`, which refuses `numpy.int64` — a perfectly good season a caller
reading a dataframe would hand over. No current caller does (`scripts/run_nflverse_usage_capture.py`
uses argparse `type=int`; `DEFAULT_SEASONS` is a literal tuple), so this was a false refusal waiting
to be hit, not a live break. Widening to `numbers.Integral` then exposed a second, worse problem the
control caught immediately: the writer serializes with `default=str`, so `numpy.int64` landed in the
artifact as the **STRING** `"2024"` while a python int landed as the **NUMBER** `2024` — the same
capture producing two envelope shapes depending on how the caller built its list. Resolved by
accepting `numbers.Integral` (explicitly excluding `bool`, which is an Integral and would write
`"season": true`) and normalising with `int()`, which is exact and total.

**SEASONAL FREEZE — proved by direct comparison, not by inspection.** The pre-fix
`write_raw_snapshot` was loaded from `git show HEAD:...` into a separate module and run on identical
input beside the fixed one: **filename identical, bytes identical.** Re-verified after the `int()`
coercion landed. Twelve frozen streams write through this path.

**Controls (8):** five illegal shapes refused (each also asserting **no file was written**), the
seasonal envelope pinned key-for-key, the snapshot envelope asserted to carry the partition and no
`season` key, and a five-way parametrized control pinning the season predicate (python int and
`numpy.int64` accepted and both serializing as the JSON number `2024`; float, string and bool
refused).

## 4. V12-5 — one census vocabulary, three views

**Defect.** `rows_not_canonically_identified` was carried at top level and in the `snapshot_*`
aggregates but omitted from the per-stream `by_stream_snapshot` entry — while the GREEN report
claimed "the same census in `by_stream_snapshot`". A census complete in two views and silently short
in the third is how an unresolved population goes invisible to whoever reads the per-stream view.

**Fix.** All three views are now driven off one module-level constant `_SNAPSHOT_CENSUS_KEYS`. They
were three hand-written tuples; the third quietly lacked the field. Sharing the constant makes the
drift impossible rather than fixed once.

**Control (1):** every census key present in `by_stream_snapshot`, each reconciling exactly against
both the run's own coverage block and the `snapshot_*` aggregate, the unresolved count asserted
`> 0` so the control cannot pass vacuously, and the four identity buckets asserted to sum to
`rows_total`.

## 5. G2 seasonal freeze — pinned, no longer a remembered number

`test_the_legacy_seasonal_rows_hash_is_pinned` encodes
`da36dcc59ebb94c30a0c1f1f1cd672059871f2398e126db93ae688ea0210c2c4` against the 169-row
`ngs_passing` slice, plus the mechanism (`content_sha256` must never appear on a seasonal row).
Reproduced independently this session before being pinned. This was previously a value two lanes
had each measured and neither had encoded.

## 6. Also pinned (v11 required controls that had no test)

- `_bind` preserves `refuse_unexpected_columns`; **CONTRACTS True and all twelve prior streams
  False**, with the count asserted at twelve so a new stream cannot join silently.
- `contracts` emits **no `source_era`** — the trace the rejected synthetic-era G1 option would have
  left — asserted on normalized rows, on `stored_columns`, and on `spec.eras`.

---

## 7. Gate

| Check | Result |
| :-- | :-- |
| `tests/contract/test_contracts_ingestion_red.py` | **82 passed** (59 prior + 23 new controls) |
| Focused step-1 ingestion contracts (6 files) | **147 passed** — matches the board's pinned figure |
| `ruff check src app` | All checks passed |
| `git diff --check` | clean |
| `scripts/verify_sprint_closeout.py` | ENFORCE verdict: PASS |
| Full suite | **4,634 passed · 12 skipped · 9 xfailed · zero failures**, `pytest` exit code **0** |

### 7.1 Full-suite measurement

Run after the final `int()` coercion edit. **The invariant is zero collection errors; the count is a
measurement of this tree, never a target.**

`4,634 + 12 + 9 = 4,655`, against `4,632` collected at session start — a delta of exactly the **23**
controls added. Checked against what changed rather than treated as drift, and not treated as a
regression in either direction.

**A process note, recorded because it is exactly the class of error this GREEN is answering.** An
earlier invocation of this gate was piped as `pytest -q 2>&1 | tail -3`, moved to the background on
timeout, and returned **exit code 0 with no pytest summary in its output** — because the pipeline's
exit code is `tail`'s, not the suite's. That run proved nothing and was **discarded, not reported**.
The figures above come from a re-run writing to a file with the suite's own exit code captured
directly. A green-looking exit code from the wrong process is indistinguishable from a passing
suite unless you look.

## 8. Files changed

- `src/dynasty_genius/nflverse_usage.py` — V12-1 check reordered (and its duplicate removed);
  `write_raw_snapshot` envelope validation + `numbers` import; `_assert_snapshot_ledger_constrained`
  added and called; `_SNAPSHOT_CENSUS_KEYS` added and the three census views driven off it.
- `tests/contract/test_contracts_ingestion_red.py` — the V12 durable-controls section (23 controls).

No fixture, no other stream's spec, no product store, no export, no script, no config.

## 9. What I am NOT claiming

- **Not** that contracts is ready to land. Landing is one export covering all twelve prior streams
  plus contracts, reconciling prior published files and the NGS consumers, and needs David's
  explicit separate word.
- **Not** that any of this produces edge. Six tables, zero consumers. `substrate_only` throughout.
- **Not** that the fixes are correct because the tests pass — the tests are mine, and the prior
  cycle is the standing evidence that my own verification is not sufficient. That is what the
  independent review is for.

## 10. Requested

Independent adversarial review of V12-1..5 and the control set: whether each control actually tests
what it claims, whether any control can pass vacuously, and whether the reordering in §1 or the
envelope validation in §3 changes behaviour for any of the twelve frozen streams beyond the
byte-comparison evidence given.
