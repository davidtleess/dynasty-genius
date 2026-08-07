## CH1 per-stream season isolation — Codex RED

### Preflight

- **Layer:** Layer 1 data ingestion/refresh containment.
- **Authority:** David's narrow code authorization, relayed by Claude as `w#3qqyaf18-1`.
- **Authorized behavior:** isolate the five nflverse loaders so one dataset's absence cannot cap the
  other datasets, and handle both `ConnectionError` and provider/client `ValueError` failures.
- **Excluded:** capture, store, scheduler/plist, consumer migration, Option A construction, commit,
  push, and Layer 2 work.
- **Review role:** Codex authors failing durable controls; Claude implements GREEN; Codex reviews
  the resulting target state independently.
- **Branch:** `fix/ch1-per-stream-season-isolation` is acceptable, but branch creation/switching is
  left to the implementing lane because the checkout is shared and currently contains unrelated
  parked work.

### Intended RED surface

1. A single `ConnectionError` does not lower healthy streams' effective seasons.
2. A single loader `ValueError` is isolated and does not crash the refresh.
3. All five loaders failing is loud and cannot create a silent partial success.
4. A successfully returned empty frame remains distinguishable from a failed/absent stream.
5. The report/marker records each stream's effective season and failure state.
6. Per-stream season differences participate correctly in source hashing and no-op behavior.
7. The pre-existing NGS last-good-export path is unchanged.

### Durable controls authored

File: `tests/contract/test_feature_refresh_source_isolation_red.py`  
SHA-256: `e5fa0f03557f09b072a9efde7dc9ee97a032540c0f2a8846f0fca44425b9eae0`

1. `test_ch1_connection_and_value_errors_are_isolated_per_stream`
2. `test_ch1_unavailable_and_successful_empty_are_distinct_without_capping_healthy`
3. `test_ch1_all_five_unavailable_fails_loudly_before_hash_or_publish`
4. `test_ch1_stream_provenance_participates_in_source_hash`
5. `test_ch1_stream_provenance_is_persisted_in_latest_report`
6. `test_ch1_ngs_last_good_export_path_is_unchanged`

### RED result against the unfixed implementation

`pytest -q tests/contract/test_feature_refresh_source_isolation_red.py`:

- **5 failed, 1 passed**.
- Failures independently reproduce: dict-literal preemption on `ConnectionError`; the same
  preemption for a fully unavailable single stream; uncaught all-source failure; absence of
  provenance in the source-hash contract; and absence of provenance in the latest report.
- The passing control proves the NGS last-good local-export route already behaves as required and
  must remain unchanged.

Pre-existing focused contracts remain green: `test_feature_refresh_runner.py` plus
`test_feature_refresh_ops_scheduler.py` — **21 passed**. `uvx ruff check` on the RED file passes,
and `git diff --check` is clean for the two Codex-authored paths.

No production code was changed. No branch switch, commit, push, capture, scheduler, store, or
consumer migration was performed. H2 QB rushing remains a registered hypothesis UNDER TEST with
no result.
