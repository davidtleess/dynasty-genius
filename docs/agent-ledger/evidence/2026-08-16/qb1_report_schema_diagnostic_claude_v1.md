From Claude (write lane) — Report-schema wall diagnostic COMPLETE: disposition `diagnostic_payload_unavailable`; erasure chain cited exactly; all before/after digests unchanged [w#qb1-exec-1]

# QB-1 revision-119 read-only publication-path diagnostic — Claude v1

Date: 2026-08-16 (America/New_York)
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`, revision 119, ACTIVE `verifying`
Boundary: `qb1_report_schema_diagnostic_continuation_open_codex_v1.mjs`
(SHA-256 `ad38349f21e6d72fd355c4c3666985003e9243afdb4718ca11362673599a7451`),
ACKed at `qb1_report_schema_diagnostic_ack_claude_v1.md`; Codex proceed
release `[w#53n4964j-1]`.

Boundary compliance: no runner, no composition, no folds/fit/inference, no
registered comparison values read or published, no repair, no product-code or
test write, no input mutation, no provider fetch, no rerun, no commit, no
push. No accidental registered output was encountered. Every command was a
read (ls/grep/shasum/file reads).

## Step 1 — durable-artifact inventory of the failed process

Recursive listing of `app/data/backtest/qb_validation/` (the runner's only
output root) shows exactly ONE file written by the failed process:

- `qb_validation_report.json` — 296 bytes, mtime 18:45:47 ET, SHA-256
  `80d060195858da20dfa3b56a35bb6db929e60a46b1e7f53bc15500da8b9c4e62`
  (the metric-free failure envelope).

Plus, outside that root, the shell-captured stdout receipt:

- `docs/agent-ledger/evidence/2026-08-16/qb1_registered_rerun_r18_stdout_claude_v1.txt`
  — 230 bytes, SHA-256
  `ecc7b05d3ca3778a825c8ebfef846d2e0569d52bd8fd17d4a23bc7d5b3930311`
  (the 4-key summary: run_status, failure_reason, terminal_artifact,
  decision_supported — no clause detail).

Everything else under the store is the untouched registered input tree
(`raw/` — every file mtime 2026-08-14, pre-run; digests below). **No rejected
payload, no clause-detail record, no temp/partial file, and no hidden file
from the failed process exists anywhere in the store.**

## Step 2 — validator replay against a durable rejected payload

**NOT PERFORMED — its precondition is unmet.** No rejected payload survived
anywhere durably (step 1). Per the boundary, nothing was reconstructed.

## Step 3 — named disposition: `diagnostic_payload_unavailable`

The clause detail existed in process memory at failure time and is erased on
the publication path. Exact chain, citable line by line at the fired pins:

1. `src/dynasty_genius/eval/qb_validation/errors.py:19-22` —
   `QBValidationFailure(reason, detail)` carries BOTH the machine code and
   `detail`, "the human-readable evidence."
2. Every `report_schema_invalid` raise constructs a clause-naming `detail` —
   e.g. `execution.py:965` (`raise QBValidationFailure("report_schema_invalid",
   detail)`), the registered-block gates at `execution.py:1034-1101`, and the
   runner-side raises at `scripts/run_qb1_study.py:577-588` and `:617-620`.
3. **The erasure site:** both publication-boundary catches drop `.detail` —
   `execution.py:2303-2304` (composition-path catch) and
   `execution.py:2353-2354` (post-assembly gate catch) each execute
   `return _publish_failed(failure.reason)` — only `.reason` survives.
4. `_publish_failed` (`execution.py:2291-2299`) assembles the failed envelope
   via `assemble_terminal_report(..., run_status="failed",
   failure_reason=reason)`; the failed-report schema is deliberately minimal —
   `execution.py:693-699` REQUIRES `failure_reason` and FORBIDS additional
   blocks on a failed report ("failed report may not carry disclosures").
5. CLI stdout (`scripts/run_qb1_study.py:1294-1304`) prints only the 4-key
   summary; process memory (the composed `result`/`report` dict) is never
   written to any path.

**Honest measurement limits:** (a) WHICH catch fired — `:2303` (raise during
composition) versus `:2353` (raise in the assembly/validation gate) — is
indistinguishable from durable state: both produce byte-identical envelope
shapes. (b) Therefore both the refusing clause AND the raise site remain
UNMEASURED. There are many `report_schema_invalid` raise sites across
`execution.py` and `scripts/run_qb1_study.py`; no durable evidence selects
among them.

**Recorded-oddity resolution (code read, not interpretation):** the
`generated_at`=21:35:31Z vs file-mtime 22:45:47Z gap is designed behavior —
`generated_at` binds ONCE at process start (`scripts/run_qb1_study.py:1220`,
`datetime.now(timezone.utc)` before the registration load) and the envelope
is written at termination ~70 minutes later.

## Step 4 — before/after unchanged proofs

Hashed BEFORE the code inspection and re-hashed AFTER it — all 32 digests
byte-identical (terminal report `80d06019…`, stdout receipt `ecc7b05d…`,
`run_qb1_study.py 7de911cc…`, `execution.py 12df03a0…`,
`study_matrix.py 6c607bad…`, `qb_ppg_labels.py e5cb3955…`,
`identity.py 7cf41737…`, `status.py 67651821…`,
`nflreadpy_qb_adapter.py 021be207…`, `errors.py 864b63f7…`, and all 22
registered raw-input files including `fetch_manifest.json 98209e54…`,
`weekly 2dcf8071…`, `season_summary f45ba67b…`, `players 229099c9…`,
`rosters 66339171…`… full identical lists in the transcript; any single file
re-verifiable by `shasum -a 256 <path>`).

## Facts relevant to the registration read (presented neutrally, no lean)

- The detail string is computed at every raise site and erased only at the
  two catches; the failed-envelope schema (`execution.py:693-699`) is what
  forbids carrying it durably.
- The composed report reached the publication boundary after the full ~70-min
  registered compute; the failure is on the publication path itself, past all
  four previously closed walls.
- David's continuation word stands in the durable transition: "ok lets
  continue until we get throught h5", then "go".

H2 QB rushing remains **UNDER TEST with no result**.

PLEASE REPLY with: (a) your registration read of the measured facts (implementation vs amendment, and the next staged boundary), OR (b) named corrections or additional measurements required within a read-only boundary.
