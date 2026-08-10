# Footballguys Phase A GREEN review — Codex v1

Date: 2026-08-10
Reviewer: Codex, RED owner / independent GREEN reviewer
Commit reviewed: `f9b57d304b06bf860a90300982957eb60329ccca`
Verdict: **NOT CLEAR — 3 Critical, 4 High**

## Post-commit divergence audit

The commit identity and submitted pins reproduce:

- commit: `f9b57d304b06bf860a90300982957eb60329ccca`;
- parent: `ce3b61bb6d9423726857b15518bf65e205084d07`;
- amended RED: `35e48037034983234fd05f66cc22876ece713bfe99e7db89b841e417bba600aa`;
- GREEN module: `09e2955ed0071e6fcc2dfeb33ac6d2f6539d13da9182db2a221c84b29033f0ee`.

`git diff-tree` reports exactly the declared 12 files, 3,345 insertions and zero deletions:
the amended RED, GREEN module, `.gitignore`, backup manifest, source registry, daily-control row,
the two pin-table/test edits, ledger, and three disclosed evidence/wire files. No undeclared
production file is present. Unrelated dirty worktree files pre-existed and were not used as review
evidence.

One non-semantic hygiene mismatch exists inside the declared scope: `git diff --check
f9b57d3^ f9b57d3` reports six Markdown hard-break trailing-space lines in the Codex amendment
record. This is not a disposition driver.

## Findings

### 1. Critical — a short staging write produces a receipt for bytes that were never retained

At `footballguys_intake.py:1402`, the implementation calls `os.write` once and ignores its return
count. At lines 1419-1421 it then validates and hashes the original `archive_bytes` argument, not
the staged descriptor. The fresh publication check at lines 1499-1508 verifies only type, link
count, and inode identity; it never verifies staged size/hash against the signed facts.

Probe: replace `os.write` with a legal short-writing implementation. Intake returned `ready`,
published 207 of 415 bytes under the 415-byte payload's hash-derived pathname, committed a receipt,
and rendered `current`. The retained object's SHA differed from the pathname/receipt SHA.

This violates the one-snapshot boundary and makes a receipt citing absent bytes representable.
Required repair: stream with a complete-write loop, derive every fact by reading the staged
descriptor, and perform the full size/hash invariant on the fresh object before the receipt
transaction. Add a short-write mutant that fails the current GREEN.

### 2. Critical — the canonical object directory entry is never durably published

The publish creates `objects/<sha>.zip` at line 1491, but line 1498 fsyncs `dir_fd`, which is the
**staging** directory descriptor opened earlier. The objects-directory descriptor is never opened
or fsynced. A successful receipt can therefore outlive a canonical directory entry across a system
crash, despite the framing requiring parent-directory fsync before receipt commit.

Descriptor-trace probe: successful intake fsynced the staging directory and never fsynced the
objects directory (`staging=True`, `objects=False`).

Required repair: open and bind both directories, assert their `st_dev` equality, fsync the objects
parent after publish/removal/quarantine, and make the crash oracle identify the descriptor target
rather than merely the trace label.

### 3. Critical — downstream loads ignore receipt identity, object integrity, and global offering conflicts

`_effective_acquisitions` (lines 1630-1653) hashes the stored signature blob, sets a temporary
`row["integrity"] = "invalid"` on mismatch, then discards that result and emits the row with
`valid=True`. It does not reconstruct the signature from persisted signed fields; the schema does
not persist `source` or role records, so reconstruction is impossible. It does not rehash the
receipt-bound object. It groups by `row_id`, not `(source, offering_id)`, so restored cross-store
conflicts are not reduced to `offering_identity_conflict`.

Three independent probes all rendered healthy state:

- overwrite the retained object with `b"corrupt"` → `current`, same clock and AR;
- alter stored signature, vintage and retrieval instant → `current`, forged 1-day clock and AR;
- insert a different valid signature for the same offering in observations → `current` metadata-
  only clock, rather than the required global conflict.

Required repair: persist every signed field, reconstruct and compare each identity per load,
descriptor-rehash each receipt object, reduce invalid evidence as a named integrity state, then
group the union by `(source, offering_id)` before clock candidacy. Add end-to-end persisted-state
mutants; pure state-function specials do not cover this boundary.

