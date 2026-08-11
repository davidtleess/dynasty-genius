From Codex (independent reviewing lane) — review of `7e39763`: NOT CLEAR, five findings

Durable review:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_green_v8_review_codex_v1.md`
SHA-256 `a07abc018d288e77b7c0d1b709481e00d30f5396e8c3ed255f64bd5aae442d19`

PIN/SCOPE CLEAR: commit parent, exact three-file diff, +573/-73, RED `8a31fd94…`, and GREEN
`241d031d…` all reproduce. Current later HEAD is byte-equal on both reviewed paths.

GATES REPRODUCED: strict cold RED 340/340 exit 0; full tracked suite 5,573 passed / 12 skipped /
9 xfailed exit 0; Ruff clean; cold `-W error` compile clean.

FINDINGS:

1. CRITICAL — semantic table validation checks column sets, not load-bearing PK/UNIQUE
constraints. I rebuilt `semantic_attachments` with the exact columns/no PK and inserted two rows
under one evidence_id: unsupported provenance first, the original valid row second. Initialization
accepted 2 duplicates/0 indexes; dict projection collapsed the conflict and returned
`state=known`, `value=redraft`, `eligible_for_phase_c=True`. Physical row order decides. Require
constraint validation and duplicate detection before projection for assertions, attachments,
evidence objects, and adjudications.

2. HIGH — `event_sequence` accepts ANY unique index. Exact columns plus `UNIQUE(subject_id)` passed
initialization, and two rows with the same `event_id='dup'` committed. Inspect `PRAGMA index_info`
and require the exact, full, non-partial event_id key.

3. HIGH — event order is not closed. A valid receipt plus later failed intake was tampered/restored
so the acquisition claim and matching central `event_at` were the same offset-naive ISO value,
while the attempt remained offset-aware. Reconciliation returned `reconciled`; `read_model()`
raised bare `TypeError: can't compare offset-naive and offset-aware datetimes`. Canonicalize and
validate event instants and exact integer sequence on write and read; malformed order must be a
named fail-closed state.

4. HIGH — the byte-freeze claim is false outside the RED's already-WAL fixture. A DELETE-mode
populated bare semantics store started SHA `44a2ec2b…`, correctly refused
`store_migration_unreconcilable:semantics`, but ended SHA `5eedeef59…` in WAL mode because PRAGMA
WAL runs before validation. Prevalidate read-only or explicitly narrow and bind the allowed
pre-refusal mutation.

5. MEDIUM — adjudication writer totality stops at vocabulary fields. `key=[]` leaks bare
`sqlite3.ProgrammingError`; `effective_assertion_id=[]` leaks bare `TypeError`. Validate every
identity/key field as nonempty text before membership checks or SQLite calls, with unchanged-state
mutants.

DISPOSITION: NOT CLEAR. Finding 1 can convert conflicting semantic evidence into positive Phase-C
eligibility. Keep the pin unpushed and do not first-capture against it. I changed no RED/GREEN,
config, manifest, or runtime state. No provider, scheduler, capture, or Phase B/C/D opened. H2 QB
rushing remains UNDER TEST with no result and is unrelated.

PLEASE REPLY with dispositions/corrections. A next RED is not opened by this review alone.
