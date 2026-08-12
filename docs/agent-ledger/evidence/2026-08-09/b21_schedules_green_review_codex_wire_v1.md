From Codex (reviewing lane) — B21 GREEN v1: NOT CLEAR, three consolidated P0 findings

Durable review:
`docs/agent-ledger/evidence/2026-08-09/b21_schedules_green_review_codex_v1.md`

Reviewed RED pin `38fceec11f9a4d623b53dee986fb59efe96fbf12429e18a2950190c9eca9cb86`
and GREEN module pin `6da5666413ee08774aaafd049ba3129516d5fa1e40a2651d86e5e306c1da49ce`.

NOT CLEAR:

1. Production blocker: GitHub's exact release URL normally returns HTTP 302 to a signed
   `release-assets.githubusercontent.com` URL. `HttpFetcher` follows it, then `capture` rejects the
   final URL. A real CLI run against a temporary root retrieved the valid 517,546-byte Parquet and
   exited 1 `source_identity_unexpected`. S8's assertion that every redirect is substitution is now
   falsified by live provider evidence; revise RED and GREEN to admit only the measured sanctioned
   GitHub release chain while preserving requested/final provenance and refusing arbitrary mirrors.
2. Content integrity: pre-seeding `content/<valid-sha>.parquet` with wrong bytes still produced a
   successful marker claiming the incoming hash; `read_raw` returned the wrong hash and
   `partial_artifacts()` was empty. Verify full SHA/size before reusing existing content/check paths;
   fail closed and add the counterexample to RED.
3. Atomicity: production storage raises `OSError`, but rollback catches only `PublishError`; E1's
   collaborator raises the expected type before writing. An injected `OSError("disk full")` at
   index left new content/raw/vintage artifacts, failed count 0, and the exception escaped. Normalize
   real boundary failures, rollback/clean/audit them, and add a production-shaped RED fault.

Positive gates: focused 56 passed; backup suites 27 passed; Ruff clean; diff-check clean. Actual
Parquet validates: 7,548x46, 272 rows for 2026, schema hash `9bbd6413...`, 259 null gametime globally,
zero in 2026, zero null gameday. Full dirty-tree suite: 5,014 passed / 15 failed / 12 skipped / 9
xfail; all failures are the separate untracked governed-cadence RED. No canonical capture performed.

Please return one revised RED pin covering F1-F3, its true RED/collection gates, then revised GREEN
hashes and complete gates. Do not run the canonical capture on this GREEN.
