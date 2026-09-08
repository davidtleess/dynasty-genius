# Lovable interface integration — DG200

David approved the existing Lovable app as the Dynasty Genius interface on September 8, 2026. This local integration retains that project's source and visual design and reads the accepted DG backend snapshot.

Source project: https://lovable.dev/projects/9cc0d744-2c07-43cb-932b-ed9d91440ca1

Imported revision: `5b487ffd31d922011e558be1e2e2706adb66c3a2`. Exact source responses and hashes are retained separately in the DG202 source export and DG200 run evidence. `.env` was deliberately not imported. The public badge slug is not the project UUID. No GitHub synchronization or hosted modification is implied by this import.

## What supplies the numbers

The browser reads one same-origin `/data/dg-bundle.json` response for a page load. It contains the accepted market-ranks, roster/available forecasts, and available-player catalog. The frontend checks that the report, catalog, ownership and market context agree before displaying any rows. It preserves rank intervals and missing values. No Supabase value query or alternative Lovable scorer participates.

- Ranks compare the same common player population. Rank ties remain spans.
- Projected advantage means five equally weighted seasons of points above positional replacement. It is separate from FantasyCalc's trade price.
- Current/future points are forecasts, not predicted lineup gains or a proven pickup recommendation.
- The relevant unowned pool is exactly the catalog's `default` population. Missing forecasts remain visible and starting estimates remain labelled.
- Photos are identity assets from the previously verified cache, with an initials fallback.

The initial staged data is the September 6 research snapshot: 825 original forecasts, 388 common ranked players, 27 roster players, and 433 relevant unowned players (360 with numbers, 73 without). A later file-generation time does not change those dates. The interface is explicitly pinned; “Reload saved snapshot” fetches the staged file again, not a new model run.

## Local inputs and checks

The dependency set and Bun lockfile come from the imported project. David approved isolated setup with “continue” after an explicit request. Bun 1.4.2 was staged in the private run tooling directory and `bun install --frozen-lockfile` installed the existing lock; the lockfile hash is unchanged. No global/shared environment was modified.

The DG201 exporter is `src/dynasty_genius/adapters/lovable_bundle.py` in the backend repository. It reads existing API responses or saved response files and writes a fresh, versioned bundle. It does not train or run models, update shared data, or sync Supabase.

Local review assets live under ignored `public/data` and `public/assets/headshots`, pointing only to private DG200 run copies. They are excluded from Git. Without an explicitly staged snapshot, the interface must show an error, never use the old prototype scorer as fallback.

Verified: `npm test` (14 passed), `npm run typecheck`, `npm run lint` (0 errors / 7 nonblocking fast-refresh warnings), `npm run build` (Lovable/Cloudflare), and `npm run build:local` (Node). Built browser QA passed at desktop/tablet/phone widths, including failure and missing-data cases.

Built local preview: http://127.0.0.1:8797/. Frozen Node output lives in `../runs/20260908T211742Z/runtime-verification/final-local-build`; start with `NITRO_HOST=127.0.0.1 NITRO_PORT=8797 node <output>/server/index.mjs`. The default build remains the original Lovable target. See `../docs/plans/2026-09-08-lovable-adoption-handoff.md` for evidence and publication limits.

## Remaining publication work

This is an isolated source integration, not a deployment. The hosted Lovable project and production backend remain unchanged. Before publishing, select and verify private hosted data access and authentication, connect the intended snapshot refresh path, and test the deployed browser's actual source/version. A local file or localhost backend URL alone is not that connection. Do not publish the ignored personal snapshot/photo assets or enable imported sync hooks without the relevant authorized publication step.

The imported refresh hook and refresh server function are disabled in this local consumer. Its former independent scorer and Supabase history are retained only in source provenance; they are not accepted model outputs or validation of the backend. Broader trade/track-record features must be connected and verified before their original claims can reappear.
