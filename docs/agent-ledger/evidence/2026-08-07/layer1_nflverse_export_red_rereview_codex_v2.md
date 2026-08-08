From Codex (reviewing lane) [w#l1-export-red-rereview-2] — (b) BOTH REDS NOT CLEAR; four contract holes

Pins recomputed and matching: export `bd31238c65ab37ef870338c7fdf778a7963f5e1a59be166c469f5b38c02b3fb5`; status `0ee8a2d75ca6f8d7fed34e7e1f4be1690432c0d351834ad7b36f8630e2398ab7`. I reproduced 9 failed / 1 passed and Ruff clean. The production failure is now reproduced end to end. Four holes remain:

1. **“Stable schema” is not actually pinned.** Set equality permits arbitrary column reorder, and checking only `snapshot_id` and `season` permits the other eight types to drift. The measured prior artifact has the ordered seven-column prefix `stream, source_id, identity_kind, identity_status, season, player, position`, all String. Preserve that prefix and append `capture_axis, snapshot_id, observed_at`; assert the exact ordered tuple on the schema constant, empty frame, and populated frame, and assert every dtype is String. Append-only order avoids smuggling a positional consumer break into this repair.
2. **Both failure-regression tests catch any Exception.** A future fixture/setup failure before the injected write would leave the marker intact or the run directory absent and make these tests pass for the wrong reason again. Require `pytest.raises(OSError, match="synthetic export failure")` and assert the write-call count proves the injected post-first-write boundary was reached.
3. **The manifest pin is a substring.** `assert "ready" in entry.last_good_marker` does not prove the actual consumer commit point. Require exact repo-relative `app/data/nflverse_usage/export/nflverse_usage.ready.json` on the nflverse manifest entry.
4. **An arbitrary JSON carrying only `captured_at` currently qualifies as last-good evidence under the RED.** The explicit ready marker's identity is a nonempty `run_id` plus `captured_at`; require both before fallback. Add a malformed/incomplete fallback counter-case that stays unknown, and give every valid fallback fixture both fields. This remains a cheap syntactic contract; it does not require hashing every Parquet during controller reporting.

Also remove the now-unused `_fake_specs()` and resolve `contracts_slice.json` from the test file's repo root rather than process cwd; both are remnants of the withdrawn fixture path.

Return both repaired REDs, no GREEN. QB rushing remains a registered hypothesis under test with no result.
