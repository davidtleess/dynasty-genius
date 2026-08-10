# Footballguys Phase A repaired GREEN review — Codex v1

**Date:** 2026-08-10  
**Reviewed commit:** `8bf15189372ba29f83a62b09af3ece2e77813547`  
**Verdict:** **NOT CLEAR — 2 Critical, 4 High, 3 Medium**  
**Layer:** Layer 1 acquisition, persistence, provenance, and freshness/readiness state  

## Post-commit divergence audit

The landing itself matches the declared five-file act:

- parent `f2dc48a41fae8ba75d1e18758ca1bdb38e0d1652`;
- 5 files, `+942/-79`, exactly the ledger, repaired-wire evidence, RED-v3 evidence, production
  module, and RED-v3 test file;
- RED v3 SHA-256 reproduced exactly as
  `3b5383380c2bdbe0d9f0d85da10704bed721f7033f0a0f2a67b8c6331eeaa565`;
- GREEN SHA-256 reproduced exactly as
  `c5d87c6283ce8a9513362e1d98cd7dc7f72e79d42678122525ac2f24e45fc4aa`;
- the two working-tree files are byte-equal to the committed pin;
- `git diff --check 8bf1518^ 8bf1518` is clean.

There is no undeclared file-scope divergence. The blocker is behavioral divergence from the
cleared framing and from the implementing lane's repaired-GREEN claims.

## Findings

### 1. Critical — the next real capture crashes against the runtime databases already created by the prior GREEN

The prior production bootstrap left `app/data/footballguys/receipts.db` and `semantics.db` with
the old acquisition schema. A read-only schema inspection confirms `receipts.db` lacks `source`
and `role_records`, and neither database has the new tables required by this commit.

`initialize_database()` uses `CREATE TABLE IF NOT EXISTS` without validating or migrating an
existing schema (`footballguys_intake.py:1163-1216`). A temp-root fixture built with the exact old
schema then exercised the committed intake. It published one canonical ZIP and failed afterward:

`OperationalError: table acquisitions has no column named source`

The receipt store still contained only the bootstrap row, leaving the paid object orphaned. The
first-capture path therefore is not compatible with the disclosed runtime state on this machine.
The store schema must be validated/migrated before publication, with the actual old-to-new shape
as a required positive control and a restart/convergence assertion for any failure.

### 2. Critical — semantic evidence is neither retained nor verified, but it can open the horizon gate

Framing v25 requires a retained, hash-verified evidence attachment with retrieval provenance and
allowed-claim fields, an append-only assertion lifecycle, and explicit adjudication records
(`framing_claude_v25.md:348-357,410-429`). The implementation stores only a caller-supplied
provenance string, a digest, and a byte count; it stores no evidence bytes or governed object
reference and has no adjudication table (`footballguys_intake.py:1174-1189,1777-1881`). On load,
any nonempty stored digest plus `retention='retained'` is relabeled `retained_verified`; no bytes
are rehashed. `INSERT OR REPLACE` also lets a reused evidence identity replace the attachment.

Independent probes showed both of these states returned `state=known`,
`eligible_for_phase_c=True`:

- provenance changed to `untrusted-blog`;
- persisted `evidence_sha256` overwritten with 64 zeroes.

This recreates the pilot's core assumed-semantic failure at the evidence gate. The attachment
must have governed retained bytes (or a content-addressed governed object), descriptor-bound
rehashing on every use, validated provenance/claim allowlists, append-only identity semantics,
and durable adjudication records supplied to the reducer.

### 3. High — later valid semantic evidence cannot promote a retained receipt

Readiness is computed once during receipt insertion and persisted (`footballguys_intake.py:1713-
1745`). The read path never combines acquisitions with the current semantic reducer state. A
probe ingested a valid retained archive first (`review_required`), then wrote the effective
provider-authentic horizon assertion. A fresh driver still returned the identical
`awaiting data review` state with `latest_analysis_ready_id=None`.

Framing v25 explicitly allows later evidence versions without changing acquisition identity or
freshness. Readiness therefore must be derived on load from the acquisition plus effective
semantic state, or represented by a separately governed/versioned evaluation record; it cannot
be a permanently frozen acquisition column.

### 4. High — durable failed attempts disappear whenever a valid clock exists

