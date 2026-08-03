# nflverse injuries post-live correction — Codex CLEAR

Date: 2026-08-02  
Layer: 1 (ingest)  
Verdict: **CORRECTION CLEAR**

Claude's corrected body closes the three v2 re-review rows:

1. Every record in an era-bearing batch is checked against the selected era's exact column set.
   A later added field and a later missing field both refuse with
   `nflverse_heterogeneous_batch`; a homogeneous multi-row batch remains accepted. Codex reran the
   original counterexample and independently observed the typed refusal.
2. The schema-mismatch message now states that widening is not automatic and names the explicit
   `UsageStore.migrate_additive_columns(db_path, specs)` entry point.
3. The property-test module now accurately says the invariants/type axes are hand-selected and
   Hypothesis contributes generated value coverage and shrinking inside those invariants.

Independent focused census:

```text
97 passed
Ruff: all checks passed
```

This CLEAR covers the corrected injury/ingestion/property-test body only. It is not a statement
that the complete tooling authorization is finished: the nflverse column+dtype fingerprint bundle,
archived-real schema-era replay/live fingerprint preflight, and isolated mutmut pilot remain to be
implemented and measured before David's instruction to complete all authorized recommendations can
be called done.
