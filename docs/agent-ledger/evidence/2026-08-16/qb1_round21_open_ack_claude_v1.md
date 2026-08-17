From Claude (write lane) — ACK revision 129: Round-21 hostile-repr correction boundary restated before RED [w#qb1-exec-1]

(a) ACK. Verified by my own reads: revision **129**, ACTIVE `green-review`,
Round **21** open (01:46:50Z), exact two-file scope, snapshot `607b377a…`;
opening pins match my working tree exactly (runner `ec19067c…`, contracts
`9661c536…`); R20-G1 carried unresolved; David's fresh word recorded.

**Restated boundary:** remove ALL repr/stringification inspection from
`_canonical_excluded_folds`. The exact token `empty_common_pool` is inspected
ONLY when the entry is a Mapping AND its `reasons` is a list/tuple —
structural inspection, value-equality on elements, nothing else. Unreadable
shapes pass through UNCHANGED to the registered validator. The Round-20
exact-token/co-occurring-`fold_starved` law, unknown-word preservation,
None/empty preservation, metadata/order preservation, and
no-inference-mutation all stand unchanged.

**Proof matrix I will run:** RED-first hostile-`__repr__` regression
(adapter-level AND end-to-end through the public runner) · e2e named-failure
requirement (`report_schema_invalid`, never `execution_error`) · unrelated
metadata carrying the token triggers NO canonicalization · all original R20
contracts (the two repr-era unreadable-shape rows re-specified to
pass-through semantics, disclosed) · focused correction bundle · five-file
bundle · full suite · scoped Ruff + strict compile · synthetic terminal
publication · exactly ONE fresh metric-free real-composition projection
outside the runner with mandatory before/after digests.

**One measurement routed, not resolved (per your "resolve nothing
yourself"):** whether the unchanged validator's own eager `{entry!r}`
interpolation (`execution.py:1298-1302`) converts a hostile-`__repr__` entry
into a non-named failure on either publication path. I will measure it
exactly as the RED observes it and route the fact with the evidence —
`execution.py` stays untouched regardless.

No registered runner, no provider fetch, no commit, no push; the one fresh
registered rerun stays held for your explicit CLEAR after re-review. H2 QB
rushing remains **UNDER TEST with no result**.

PLEASE REPLY with: (a) noted — proceed, OR (b) a correction to any clause above.
