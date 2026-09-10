# DG-213 — publish the verified Dynasty Genius reading

## Problem and outcome

The published Lovable interface cannot load the reviewed player data, and its mobile badge blocks two navigation targets. Deliver the same reviewed roster, independent valuations, market comparisons, available-player pool, headshots and saved track-record reading through permanent public storage, with working mobile navigation.

David already authorized Lovable as the interface, no sign-in, and commit/push/merge/publication. He directly granted the native Lovable upload, database and message tools through Claude permissions on September 10. Those user-owned permissions remain unchanged. Upload only reviewed user-visible JSON and photos; exclude raw provider files, credentials, model artifacts and private paths.

## Delivery contract

- Preserve the accepted v4 export: 27 roster players, 433 available players, 388 comparable model/market ranks and 954 headshots. Keep missing forecasts/prices distinct from zero. No forecast, valuation or evaluation changes.
- Store 956 manifest-listed assets plus the manifest itself in one versioned public-read bucket. Set content types from the manifest: 953 PNG images and one WebP have `.jpg` filenames. Create no anonymous write policies; upload without overwriting existing objects and verify any collision before skipping it. Publish the manifest last.
- Pin the permanent base URL and manifest SHA256 in `lovable/src/lib/dg/release.config.ts`. Accepted manifest digest: `2e3027eaeebb0b85c3ee6c6d1ab771fa24721e7362ac09d3f21497effd808f42`.
- Hash documents before parsing them and require their declared lengths, schema, source provenance and selected reading to match. Refuse a broken release or unavailable pinned reading without substituting another source or scoring method.
- Preserve explicit local mode when the release constant is null. Hosted mode reads the fixed published snapshot and disables saving with a plain-language explanation.
- Reserve mobile navigation clearance for the Lovable badge and verify actual hit targets at 390px and 320px.

## Ownership and verification

Claude54281 owns supported platform transfer and returned-change receipts. Claude54410 owns runtime and explicit local/hosted test fixtures. Claude54331 independently reviews platform/source changes. Root owns final configuration, independent public-file checks, integration, landing, publication and browser verification.

Verify every permanent public object independently for bytes, SHA256, MIME and CORS. Run the relevant exporter and frontend suites, typecheck, lint and production build. Exercise roster, board, league directory, player comparison, track record, player search/drawer and mobile navigation against actual public assets. Confirm the published site uses the reviewed reading and retains the disabled hosted Save behavior.

Tests must declare local or hosted configuration explicitly and must not use the production URL or live network. Mutation checks must show that removing local-mode pins exposes the original failures.

Every Lovable agent message requires inspection of its returned commit diff. Preserve the previous 49-file verified baseline plus the explicitly reviewed two-file generated Supabase delta at `c37bab2d`; exact bytes remain the default for all other paths. Do not broaden this exception or trust a claim that no files changed without checking the diff.

## Landing and boundaries

After public-file and local app verification, stage only the named source, test and plan files. Preserve the original ticket checkout and immutable runs, and use a separate disposable landing checkout for the official `dg-land.sh` gate. That gate also runs the Python and legacy frontend suites. Transfer source to the existing Lovable project from immutable landed GitHub URLs, verify the actual returned paths/content, then publish and inspect the live desktop/mobile app.

No dependency installs, shared-trunk/data edits, model changes, ingestion activation, new service, project relinking, or access to `frontend-studio`. DG-214/215/216 ingestion activation remains separate. Preserve unrelated worktrees and all immutable evidence.

Evidence and historical permission dispositions are retained under `runs/20260910T001048Z/`, `runs/20260910T123046679562Z-hosted-resume/`, `runs/20260910T125748Z-dg213-test-isolation/` and `runs/20260910T151911Z-hosted-permission-resume/`. Current delivery status belongs in the ticket and handoff, not in this implementation contract.
