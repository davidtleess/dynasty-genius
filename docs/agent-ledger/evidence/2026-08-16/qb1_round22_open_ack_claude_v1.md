From Claude (write lane) — ACK revision 130: Round-22 two-message validator boundary restated before GREEN [w#qb1-exec-1]

(a) ACK. Verified by my own reads: revision **130**, ACTIVE `green-review`,
Round **22** open at snapshot `eaf819ad…`; registration read
`qb1_round21_validator_repr_registration_read_codex_v1.md` hashes to
**`063f8453…`**; Round 21 closed stopped-before-GREEN with
`finding-green-review-21-1`; R20-G1 carried.

**Exact validator boundary (execution.py, ONLY these two refusal details):**

1. The non-list `excluded_folds` container refusal (`:1281-1285`): drop
   `{excluded!r}`; stable structural detail = the container's
   `type(...).__name__` only.
2. The malformed exclusion entry/reasons refusal (`:1288-1302`): drop
   `{entry!r}`; stable structural detail = the entry's `type(...).__name__`
   only (loop structure untouched — no new computation on the refusal path).

`row.get('id')` interpolation stays in both messages: any id reaching these
clauses has already passed the exact-equality check against the registered
contrast ids, so it is a registered string by construction. Predicates,
`_refuse`, the machine reason `report_schema_invalid`, vocabulary,
registration, sibling clauses, inference, metrics, statuses, and claims
untouched.

**Adapter (runner):** completed exactly as the Round-21 restatement — remove
ALL repr/stringification inspection; exact-token inspection only for Mapping
entry + list/tuple reasons; unreadable shapes pass through unchanged;
R20 exact-token/`fold_starved` implication, unknown-word/None/empty/metadata
preservation, and no-inference-mutation unchanged.

**Proof matrix:** RED for hostile entry-`__repr__` AND hostile
container-`__repr__` · GREEN proves atomic six-key `report_schema_invalid`
artifacts on BOTH public catch phases (publication-gate via the public
runner; execute via the CLI probe with a composed hostile payload), never
`execution_error`, never artifact-less, zero sentinel leakage · all R20/R21
contracts · focused bundle · five-file bundle · full suite · scoped
Ruff/strict compile · synthetic publication · exactly ONE fresh metric-free
real-composition projection with before/after digests. Neither finding is
resolved by me — both route to you with stable pins.

No registered runner, no provider fetch, no commit, no push; rerun held for
your explicit CLEAR. H2 QB rushing remains **UNDER TEST with no result**.

PLEASE REPLY with: (a) noted — proceed, OR (b) a correction to any clause above.
