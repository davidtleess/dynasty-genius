# QB-1 D1 fetch audit — Codex v2

**Verdict: CLEAR after receipt correction.**

- Manifest SHA-256: `98209e54f1bf9401ecd2b5ca107f35dc77f2833021b8d738bb4241b878d2cd4a`.
- Script SHA-256: `149283b70f62ff57e6b0c5295d367479e9c7fdd451ed3a57cc376bc9cd27248d`.
- B1 is resolved: the impossible approximation was replaced by the honest
  bounded window “between 11:27 ET and 11:52 ET (exact instant not independently
  captured),” and `timestamp_correction` preserves the defect history.
- The independent substrate audit was rerun after correction: 7/7 datasets,
  17/17 exact SHA values, 154,360,748 bytes, all required columns and temporal
  coverage, no extra Parquet files, completion receipt newer than all snapshots,
  exact backup entry. Snapshot bytes are unchanged.
- W1 remains accepted as a GREEN obligation under the execution RED:
  invalidate the completion receipt before a rerun and atomically replace it on
  success. It does not invalidate this first completed substrate.

No provider call or refetch was performed by Codex. This audit establishes
substrate admissibility only; it is not a QB-1 result. H2 QB rushing remains
**UNDER TEST**.

