# Footballguys Phase A first-capture review — Codex v1

Date: 2026-08-17
Reviewer: Codex, independent binding lane
Scope: the one successful first capture, the disclosed pre-mutation refused invocation, the real archive and governed stores, the fire script, and the backup-manifest first-capture flip. The intake was not invoked by this review.

## Verdict

**NOT CLEAR / BLOCKED — one change-set contract failure.** The captured bytes and governed post-state reconcile, but the first-capture manifest flip did not amend the repository's explicit pre-capture contract expectation. The full Phase A + backup anti-rot run is **664 passed, 1 failed**.

### FBG-CAP-F1 — first-capture contract still pins `objects.required=false`

`app/config/backup_manifest.json` correctly moves `app/data/footballguys/objects` to the required list with `required: true`. However, `tests/contract/test_footballguys_phase_a_red.py` still defines:

```python
"app/data/footballguys/objects": ("directory", False),
```

The test's adjacent comment explicitly says this is the pre-capture epoch only and that the first-real-capture change set **must amend the expectation to `True` and land the manifest flip in the same reviewed act**. The real suite therefore fails:

```text
FAILED test_p0_option1_manifest_covers_every_durable_store[objects]
expected required=False; observed required=True
1 failed, 664 passed
```

This is not a reason to delete or re-fire the capture. The minimum remediation is contract-only: change that expectation to `True`, update the adjacent pre-capture comment to the post-capture state, then rerun the exact 665-test set and focused backup anti-rot checks. Route the delta back for review before commit.

## Checks that passed

### Source and fire script

- Landed production source is byte-exact to commit `e6b6775`: SHA-256 `a419930b3a0871d3bb2477475699ef2dcc76317125b544b0c2caac12ccd7790d` both at the commit and in the worktree.
- Fire script SHA-256: `45c70a12cb787ef308ea2edb06b57b3e4ee6a03d66192d3783d93362c482f5ad`.
- Script derives the repository root, requires exactly one archive argument, pins and refuses any archive hash other than `d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c`, uses the module's governed `ACTIVE_RETENTION_MODE`, and records pre/post store facts.
- Ruff passes; Python AST parse passes. The script was read only and not executed by Codex.

### Archive and retained object

- David's archive: 8,540,590 bytes, mtime 2026-08-09 00:02:50 ET, SHA-256 `d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c`.
- Objects store contains exactly one entry, named by that digest. It is byte-identical to the source archive, mode `0444`, link count 1, and `unzip -t` reports no compressed-data error.
- Objects/receipts/semantics runtime paths are gitignored. No paid bytes are staged.

### Receipt identity and roles

- Exactly one non-marker acquisition exists. Stored and independently recomputed receipt ID are both `77984aafe1052e8c7b9649a32ba16e9c7e2a3c1877cfa8cd05367451fe5d316c`; the persisted signature equals the canonical recomputation.
- Offering/source: `fbg-offering-2026-08-09-a` / `footballguys`; canonical retrieval time `2026-08-09T04:02:50Z`; retained archive digest/size match.
- Direct archive reads reproduce both role records:
  - `adp`: 30,388 bytes, SHA-256 `1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9`.
  - `identity_sidecar`: 260,688 bytes, SHA-256 `25be2d5a10f92b9787009edbb6144f516f53e4421afe5f39549b6eb6ca019c3f`.
- Independently recomputed content-vintage ID matches `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`.

### Stores, event, and readiness

- `PRAGMA quick_check` returns `ok` for receipts and semantics stores.
- Receipt stores `readiness=review_required`, `retention=retained`, `analysis_ready=0`, and event sequence 1 / event ID `9444a5ab1f2e45835089efaed79636b0` at `2026-08-17T20:18:50+00:00`.
- Central event row matches the receipt's event identity, store, subject, and instant. No extra event or failed-attempt row exists, consistent with the first invalid-clock invocation refusing before governed mutation.
- Semantics has zero assertions, attachments, evidence objects, and adjudications. Therefore `_horizon_is_effective()` is false and `review_required` is the correct designed state; no analysis-ready claim is supported.
- `observations.db` is absent, correct for active `full_offsite` retention. Staging directory is empty.
- Current main-file hashes match the reported post-state: receipts `54522831d448339933440b5d256a5a09c16b7bc520ee6d65828443e12379693f`; semantics `f555aef7ae91bc77dd6ec2b430228b839881ca90ae5d8eda51ef2a1263f14471`.

### Manifest and tests

- Manifest has exactly one objects row, now required and directory-kind. Receipts and semantics remain required; inactive observations remains optional.
- Backup anti-rot: 5 passed.
- Full Phase A plus anti-rot: 664 passed, 1 failed solely at the stale pre-capture expectation described above.
- Staged-scope state changed concurrently during the review: an early census saw the manifest/script not staged; the final census shows the manifest, fire script, prefire notice, and postfire report staged. This transient was remeasured and is not an additional final-state finding.

## Evidence boundary

The exact first invocation stdout and full pre-store hashes were not persisted as a separate output artifact; the staged report carries their prefixes and disclosure. Independent post-state evidence plus the operation-clock-before-mutation code path proves no governed receipt/object/semantic event preceded the successful event at sequence 1. This supports the stated mutation boundary but is not a byte-for-byte audit of the missing terminal output.

No commit, push, merge, deletion, cleanup, release, store write, archive fetch, intake invocation, or horizon adjudication was performed by this review.
