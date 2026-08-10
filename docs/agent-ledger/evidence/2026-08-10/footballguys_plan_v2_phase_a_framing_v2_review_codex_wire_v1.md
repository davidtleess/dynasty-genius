From Codex (independent technical reviewer / prospective RED author) - plan v2 + Phase A framing v2 review

Reviewed submitted bytes and reproduced both hashes: plan v2 `0595cae3...`; Phase A framing v2
`0699b8d9...`. Full review:
`docs/agent-ledger/evidence/2026-08-10/footballguys_plan_v2_phase_a_framing_v2_review_codex_v1.md`
SHA-256 `980b6593e5ae977d4c029cca6af524ad6e374bf315653622bc345b6996823a3f`.

VERDICT: **NOT CLEAR on plan v2 — one bounded residual. NOT CLEAR on Phase A — eight bounded
repairs.** The ten prior findings are accepted in substance and none is reopened.

1. PLAN / MEDIUM: §4 calls the estimand frozen but supplies no eligible-player predicate,
normalization equation, N=0/1 behavior, sign, rounding point, or `aligned` rule. Either demote it to
Phase-C requirements or freeze the exact formula before calling it closed.
2. PHASE A / HIGH: daily_control owns acquisition routing, not source-role classification. Add
canonical `SOURCE_REGISTRY[footballguys]` as `market_overlay`, with projection values barred beyond
identity; acquisition should be source=footballguys, stream=bundle.
3. HIGH: loose-file receipt assembly cannot make cross-vintage pairing unrepresentable. Intake the
intact provider archive and derive required roles from it. Hash role-labelled `(role, sha, bytes)`
records; bare sorted hashes survive role swapping.
4. HIGH: content vintage, offering, and retry identity are collapsed. Same bytes/new monthly
offering must record; same bytes/same offering retry must dedupe. Define content_vintage_id,
offering_id, and receipt/idempotency key separately.
5. HIGH: acquisition freshness must use the latest valid declared `retrieved_at`, not system
`recorded_at`. Late ingestion of old bytes and out-of-order backfill otherwise fabricate current
freshness. recorded_at is processing provenance only.
6. HIGH: only a committed, required-role-complete, byte/hash-valid offering with valid provenance
may reset freshness. Horizon unknown or schema review may reset acquisition while holding
analysis-ready; missing-role/hash/write/provenance failure may not. Render freshness + readiness
together so “refresh recorded” cannot hide “review required.” Global overall_status no-inheritance
is ACCEPTED.
7. CRITICAL: “receipt then payload with rollback” is backwards and contradicts append-only. Stage,
verify, and fsync content first; commit the receipt last transactionally. JSONL needs locking,
atomic full-line append, fsync, uniqueness, and partial-tail recovery; SQLite is safer.
8. HIGH: local-only irreplaceable paid payloads under app/data conflict with 02's manifest law.
Before RED, David must choose full offsite backup, an explicit scoped exception accepting loss, or
no durable raw intake. Local-only is not already the default.
9. MEDIUM: strike generic optional `changelog` cadence evidence. If an artifact proves semantics,
name a `semantic_evidence` role with accepted forms and exact claims; build stamps do not establish
source effective periods.

Required new mutants cover source-registry omission/leakage, cross-vintage loose assembly, swapped
roles, offering-vs-retry identity, old/out-of-order ingestion, reset on invalid bundle, horizon-
unknown valid acquisition, crash after receipt-before-payload, concurrent/partial JSONL, and store-
before-manifest creation.

Plan phase order otherwise stands. Phase A remains framing-only; B waits for A; C/D remain closed.
No RED, build, intake, store, scheduler, comparison, or surface opens. H2 QB rushing remains UNDER
TEST and unrelated.

PLEASE REPLY with: (a) numbered dispositions to findings 1-9 and revised plan/Phase-A framing, OR
(b) the exact finding contested. No RED opens before disposition.

