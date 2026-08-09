# B21 schedules GREEN v4 — behavioural CLEAR

Date: 2026-08-09
Layer: 1 — source capture and retained provenance
Reviewer: Codex
Verdict: **CLEAR**

## Cleared pins

- `tests/contract/test_b21_schedules_capture_red.py` v9, 1,326 lines:
  `4d924d6ce9bace5d5e4816c46eca43ac69385284efe9743807bbcf755439f79a`
- `src/dynasty_genius/sources/schedules_capture.py` v4, 985 lines:
  `2f5425f3264bc09ec36ae197ae61d0a1b05941be54353c3cfae832d0c7a5c10f`
- `scripts/run_schedules_capture.py` v2, 96 lines:
  `9e5dcc954b0f492d5e6e2079ede29dc36466d23340c5054139d19b893e765c6b`
- `app/config/backup_manifest.json`:
  `31839b15391b5547dac1d57671992cd19cadfb6207d922663269fb8439c0b486`

All pins were recomputed locally and match the implementation packet.

## Independent checks

- Canonical invocation `.venv/bin/python3.14 -m pytest -q
  tests/contract/test_b21_schedules_capture_red.py`: **72 passed in 2.77s**.
- Four repository backup suites (`test_dgx02_backup_coverage_red.py`,
  `test_horizon0_backup_red.py`, `test_backup_manifest_anti_rot_red.py`, and
  `test_backup_directory_red.py`): **55 passed in 1.15s**.
- Ruff on the RED, module, and CLI: **clean**.
- Independently inspected the completed full-suite output: **5,030 passed, 15 failed, 12 skipped,
  9 xfailed**; the 15 named failures are exclusively the separate untracked governed-cadence RED.
- Re-ran the exact transport-error counterexample outside pytest. URL userinfo and all synthetic
  query/fragment secrets were absent from both the raised exception and every retained file; the
  diagnostic retained the sanitized provider host/path without a doubled error code.

The v9 contracts were shown non-vacuous by the implementing lane: against the prior module pin the
two widened userinfo cases failed **2 / 70**, exactly S9c and D6, before the v4 repair.

## Independent isolated live capture

One provider request was made through the real CLI into a temporary store, never the governed
repository root.

- Observed at: `2026-08-09T07:33:22-04:00`
- Provider retrieval time: `2026-08-09T07:33:30.801851-04:00`
- Requested source:
  `https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet`
- Sanitized delivery path:
  `https://release-assets.githubusercontent.com/github-production-release-asset/452908115/20471cd8-193e-41a5-aac5-06b3ab16148a`
- Raw byte count: **517,546**
- Raw SHA-256:
  `eeea1f47644cc498676be92b5ac0fb853fd4bce238348f0436aa786c1440d5c1`
- Check ID: `c-20260809T0733220400-eeea1f47644c`
- Vintage ID: `v-eeea1f47644cc498`
- Independent Parquet shape: **7,548 rows x 46 ordered columns**
- 2026 rows: **272**
- Schema SHA-256 independently recomputed from compact JSON ordered `[column, dtype]` pairs:
  `9bbd6413bc4c498d190db8502a9b6dd7dd326c2feffa6b7208e1ef99d6b4c6a5`
- Stored ordered dtypes exactly matched the independent pairs.
- Duplicate `game_id`: **none**.
- `gameday`: zero null and zero empty values.
- `gametime`: **259 provider nulls**, zero empty strings, retained truthfully.
- Finality capability: `unverified`; no terminal-status claim was added.

The content object and check raw were the same 517,546-byte object with the same SHA-256 (and the
same inode). Marker, index, vintage, and success audit were all present. A text scan of every
retained non-Parquet file found no `X-Amz-*`, token/JWT, synthetic signature, fragment-token, or
userinfo marker. `delivered_from` carried scheme + sanctioned host + path only.

Local `ScheduleStore.replay(check_id)` returned the same **7,548 rows** and raw hash. Counts before
and after replay stayed `(1 vintage, 1 successful check, 0 failed checks)`, proving replay minted no
check or duplicate vintage.

The isolated live store and both synthetic counterexample stores were deleted after measurement.
They were temporary review artifacts; no governed capture was removed or changed.

## Verdict and handoff

**Behavioural CLEAR** on the four pins above. No further finding remains from this review round.

The next operation is the first canonical capture into
`app/data/sources/nflverse_schedules`, followed by evidence-based catalog update, exact-path staging,
commit, push, and terminal CI. The backup-manifest entry must land in the same commit as the
populated required store, never before it.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
