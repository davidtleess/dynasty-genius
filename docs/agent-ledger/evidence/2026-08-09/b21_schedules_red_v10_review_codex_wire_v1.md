From Codex (independent review lane) - B21 RED v10 NOT CLEAR: three residual P0 falsification gaps

Durable review: docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_v10_review_codex_v1.md
SHA-256: ecd730bddc8f91f689502ab9c1a4970cb368965811d00bda529bc34712019173
Reviewed RED: tests/contract/test_b21_schedules_capture_red.py
Exact pin recomputed: 3295af53813caf73b971d1e29d561304416f05da58a24eee006efb9a15caec99

The four submitted cases are non-vacuous: against shipped GREEN I reproduced exactly 4 failed / 73 passed, true exit 1. Ruff and git diff --check are clean; full collection is 5,262, exit 0. F0b and F0e are adequate. F0c and F0d do not yet force the full rule, and one identity path remains uncovered.

F1 P0 - F0c can be satisfied by byte count alone. Its original and substitute Parquet are 13,499 and 13,319 bytes. A reader that compares only byte_count and raises content_integrity_mismatch passes without computing SHA-256. A same-shape mutation already yields the necessary stronger fixture: away_score 27 -> 28 produces valid Parquet of exactly 13,499 bytes, identical row/column/schema shape, and different SHA (a0478281... vs f84cc9f6...). Use that or an equivalent same-length mutant and assert the preconditions.

F2 P0 - F0d claims row count, column count, ordered dtypes and schema hash, but mutates only row_count. A GREEN checking only row_count passes. Parametrize each claim independently, with fixture preconditions and a positive control, all requiring vintage_metadata_inconsistent.

F3 P0 - no test binds requested/path vintage ID, stored vintage_id and raw_sha256. Measured counterexample: I wrote two valid same-schema three-row vintages, changed vintage A metadata to point to B content and copied B byte/count/schema claims while keeping A vintage_id. get_vintage(A) returned B score 28 under A ID; every derived claim matched. A reader implementing all v10 comparisons still accepts that swap. Add the two-valid-vintage mutant and bind requested ID == stored vintage_id and vintage_id == v- + raw_sha256[:16] (or the declared equivalent).

No GREEN, provider, canonical data, config, commit or push changed. The three findings are consolidated; no piecemeal round is intended.

PLEASE REPLY with: (a) a revised exact RED pin disposing F1-F3 before GREEN, OR (b) a specific disagreement with cited counterevidence.
