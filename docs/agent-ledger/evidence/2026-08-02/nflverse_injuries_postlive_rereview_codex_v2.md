# nflverse injuries post-live correction — Codex re-review v2

Date: 2026-08-02  
Layer: 1 (ingest)  
Verdict: **NOT CLEAR — two blocking rows and one material record defect**

## Scope and method

Reviewed Claude's uncommitted correction in:

- `src/dynasty_genius/nflverse_usage.py`
- `tests/contract/test_nflverse_injuries_red.py`
- `tests/contract/test_nflverse_usage_ingestion_red.py`
- `tests/contract/test_ingestion_properties_red.py`
- `requirements.txt`
- `requirements-dev.txt`

No file in that scope was edited by Codex. The three focused suites pass (`93 passed`), so each
finding below is specifically a case the green suite does not distinguish from correctness.

## R2-B1 — exact-era validation checks only the first record (blocking)

`normalize_rows` resolves `available = set(records[0].keys())` once, selects an era once, and never
checks the remaining records' key sets. A mixed-shape batch therefore defeats the exact-column-set
contract.

Reproduced with a valid revisioned row first and a second row carrying
`unexpected_provider_field`:

```text
accepted_rows 2
extra_survives False
```

The second row was accepted and the provider field was silently discarded. A second probe removed
`report_primary_injury` only from the later record; the batch was accepted and stored that field as
`None`:

```text
missing_later_accepted 2 None
```

The new positive control covers only a one-row batch where the unexpected field is on
`records[0]`. The contract must either prove upstream construction makes every record's key set
identical before `normalize_rows`, or validate every record against the selected era. The latter is
the safer boundary because `normalize_rows` publicly accepts `Sequence[Mapping[str, Any]]` and test
injection is a supported capture path.

## R2-B5 — fail-closed error text contradicts the explicit migration contract (blocking)

`UsageStore.migrate_additive_columns` is deliberately explicit and never runs on store open. But
`_assert_schema` says:

```text
Additive widening is applied automatically
```

That is false, and it misdirects the exact operator facing an old production store. The message
must name the explicit `UsageStore.migrate_additive_columns(...)` entry point (or an actual CLI if
one is added) and preserve the distinction between additive migration and non-additive refusal.

## R2-M1 — the Hypothesis contract repeats the corrected overclaim (material)

`tests/contract/test_ingestion_properties_red.py:13-15` says every hand-enumerated input class —
including `None`, integer/float/text variants, duplicate keys, and blank grain coordinates — is a
case Hypothesis "generates on its own." That is not what these two properties do. The first test
explicitly constructs the int/float/text axis; the second generates whitespace strings only. It
does not generate `None`, duplicate rows, or grain-coordinate combinations.

This was already corrected to David in the durable tooling answer. Committing the old overclaim in
the test module would reintroduce the factual error. Rewrite the module description to state the
actual earned contribution: generated value coverage and shrinking within explicitly selected
invariants.

## Rows independently confirmed closed

The corrected body does close the original B2, B3, B4, B6, M1 (numeric refusal), and M2 mechanisms,
and B1 for a homogeneous batch. The remaining rows above prevent a production-grade CLEAR.

## Provider-bundle finding M-C1

Claude's M-C1 is **accepted**. `freeze_review_target.py` now enumerates
`git ls-files --others --ignored --exclude-standard` within the exact scope and refuses with
`review_scope_contains_ignored_files` before building a target. A new throwaway-repository contract
creates a real ignored in-scope file and proves the refusal. Focused census: `10 passed`; Ruff clean.
A new frozen target will be issued after the final review edits so the target includes this repair.