The attempt table stores only `(status, reason)` and loads those fields without an acquisition
instant or ordering relation (`footballguys_intake.py:1747-1773`). The state evaluator can only
append a failure suffix when it knows the failure is the newer attempt. RED s24 covers failure
with no prior clock only.

After a valid retained intake, an independently recorded later malformed intake survived a fresh
load in the attempts table, but the rendered copy omitted
`newest attempted drop failed intake`. That contradicts framing rows 5/7 and the two-stage overlay
contract (`framing_claude_v25.md:1014-1016,1039-1059`). Persist attempt identity/time and test
newer/older/equal attempt ordering over every base state.

### 5. High — integrity/conflict rendering drops the held analysis-ready receipt and bypasses stage 2

For integrity and offering-conflict specials, the evaluator emits the AR clause and AR identity
only when `ar_row is not clock_row` (`footballguys_intake.py:517-551`). When the held prior clock
is itself the held analysis-ready receipt—the ordinary row-19c case—it incorrectly returns
`latest_analysis_ready_id=None` and omits `analysis uses the <date> drop`.

A two-receipt probe (older valid AR, newer object corrupted) reproduced exactly that loss. These
specials also return before the newer-attempt overlay is composed. Framing rows 18c/19c and the
stage-2 rule require the held AR identity/date and any newer failed/invalid suffix to survive.
The production evaluator needs literal coverage for those combinations; a helper-only renderer
is not sufficient.

### 6. High — the claimed real sidecar schema guard still validates only column count

`validate_role_schema()` accepts any identity sidecar whose first column is `id` and which has at
least three columns (`footballguys_intake.py:343-360`). The independent payload
`id,foo,bar\nGibbJa00,one,two\n` was accepted. It has no name or position field and cannot support
the identity correctness guard that justified this sidecar.

Pin the actual required identity columns (including accepted aliases if the real product needs
them), parse CSV rather than splitting the header naively, and add a full-real-shape or
byte-faithful acceptance control plus named-column mutants. The current RED's malformed fixtures
test too few columns, not wrong identity columns.

### 7. Medium — published objects do not receive the framed read-only mode

Framing v25 requires published objects to be set `0444` while correctly refusing to rely on mode
as immutability (`framing_claude_v25.md:631-636`). The publish path creates staging at `0600` and
links it without a mode transition. A successful probe measured the canonical object at `0600`.
Keep descriptor rehashing as the real integrity boundary, but enforce and test the promised
defense-in-depth mode through the bound descriptor.

### 8. Medium — RED v3 is not clean under `-W error`

The exact claimed command exits **1**, despite the 201 test bodies passing. Pytest teardown raises
an `ExceptionGroup` containing four `ResourceWarning: unclosed database` warnings. The leaks are
the four `with sqlite3.connect(...)` uses at test lines 1310, 1328, 1363, and 1364; SQLite's
connection context manager commits/rolls back but does not close the connection. Use
`contextlib.closing` (including nested connections) and preserve the strict command as a gate.

### 9. Medium — the production provenance header still points to the superseded original RED

The module header says it is GREEN for pin `1130f2bc…` (`footballguys_intake.py:3`) even though
the landed contract is RED v3 `3b538338…`. This is non-behavioral but load-bearing provenance in a
cycle where exact pins govern review. Update it in the repair act and add a pin/header assertion
or remove the mutable pin from the module header.

## Checks run

- commit/parent/name-status/numstat/diff and exact SHA-256 audit;
- `git diff --check 8bf1518^ 8bf1518` — pass;
- exact RED command: 201 bodies passed, process exit 1 from four unclosed SQLite connections;
- all tracked tests (excluding only the untracked cadence RED by construction): **5,434 passed,
  12 skipped, 9 xfailed**, matching the landing census;
- `.venv/bin/ruff check src app tests/contract/test_footballguys_phase_a_red.py` — pass;
- read-only inspection of the disclosed production DB schemas;
- independent temp-root probes for old-schema intake, later semantic evidence, untrusted semantic
  provenance, tampered evidence digest, valid-clock-plus-failed-attempt overlay, held-AR integrity
  fallback, wrong sidecar columns, and canonical object mode.

No provider contact, first capture, scheduler, push, or Phase B/C/D work was performed. No
production application row or provider object was written. `8bf1518` must remain unpushed and no
first capture should run against it. H2 QB rushing remains **UNDER TEST** with no result and is
unrelated.
