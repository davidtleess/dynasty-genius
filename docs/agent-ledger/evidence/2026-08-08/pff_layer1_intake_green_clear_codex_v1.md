# PFF Layer 1 intake/indexer — Codex GREEN CLEAR

**Reviewed:** 2026-08-08 03:29 ET  
**Layer served:** Layer 1 — source acquisition, lossless persistence, intake, and refresh-state reporting.  
**Ruling:** **CLEAR** for the six pinned code/contract paths below. The ruling does not authorize provider contact, an automated PFF fetch, a scheduler, analytical scope selection, row normalization, consumer rewiring, or promotion of PFF grades to a model surface.

## Reviewed pins

| Path | SHA-256 |
|---|---|
| `src/dynasty_genius/sources/pff_intake.py` | `c73dea2643129e7e4544f4b0108490e45b9040be3e9754745f0abe2bc0c75d2c` |
| `scripts/run_pff_intake.py` | `66d7ba5190a4e08cd4fa17793f4aa07232b2f2cde446510dddd28bc54a97ec19` |
| `src/dynasty_genius/sources/daily_control.py` | `23a68d71686254b1ef74392414d0afd1287b6b43128651d72aca0e57f5d3bf5c` |
| `tests/contract/test_pff_intake_red.py` | `268cbd1233d584cdc7831f7b9e51ae6afbfe2051c02f35de99731736ff7c6efb` |
| `tests/contract/test_layer1_daily_control_red.py` | `932b2ea265a29445a6d96756ad2c46fc6e5dbf359becddca45e2e316d3bd2656` |
| `tests/contract/test_backup_manifest_anti_rot_red.py` | `3429e08de629d37dcdae7c9c9b5729dde98bce966dea795263f4cbdad4e9a93c` |

## What is now true

- PFF remains a **manual download** source. No network or provider-contact path was added.
- A sidecar-declared, operator-callable intake CLI now copies payloads into the existing content-addressed private raw tree and commits metadata in one SQLite transaction.
- Payload identity is SHA-256; offering identity is `(batch_id, offering_id)`. Distinct offerings of the same bytes remain distinct provenance mappings without duplicating the payload.
- Layer 1 performs no REG/REGPO selection, duplicate-vintage winner selection, status filtering, or cross-family/schema flattening.
- Unknown schemas are durably preserved and indexed with `review_required`; transport success and evidence-review state remain separate axes.
- The daily controller now recognizes PFF as a complete manual route and reports manual freshness from the newest declared source retrieval time, not the index execution time.

## Private acceptance evidence — aggregate only

The governed private archive was backfilled through the production CLI after the path-isolation repair:

- 149 distinct payload SHAs;
- 307 offering mappings;
- 7 report families;
- 12 schema hashes;
- all 6 governed legacy status labels preserved;
- 0 payload-hash mismatches;
- 0 unresolved offering-to-payload mappings;
- exact replay idempotent;
- 149 raw files remained byte-identical and their mtimes were unchanged;
- governed inventory/coverage/download-map artifacts remained unchanged;
- production latest-attempt and ready markers both point to source retrieval `2026-08-01T09:23:59.950822-04:00`;
- live manual status: `manual_due`, `failed=False`, age approximately 6.74 days at review time.

No paid headers, rows, player identities, grades, or external source paths are reproduced here.

## Blocking defects found and closed during review

1. **Cross-root contamination:** isolated runs could use custom ledgers/stores while silently overwriting production markers or the governed raw tree. Any deviation from the exact canonical store/ledger pair now requires explicit paired marker paths.
2. **Within-batch duplicate payload rollback:** two offerings of identical bytes in one batch attempted two payload inserts and rolled back. The batch now yields one payload plus both mappings.
3. **Missing governed catalog default:** the documented production invocation would have quarantined every payload. The CLI now defaults to the governed schema catalog and fails safe to review-required when the catalog is absent or unreadable.
4. **Partial staging:** validation and copying were interleaved, so a later bad offering could strand an earlier unindexed copy. Intake now validates/profiles the complete batch before copying and refuses to overwrite a conflicting canonical object.
5. **Unsafe retrieval time:** `retrieved_at` was string-sliced into a path, so a traversal-shaped value could escape the declared report/scope/season layout while returning success. It is now parsed as a timezone-aware ISO instant before any copy, and the canonical date comes from the parsed value.
6. **Broken live manifest integration:** PFF's importer was a bare string, so the controller iterated its characters as paths; a substring assertion passed vacuously. The manifest now uses the required one-element tuple and the contract asserts real `entry_status(...).ok` behavior.
7. **Backup anti-rot false negative:** `app/data/pff_exports` was already a required recursive backup directory, but the test recognized only exact covered paths. Directory coverage now mirrors the backup runner's real `rglob` behavior with a slash boundary; the manifest was not duplicated, avoiding duplicate DB uploads.

## Gates

- PFF intake contracts: **66 passed**.
- Daily-control contracts: **67 passed**.
- Last-good freshness contracts: **17 passed**.
- Combined focused set independently rerun by Codex: **150 passed**, true pytest exit 0.
- Backup anti-rot: **5 passed**, true pytest exit 0.
- Existing PFF consumer regression slice: **23 passed, 3 skipped**.
- Ruff / diff check: clean.
- Final unmasked full suite: **4,846 passed, 12 skipped, 9 xfailed, 0 failed, 0 collection errors**, true exit 0.
- Real Layer 1 preflight: 20 routes checked; PFF complete; only RotoViz and Campus2Canton remain incomplete because no importer exists for them.

## Boundaries that remain

- This creates no automated PFF acquisition. A human still downloads the subscriber export and supplies an explicit sidecar.
- Local target cadence remains daily, but source publication cadence is not inferred and the A-C publication-cadence fields remain open.
- No normalized PFF analytical/query store is created. Payload rows remain private raw evidence.
- No existing Phase 13/16 consumer or manifest is rewired.
- H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result; this intake work supplies no evidence about it.
