# Footballguys plan v2 + Phase A framing v2 — Codex review

Date: 2026-08-10

Reviewed artifacts:

- `docs/agent-ledger/evidence/2026-08-10/footballguys_horizon_divergence_plan_claude_v2.md`
  — submitted and reproduced SHA-256
  `0595cae32eef6a739e920b884ffe0ddf16f087a132e2b21f763aa5a9b46f8f45`.
- `docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v2.md`
  — submitted and reproduced SHA-256
  `0699b8d9341839c77ae98505ad303aba7a0bc78bdac82db5d6ed3257fd7c4134`.

## Verdict

**NOT CLEAR on plan v2: one bounded residual. NOT CLEAR on Phase A framing v2: eight bounded
repairs.** The ten prior findings are accepted in substance; none is reopened. The strategic phase
order, exact-field horizon gate, independent identity oracle, prospective cohort gates, neutral
labels, no-lookahead pairing direction, archive/series-break rule, and dedicated namespace are
sound.

Phase A may continue framing. No RED, build, intake, store, scheduler, comparison, or surface opens
from this review.

Layer: Layer 1 intake/reminder with a future Layer 5 consumer. The review checked the Layer 1 truth
source, Layer 2 identity dependency, canonical market-overlay registry, backup law, and the existing
login status-drawer composition.

## Plan v2 finding

### 1. Medium — §4 says the estimand is frozen, but the actual estimand is still unspecified

Section 4 freezes requirements around a future formula, not the formula itself. It does not name
the FantasyCalc eligible-player predicate, normalization equation, `N=0/1` behavior, delta
direction, rounding point, or the tolerance that produces `aligned`. Two implementations can obey
the prose and emit different deltas.

Either relabel §4 as requirements to be closed in Phase-C framing, or freeze the contract now. One
valid shape is:

- determine both native eligible player universes before intersection under explicit row-type
  predicates; never use `sleeper_id IS NOT NULL` as a proxy for “player” if unresolved players can
  lack that id;
- Footballguys native rank is its exposed ordinal after validating the complete nonblank ladder;
- FantasyCalc native player rank is descending raw price with equal prices assigned midrank;
- for `N >= 2`, `standing = 1 - (rank - 1) / (N - 1)`; `N < 2` is unavailable;
- `delta = footballguys_standing - fantasycalc_standing`, so positive means
  `footballguys_higher`;
- classify before display rounding and define `aligned` exactly (zero or a preregistered neutral
  band).

The exact formula may legitimately wait for Phase-C framing because no C RED is open, but the plan
cannot call it frozen until that closure is explicit.

## Phase A findings

### 2. High — the proposed registry home omits the canonical source-role registry

`daily_control.py` owns acquisition routing, not analytical role classification. The canonical
`SOURCE_REGISTRY` has no Footballguys entry today, while its leakage gates derive market-overlay
sources from that registry. Registering only `footballguys.bundle` in daily control would leave the
new paid source outside the market-data-out-of-model-inputs wall.

Phase A must add one canonical `footballguys` source definition with role `market_overlay`, a
fail-closed field boundary, provenance requirements, and an explicit prohibition on projection
values crossing the identity-only sidecar boundary. The acquisition manifest should reference
that registry source. In the manual-feed model, use `source=footballguys`, `stream=bundle`; the
dotted `footballguys.bundle` may be the composed stable read-model id, not an orphan source id.

This is also the correct place to prove the PlayerProfiler/PFF contracts remain byte-equal and
that Footballguys cannot appear in Engine A/B feature materialization under any alias.

### 3. High — “cross-vintage pairing has no representation” is false for loose-file assembly

Putting two selected files into one receipt only records the operator's assertion that they belong
together. It cannot detect an August `adp.csv` paired with a July `projections.csv`. The current
provider delivery is a single Draft Dominator archive, which supplies a stronger boundary.

For v1, intake the intact provider archive as the offering payload and derive the required member
roles from that one archive read-only. Record the parent archive hash plus exact member names,
role-labelled member hashes, and byte counts. Refuse duplicate/case-colliding member roles,
traversal members, missing roles, and members whose schemas do not match their declared roles. If a
future provider workflow supplies loose files, it needs separate framing and an honest
`bundle_cohesion=operator_declared` state; it cannot inherit “cross-vintage unrepresentable.”

The current bundle-id recipe also hashes a sorted list of hashes without role labels. Swapping the
two role assignments preserves that identity. Hash a canonical sequence of `(role, sha256,
bytes)` records, not bare hashes.

### 4. High — payload identity, offering identity, and replay identity are still collapsed

The framing says identical bytes re-dropped are a new offering observation, then says same bytes
produce the same receipt id and no duplicate. Both cannot be true with only `bundle_id`.

Use three explicit identities:

- `content_vintage_id`: canonical role-labelled content identity;
- `offering_id`: one declared act of David supplying that content, independent of its bytes;
- `receipt_id` or idempotency key: makes retrying the same offering a no-op.

Same content + same offering id is an idempotent replay. Same content + a new offering id is a new
monthly observation of an unchanged content vintage. A new offering must be explicit; a rerun
cannot be guessed from elapsed time or a new system timestamp.

### 5. High — freshness uses ingestion time instead of the acquisition event it claims to describe

The notice is about David's monthly refresh action, but §5 clocks it from system `recorded_at`.
That recreates the exact defect the existing PFF intake explicitly prevents: indexing a 29-day-old
download today would display a current refresh for another 29 days. Ingesting historical receipts
out of order can also make an older acquisition become “latest.”

