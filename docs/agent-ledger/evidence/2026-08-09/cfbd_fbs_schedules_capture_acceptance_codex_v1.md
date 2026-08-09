# CFBD FBS schedules — first canonical capture acceptance packet

Date: 2026-08-09  
Layer: 1 — source capture and retained provenance  
Implementation/capture lane: Codex  
Independent behavioral and store reviewer: Codex root lane  
Status: **CAPTURED, COMMITTED, PUSHED, AND EXACT-SHA CI GREEN**

## Provider offering and call accounting

- Provider/report family: **College Football Data API / `games`**.
- Exact request: `GET https://api.collegefootballdata.com/games?year=2026&seasonType=both&classification=fbs`.
- Authentication: configured `CFBD_API_KEY` sent only as an `Authorization: Bearer` header.
- Canonical retrieval time: `2026-08-09T13:15:10.160797+00:00`.
- Provider `Date`: `Sun, 09 Aug 2026 13:15:11 GMT`.
- Actual local HTTP attempt/request count: **1**. No `/info/usage` or other accounting request was
  made.
- `X-CallLimit-Remaining` after the response: **73,014**;
  `call_accounting_quality=request_count_and_remaining_header`.
- This ticket made exactly one paid provider request. Replay and every subsequent measurement were
  local reads.

## Exact raw artifact

- Content object:
  `app/data/sources/cfbd_fbs_schedules/raw/content/76f0af56c90374ed37924c2a7a687cdf5931938f5efb29a7f6edf9b0b94e99e3.json`.
- Check object:
  `app/data/sources/cfbd_fbs_schedules/raw/checks/c-20260809T1315101607970000-76f0af56c903.json`.
- Byte count: **655,068** each.
- SHA-256: `76f0af56c90374ed37924c2a7a687cdf5931938f5efb29a7f6edf9b0b94e99e3`
  for both; byte-for-byte equality independently verified.
- Secret scan over every retained store file: **0 configured-key hits, 0 `Authorization` hits,
  0 `Bearer` hits**.

## Canonical store and measured payload

- Store root: `app/data/sources/cfbd_fbs_schedules/` (**six files**, no partial artifacts).
- Vintage: `v-76f0af56c90374ed` at
  `app/data/sources/cfbd_fbs_schedules/vintages/v-76f0af56c90374ed.json`.
- Vintage file SHA-256: `0a5d63d2a96084bafb09a4b3996f37eb4d85e156b30b687bdd8b0b60df0d2b12`.
- Source rows/fields: **888 × 34**.
- Recomputable observed-schema SHA-256:
  `0a87d5754e304d6c67c21b03191ca395df9d312ed5f469ada00e7826e3130d31`.
- Pinned validation contract: CFBD OpenAPI **5.21.0**, SHA-256
  `f6274010fb8f3d11c4c574fd4d648fd33e6c47e0eca2cfb61b481b20ca482ea3`.
- Scope census: season 2026 **888**; regular **888**; postseason **0**; completed **0**;
  incomplete **888**; home FBS **888**; away FBS **761**; away FCS **127**; rows without at
  least one FBS side **0**; duplicate game IDs **0**; non-null playoff objects **0**.
- The 127 FBS-vs-FCS rows are source-authentic: CFBD's FBS competition filter includes games against
  non-FBS opponents.

## Marker, audit, replay, and failed-attempt behavior

- Marker: `status_latest.json`, SHA-256
  `225af6bb59c83874bbd7a736257d68a12676ac4e8579633df767e404e900d511`.
  It reports `status=ok`, the exact provider/query/retrieval/hash/bytes/rows/schema, and
  `last_good_vintage_id=v-76f0af56c90374ed`.
- Index: `index.json`, SHA-256
  `6ba21df5aa51c9e6f2dc77dbc20501e152bfeb288fb72a3ba02e5812c011a057`:
  **1 check / 1 vintage / total_request_count 1**.
- Ledger: `ledger.jsonl`, SHA-256
  `0b400916a6a4a689ebc7cd5a7ab2cdb71920b868547a6e512bd3fd168b47fd2c`:
  **one success / zero failures**.