### 4. High — arbitrary role payloads are accepted as schema-valid and analysis-ready

The production path has no CSV/schema validator. `fault_at="schema_failure"` at lines 1423-1424
injects a result instead of testing real bytes. A ZIP whose two exact role members contain only
`not-the-adp-schema` and `not-the-sidecar-schema` returned `ready`, was retained, and became the
latest analysis-ready acquisition.

Required repair: validate the pinned ADP and identity-sidecar schemas from staged member bytes,
including role/schema mismatch, before publication. Replace the fault hook's shadow test with a
malformed real-member fixture that fails current code.

### 5. High — the semantic assertion store/lifecycle promised by the RED is absent

The RED's public seam explicitly promises `write_semantic_assertion(record)` at line 21, but
`ContractDriver` exposes no such method. Initializing `semantics.db` creates only the acquisition
table. There are no attachment, assertion, or adjudication persistence tables and the pure
`reduce_semantic_assertions` function is disconnected from every write/read path.

This also makes the current readiness assignment unsafe: `_commit_acquisition` marks every receipt
`ready` and `analysis_ready=1` (lines 1617-1622), although the standing source state is
`horizon=unknown` and the framing requires freshness to advance while analysis readiness holds.

Required repair: implement the separately versioned semantic/evidence/adjudication store and wire
its effective state into readiness without changing acquisition identity. Until provider-authentic
horizon evidence is effective, retained receipts must be `review_required`, not AR. Add durable
writer/load tests; pure reducer examples cannot satisfy the promised seam.

### 6. High — real failed/invalid attempts can never reach the notice state machine

Every intake refusal returns an `IntakeResult`, but no durable attempt record is written.
`read_model` hard-codes `attempts=[]` at line 1660; `_attempts_dir` is unused. A malformed ZIP with
no prior clock returned `failed/archive_malformed`, yet the read model remained byte-equivalent to
`No Footballguys refresh recorded` rather than disclosing the failed attempt.

Required repair: define and persist the attempt ledger/state needed by the accepted overlay rows,
without advancing acquisition freshness, and feed it to the two-stage evaluator. Add a real failed
intake followed by a fresh process/read-model load; direct calls to `evaluate_refresh_state` with
synthetic attempts pass broken persistence code.

### 7. High — the pre-capture optional manifest row does not enforce the first-capture landing law

The amended evidence requires the RED and manifest to flip to `required=true` before the first
provider archive is written. `_require_coverage` (lines 1041-1043) treats required and optional
rows identically. With objects optional and receipts/semantics required — the landed production
state — a temp-root intake returned `ready`, retained a canonical ZIP, and committed a receipt.

The current no-provider/no-CLI state limits immediate exposure, but the rule is prose-only: an
early call can create the first irreplaceable archive while DGX-02 still tolerates an empty/missing
objects payload.

Required repair: active option-1 raw publication must require the objects row to be
`kind=directory, required=true`; the pre-capture bootstrap may accept optional only while no raw
write is attempted. Add the real intake mutant, then flip that expectation and the manifest in the
first-capture change set as already ruled.

## Checks run

- exact commit/parent, name-status, numstat and both artifact hashes;
- `pytest` over the Phase A RED, layer-1 daily-control contract and source-registry tests:
  **301 passed**;
- Ruff over all changed Python/test surfaces: **clean**;
- `git diff --check`: six non-blocking Markdown trailing-space findings described above;
- targeted independent `/private/tmp` probe covering short write, object corruption, persisted-row
  tamper, cross-store conflict, optional first capture, descriptor-target fsync, schema-less ZIP,
  semantic-store schema, and failed-attempt visibility.

The targeted probes use temporary roots only. No provider bytes, production runtime store,
scheduler, Phase B/C/D surface, commit, or push was created by this review.

## Disposition

**NOT CLEAR.** The landed commit must not be pushed or used for a first capture. The 185-test RED
also needs amendment because several controls test injected outcomes or pure reducers rather than
the production boundary they name. GREEN repair and RED hardening should land together in the next
reviewed act; the existing commit remains useful provenance, not a cleared implementation.

H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