Drive acquisition freshness from the latest **valid declared `retrieved_at`** offering, normalized
to America/New_York for the calendar-day rule. Keep `recorded_at` as processing provenance and
report processing lag; never use it as acquisition freshness. Naive, malformed, or future
`retrieved_at` makes that offering freshness-unverifiable and does not advance the clock. Selecting
“latest” must be by validated acquisition instant, not append order or ingestion time.

Add controls for a late import of old bytes, two valid offerings ingested out of chronological
order, future system clock, and day-30 behavior across DST/month/year boundaries.

### 6. High — only a committed, byte-valid acquisition may reset freshness; `failed` is too broad

The proposed “quarantined/failed still resets” rule mixes a real acquisition requiring analytical
review with a failure that may not establish the required bundle at all.

Recommended closed predicate:

- a committed offering with all required bytes present and hash-verified, valid source/bundle
  cohesion, and valid `retrieved_at` advances acquisition freshness;
- horizon unknown or schema/identity review may leave intake `review_required` and
  `latest_analysis_ready` unchanged while still advancing acquisition freshness;
- missing required roles, invalid provenance, hash mismatch, write failure, or absent bytes is
  `failed` and cannot advance freshness;
- `latest_analysis_ready` advances only to the newest eligible ready offering by acquisition time,
  never merely the last ingested record.

The no-inheritance ruling for global `overall_status` is **accepted**: a manual paid-source
obligation is not an app-health failure. Its own read model must still expose freshness and
readiness independently. The surface composition must show both axes together so “refresh
recorded” cannot conceal “data review required”; the three freshness-only copy strings are not yet
a complete state-matrix oracle.

### 7. Critical — the write order is backwards for an append-only receipt

“Receipt-then-payload with rollback” can guarantee that no receipt cites absent bytes only by
deleting or rewriting a receipt after a payload failure. That contradicts the append-only contract
and creates a crash window in which a durable receipt points to missing data.

Use prepare-then-commit:

1. validate the complete archive and semantic manifest without writes;
2. create content-addressed raw objects exclusively, verify bytes/hash, and fsync;
3. commit the offering receipt last in one ledger transaction with uniqueness constraints;
4. if receipt commit fails, retain/report unreferenced content objects as recoverable orphans;
   never publish a receipt pointing to absent bytes.

A JSONL append needs an explicit lock, full-line atomicity, fsync, duplicate-key enforcement, and
partial-tail recovery. A small SQLite ledger, like the existing PFF intake, is the safer default
for transactionality and three-part identity. Either choice needs crash-point mutants after every
durable step.

### 8. High — the local-only raw default conflicts with the current manifest-coverage law

The raw paid archive is not regenerable from the repo plus public sources; re-downloading from a
mutable paid product does not reproduce an old vintage. A new irreplaceable capture store under
`app/data/` therefore falls under `02`'s backup-manifest coverage law. Saying Phase A proceeds with
raw local-only while only receipts enter the manifest is not a neutral default; it is an exception
to that law.

Before RED, obtain David's explicit choice among:

- full raw payload backup/offsite replication;
- a named exception/amendment allowing this exact local-only licensed store despite the coverage
  law, with the accepted loss model;
- no durable raw intake yet.

Do not add raw payloads to the manifest or run a backup without his word. Do not claim option (a)
is already the operating default. The manifest entry must exist before the first protected receipt
or raw store is created; “lands together with the first receipt” is too late if runtime data can be
written before the config commit.

### 9. Medium — strike the generic `changelog` role unless it has a specific contract

“Optional, cadence evidence” is not a stable role. A changelog may describe software builds rather
than the effective period of `adp_sleeper-sf`, recreating the build-stamp/source-as-of confusion.
The two required Phase-A roles are sufficient for intake. If a provider artifact directly supports
the semantic contract, name it `semantic_evidence`, define its accepted forms and hash/retention
rules, and state exactly which fields it may establish. Otherwise omit it from v1.

## Required mutant/oracle additions

The sixteen proposed controls are useful but do not yet catch these defects. Add one broken
implementation for each:

1. Footballguys absent from `SOURCE_REGISTRY`, or misregistered as model input.
2. Projection-value column leaks beyond the identity-only boundary under an alias.
3. July sidecar + August ADP files manually assembled into one receipt.
4. Role assignments swapped while bare sorted hashes leave `bundle_id` unchanged.
5. Same content/same offering duplicated; same content/new offering incorrectly deduped.
6. Twenty-nine-day-old acquisition ingested today reports current from `recorded_at`.
7. Older offering ingested after a newer one becomes the freshness or analysis-ready head.
8. Missing-role/hash-failed offering advances freshness.
9. Horizon-unknown but byte-valid offering incorrectly fails to advance acquisition freshness.
10. Crash after receipt append but before payload persistence leaves a live dangling receipt.
11. Partial JSONL line or concurrent append corrupts the receipt ledger.
12. Raw store exists before its governing manifest entry/exception.

## Scope ruling

- Plan v2: one residual repair; findings 1–3 and 5–10 from the prior round are otherwise closed.
- Phase A: eight repairs above; the global-overall-status no-inheritance decision is accepted.
- Phase B: remains waiting for A's frozen interface and independent oracle.
- Phase C/D: remain closed.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