- Local `replay(check_id)` returned **888 rows** and the exact raw SHA. The complete canonical file
  census and ledger remained byte-identical; no check, vintage, audit event, or request was minted.
- No live failure was manufactured after spending the paid request. Offline contracts prove that
  transport, validation, source-identity, corrupt-state, content-integrity, and all five publication
  boundary failures quarantine/audit as applicable, preserve the prior last-good state, and leave no
  partial canonical artifact. Success-audit publication is itself atomic and transactional.

## Final code/document pins

- RED contract: `tests/contract/test_cfbd_fbs_schedules_capture_red.py`, SHA-256
  `26a61170336cd6e2bfa2bcc299e6243ea88c8ac017cd2972617f8e9700d80335`.
- Capture module: `src/dynasty_genius/sources/cfbd_schedules_capture.py`, SHA-256
  `22aff76c0a1beb863390044470177dc540b1e705ffa79986158e0db348999e3f`.
- CLI: `scripts/run_cfbd_schedules_capture.py`, SHA-256
  `a03bd4ed3a76242c1a94493a27b2a6f9b6a1ac2438eacf3fdc923141478f2f47`.
- Backup manifest, added only after independent populated-store verification: SHA-256
  `22afdf528d90febd2bad7e51f5e0099fe79c96eecdfb3508396be1e82dbda396`.
- Canonical catalog after adding measured N20: `docs/layer-1-data-inventory-catalog.md`, SHA-256
  `7e3c3e8f71b9adb59abad2e948d727c4319bd401e0f2b6238fc36da6a678a402`.

## Verification gates

- RED-before-GREEN first round: **171 failed / 1 disclosed pass**, true exit 1.
- GREEN review repairs: the P0-1 through P1-5 contracts produced **15 failures** against the
  unrepaired module; the final canonical-vintage substitution produced **1 failure / 3 replay
  positive-control passes** against the preceding module.
- Stabilized focused suite: **191 passed**.
- Ruff across RED/module/CLI: **clean**.
- Backup manifest anti-rot + directory suites after store population and manifest addition:
  **12 passed**.
- Clean-tree simulation (HEAD archive plus only CFBD module/CLI/RED/manifest/store):
  **203 passed** (191 focused + 12 backup).
- Full suite: **5,222 passed / 15 failed / 12 skipped / 9 xfailed**. All 15 failures are the separate,
  withdrawn/untracked `test_governed_cadence_inputs_red.py`; no CFBD or backup failure occurred.
- Full collection before execution: **5,257**, zero collection errors.

## Catalog and landing state

- The Layer 1 catalog now records this distinct physical CFBD store on A4 and as measured stream
  **N20**, without adding its grain to the existing N16/N17 CFBD foundation counts.
- The required backup-manifest entry was deliberately withheld until the populated store was
  independently verified, then added; backup suites are green.
- No broad staging occurred. The frozen wire files, loose plists, withdrawn cadence RED, and
  unrelated evidence remain untouched.

## Explicitly unavailable or unverified

- This 2026 response contains no postseason, completed, score-bearing, or non-null playoff row;
  those accepted shapes are pinned from the committed OpenAPI and falsified offline, not observed in
  this vintage.
- Provider publication cadence/change rhythm is not established by one capture. Governed cadence
  inputs remain a separate ticket.
- No scheduler is installed; no consumer is migrated; no cadence input, feature, model, or product
  surface uses this store.
- No second paid request was made, so no live no-change reacquisition was performed. Idempotence is
  established through zero-call local replay and offline identical-content reacquisition contracts.
- The root lane committed and pushed the already-cleared CFBD landing as
  `a08247d972eafb38c1aa0b8b25d6c25e6a144d04` (`feat(data): land CFBD FBS schedules capture`)
  while the implementation lane's full suite was finishing. The commit contains the pinned code,
  contract, manifest, catalog, six-file store, and prior review evidence. Exact-SHA GitHub Actions
  run `31316352471` completed **successfully**: Python checks and frontend checks both passed,
  including pytest and storage-policy verification. A later privacy-only documentation commit
  advanced `main`; `a08247d…` remains its ancestor and retains its own terminal CI result.
