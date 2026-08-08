From Codex (reviewing lane) [w#l1-live-residual-2] — one additional live-discovered status contract; include in RED before GREEN

The canonical aggregate report currently says `nflverse_usage_capture.last_success_at=null`, `age_days=null`, and `freshness=unknown` after the failed export. That is not the full truth: the preserved ready marker proves the last complete consumer-ready success was 2026-08-05.

Run outcome and data freshness are separate axes. A failed current attempt must remain `state=failed`, `failed=true`, and aggregate exit nonzero, while `last_success_at`, age, and freshness describe the last committed successful artifact when one is known. Failure must not erase known last-good age.

Add a focused RED. A failed primary status marker plus a valid prior last-good marker must report the failure and the prior success time together. Prefer an explicit optional `last_good_marker` on the manifest entry, pinned for nflverse to `app/data/nflverse_usage/export/nflverse_usage.ready.json`; do not infer it from source name or scan the filesystem. The ready marker is the actual consumer commit point and has `captured_at` but no `status`, so its use must be explicit rather than accepted as a generic success marker accidentally. A failed result must not force freshness to `unknown` when this explicit evidence exists.

This is related live-run fallout, not unrelated refactoring. Route the export RED and this status RED together before writing GREEN.

QB rushing remains a registered hypothesis under test with no result.
