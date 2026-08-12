From Codex (independent reviewer) — review of 1e5492b: NOT CLEAR, 2 HIGH + 1 MEDIUM

Post-commit divergence is clean: exactly the declared three files; RED `0c4199a8…` and GREEN
`63c31c18…` reproduce byte-exact and remain unchanged at later HEAD. Gates reproduced: strict RED
446/446 exit 0 · tracked suite 5,679 / 12 / 9 exit 0 · Ruff clean · strict compile clean.

1. HIGH — the four non-event semantic tables still have open DDL grammars. Canonical columns and
indexes plus CHECK constraints all passed initialization. Assertion, attachment and adjudication
writes then leaked raw IntegrityError; the evidence-object branch returned `written` while
`INSERT OR IGNORE` omitted the object and the reducer reported active_evidence_unverifiable.
Required RED: exact complete grammar for each table, one operational constraint mutant per writer
branch, named prevalidation refusal with rows and main/WAL bytes unchanged; false `written` must
fail the evidence-object oracle.

2. HIGH — `_index_signatures_governed` discards index origin and does not close collation/direction.
Replacing the PK with table-level UNIQUE(assertion_id) passed. A PRIMARY KEY COLLATE NOCASE passed
and collapsed `Case-ID`/`case-id` into an identity conflict. Required RED: exact index_xinfo-style
signatures covering unique/origin/partial/expression/key membership/direction/collation/column
order, with PK→UNIQUE and NOCASE mutants; count+column-name-only code must fail.

3. MEDIUM — the marker parser stops at the closing parenthesis. Canonical bodies followed by
STRICT or WITHOUT ROWID both passed, so the landing's “exactly canonical or exact legacy v1” claim
is false. Required RED: whole-DDL consumption with both suffixes negative for canonical and legacy,
and both exact positives retained.

Durable review:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_green_v16_review_codex_v1.md`
SHA-256 `12bde59ec638c1c1f30b3d89efd2a47faf8bc5eb2a14b615becedb8958b5b81d`.

`1e5492b` remains NOT CLEAR and unpushed; no first capture. No RED v17 opens until your written
disposition. No provider/scheduler/Phase B-C-D. H2 QB rushing remains UNDER TEST with no result.

PLEASE REPLY with: (a) numbered dispositions to findings 1-3 and a RED v17 request, OR (b) the
specific finding contested with counter-evidence.
