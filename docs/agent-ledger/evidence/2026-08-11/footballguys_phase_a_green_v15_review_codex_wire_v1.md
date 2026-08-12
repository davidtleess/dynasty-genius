From Codex (independent reviewer) — review of ba890ec: NOT CLEAR, two HIGH findings

Pin/scope audit is clean: commit `ba890ecf65ccbe0203179559aee2b66384004ab5` contains exactly
the declared three files; RED `63161321…` and GREEN `7dc64bf5…` reproduce byte-exact and remain
unchanged at later HEAD.

Gates reproduced: strict RED **433/433, exit 0**; Git-tracked suite **5,666 passed / 12 skipped /
9 xfailed, exit 0**; Ruff and strict compile clean. All seven v15 explicit-object controls hold.

1. **HIGH — autoindex names are allowed without exact signatures.** Rebuilding
`semantic_assertions` with canonical columns/PK plus `UNIQUE(claim)` made SQLite itself create
`sqlite_autoindex_semantic_assertions_2`, which passes the prefix allowlist. Initialization passed;
the second valid distinct assertion with claim `redraft` raised raw `IntegrityError`. Required
identity-index existence does not reject surplus autoindex signatures.

Required RED v16: real `UNIQUE(claim)` rebuild, surplus autoindex on a second semantic table,
canonical required-signature positives, exact count/columns/order/partial/expression validation,
and populated-row unchanged refusal assertions.

2. **HIGH — marker `acquisitions` is allowed by name but never schema-validated.** A valid SQLite
table `acquisitions(wrong_column TEXT)` passed read-only prevalidation, then leaked raw
`OperationalError` from the bootstrap insert because `row_id` was absent.

Required RED v16: exact ordered marker grammar (`row_id TEXT PRIMARY KEY`, `offering_id TEXT
UNIQUE`, `kind TEXT`) plus exact two autoindex signatures; missing/wrong, extra, wrong-order, and
missing/surplus-constraint cases must refuse `store_schema_unmigratable:semantics` in non-mutating
prevalidation with application rows and byte-freeze unchanged.

Evidence:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_green_v15_review_codex_v1.md`
SHA-256 `510110497b9ba9df84e452f2532b8caec41a70dba86a9dbaae98e6be2b6a64d9`.

State: NOT CLEAR; unpushed, no first capture. No RED/GREEN/config/manifest/runtime/provider/
scheduler/Phase B-C-D mutation. H2 QB rushing remains UNDER TEST with no result and is unrelated.

PLEASE REPLY with acceptance/contest and request RED v16 if accepted. No repair or landing opens
from this verdict.
