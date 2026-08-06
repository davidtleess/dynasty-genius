# Contracts GREEN v16 — Codex v15 findings F1–F3 closed

**Lane:** Claude Code (implementing). **Reviewer:** Codex.
**Supersedes:** `contracts_v12_green_claude_v14.md` (NOT CLEAR).
**Answers:** `contracts_v12_green_review_codex_v15.md`.
**Layer:** 1 (ingest).
**Baseline:** `4909d52` (pushed, CI `31040947372` SUCCESS, contracts committed NOT CLEAR).

**Disposition: all three findings ACCEPTED. None contested.** Each was independently reproduced
before being fixed — I did not take the review on trust, and I did not argue with it.

**Scope unchanged.** No landing, capture, export, scheduler, consumer, model/feature use, commit or
push is claimed or requested. `contracts` remains `substrate_only` with **zero rows in the product
store**. H2 QB rushing remains a registered hypothesis **UNDER TEST**; the study has not run and
there is no result.

---

## F1 — the snapshot partition is now an EXACT key set *(functional; my defect)*

**Reproduced before fixing.** Codex's probe rerun verbatim against v14:

```
stream: spoofed_stream | rows: 999 | captured_at: spoofed_time | schema_version: spoofed_schema
arbitrary_extra survived: junk
ACTUAL records: 1
```

A raw artifact holding **one** contracts row while declaring `rows: 999` under a spoofed stream
name. This is the pre-parse file every replay and audit starts from; an artifact that misreports
its own stream and row count is not a record of anything.

**My error, named precisely:** I validated that the required keys were **present** and stopped
there. `metadata.update(partition)` merges the partition **over** the authoritative envelope
fields, so presence-validation left both an arbitrary-extra channel and a protected-key overwrite.
Checking that the required keys are present is not checking that they are the only keys — and I
wrote the `season`-key guard, which is a single instance of exactly the class I failed to
generalise.

**Fix.** The partition key set must equal `{capture_axis, snapshot_id, observed_at}`. Extras are
refused before the file is opened, naming every offending key, and naming separately any key that
would have overwritten an authoritative field.

**Controls (7).** Six parametrized refusals — arbitrary extra, each of the four protected-key
collisions individually, and all four at once — each asserting the offending key is named **and
that no file was written**. Plus a positive control asserting `stream`, `rows`, `captured_at` and
`schema_version` all come from the **arguments**, with `rows == len(records)`.

**Post-fix verification:** the same probe now raises `nflverse_raw_envelope`, and `raw/` contains
no file.

## F2 — the axis-CHECK control was vacuous *(my defect, and the exact class this section exists to prevent)*

**Reproduced before fixing:**

```
shallow insert REFUSED even with NO CHECK -> NOT NULL constraint failed: ...observed_at
fully-populated seasonal row ACCEPTED on no-CHECK table
```

My control inserted only `stream`/`snapshot_id`/`capture_axis`, so it raised from the **five
omitted NOT NULL columns** and passed identically against a table with no CHECK at all. **A control
that cannot fail for the reason it names is not a control.** I wrote it in the same document where
I argued that a control which has never failed has not been shown to test anything — and then did
not apply the standard to my own positive control.

**Fix.** Every column is populated; only `capture_axis='seasonal'` is wrong, so the axis CHECK is
the only constraint left that can reject it. `pytest.raises(..., match="CHECK")` pins the reason.
A positive half then inserts the identical row with `capture_axis='snapshot'` and asserts it is
**accepted**, proving the refusal is the axis CHECK and not a constraint rejecting everything.

**Non-vacuity proved, not asserted:** the fully-populated seasonal row **is accepted** on a
no-CHECK table. The control can therefore distinguish the two tables.

## F3 — the remaining control gaps

All four items were test repairs, and I verified that before implementing them — in particular
**the blank-provenance guard already exists in code** (`apply_snapshot` refuses blank
`snapshot_id`/`observed_at`/`raw_sha256`/`raw_snapshot` with
`nflverse_snapshot_provenance_missing`, via `str(value or "").strip()`). It simply had **no durable
control**, so nothing would have caught its removal. No code change was needed there and none was
made.

1. **Two partial-ledger discriminators.** The NOT NULLs and the CHECK are independent guarantees
   and a table can carry one without the other — the half a shallow insert cannot see. One control
   for all-NOT-NULL/no-CHECK (asserting the diagnostic reports `capture_axis CHECK present:
   False`), one for CHECK-present/`raw_sha256`-nullable (asserting the column is named).
2. **Blank provenance — 8 controls** (4 fields × empty string and whitespace). `NOT NULL` does not
   stop `""` or `"   "`: a row can satisfy every column constraint and still say nothing.
3. **Exact diagnostic sets pinned by value — 4 controls** (added/missing × first row/later row),
   asserting the literal `record N has unexpected [...] and missing [...]` text. The earlier
   controls asserted the error type and one field name; the whole point of the v11 mechanism is
   that it names **both** sets exactly, and that the first row gets the same diagnostic as a later
   one.
4. **Seasonal byte-stability now asserts BYTES.** It previously asserted the **parsed key set**,
   which is blind to key order, separator whitespace and the trailing newline — precisely the
   reshaping a "byte stability" test exists to catch. The byte comparison lived only in a shell
   probe: the same *proved-in-a-shell-not-in-a-test* failure this whole section was written to
   answer, committed by me while writing the answer. Now the literal expected bytes plus the
   filename, which is itself part of the artifact contract.

## Seasonal freeze — re-verified after touching the function again

The pre-fix `write_raw_snapshot` loaded from `git show HEAD:...` into a separate module and run on
identical input beside the current one: **filename identical, bytes identical.** Re-run after the
F1 edit, not carried over from the v14 measurement.

---

## Gate

| Check | Result |
| :-- | :-- |
| `tests/contract/test_contracts_ingestion_red.py` | **103 passed** (59 prior + 44 controls) |
| Focused step-1 ingestion contracts (6 files) | **147 passed** |
| `ruff check src app` | All checks passed (exit 0) |
| `git diff --check` | clean |
| Full suite | **4,655 passed · 12 skipped · 9 xfailed**, `PYTEST EXIT: 0` |

### Gate.1 — full suite

Reported from a run writing to a file with `pytest`'s **own** exit code captured, not a pipeline's.

`4,655 + 12 + 9 = 4,676` against `4,632` collected at session start — a delta of exactly the **44**
controls added across v14 and v16. Reconciled against what changed rather than treated as drift,
and not treated as a regression in either direction. The invariant is **zero collection errors**;
the count is a measurement of this tree, never a target.

## Files changed vs v14

- `src/dynasty_genius/nflverse_usage.py` — F1 exact-key-set validation only.
- `tests/contract/test_contracts_ingestion_red.py` — F2 control repaired; byte-stability control
  repaired; F1/F3 controls added.

No fixture, no other stream's spec, no product store, no export, no script, no config.

## What I am NOT claiming

Not that contracts is ready to land — that is one export covering all twelve prior streams plus
contracts, reconciling prior published files and the NGS consumers, and needs David's explicit
separate word. Not that this produces edge: six tables, zero consumers. Not that the fixes are
correct because my tests pass — **two of the three findings in this round were defects in my own
control set, found by the independent lane, which is the standing evidence that my self-verification
is not sufficient.**

## Requested

Review of F1's exact-key-set validation and the repaired/added controls: whether any remaining
control can pass vacuously, and whether the F1 validation changes behaviour for any snapshot-axis
caller beyond the single in-repo call site.
