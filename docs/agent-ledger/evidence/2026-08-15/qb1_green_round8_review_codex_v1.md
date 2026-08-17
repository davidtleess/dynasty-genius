# TW15 QB-1 GREEN round-8 independent review — NOT CLEAR

Date: 2026-08-15 ET  
Reviewer: Codex  
Authority: David-authorized bounded round 8  
Layer: 3 validation/execution; Layers 1–2 remained frozen and outside scope.  
Study execution: **not run**. H2 QB rushing remains **UNDER TEST**.

## Pins reviewed

- `execution.py`: `913225f529a0c63a30b4ee6b025c3d1ac408a5d6107be15b8a65dc80d83e9f37`
- `run_qb1_study.py`: `ef7a8244d5b141eaa7280f37b269531089f5eeeb6649b230b09fcbe50bde86eb`
- correction contracts: `513ed1bd255c9c62368bcb68f8cacfbfdc3284aa5c9df3a0c8a36affd46b9b58`
- request: `38b49bc9858d1b8e4276990c505a2265172d4ecd0794aee22b515e2e14dec7dd`
- independent probe: `750f8213945cccf71c969ce7417ed4f7577ee5e7a709c988418a4b57a1bb254b`

The script-owned round-8 snapshot diff is limited to the three authorized
files: execution +309/-58, runner +22/-15, contracts +248/-5. Unchanged
status/init/RED/ratchet/reinforcement/wire pins matched the request.

## Findings

### BLOCKER R8-G1 — the below-floor H5 exception is not total

`execution.py:1291-1335` invokes the shipped function only when all six H5
numerics are present. If any one is absent below the floor, the exception checks
only `support_status` and `flags`; it does not require the numerics to be wholly
unavailable and does not check `ni_met`.

The public runner therefore publishes an H5 row with two evaluable folds,
`p_ni=0.01`, `pooled_delta=0.01`, missing `adjusted_p_ni` and one-sided bound,
and caller-typed `ni_met=True` as `unsupported_power`. This is neither the
shipped total function's output nor the explicitly allowed *honestly
unavailable* special case.

Reproducer: independent probe `test_h5_below_floor_partial_evidence_can_claim_ni_met`.

Smallest correction: make the direct below-floor branch an exact produced
schema: all unavailable inference numerics null, `ni_met=False`, registered
status, and exactly the registered below-floor flag. Otherwise invoke the total
function when complete or refuse partial evidence.

### BLOCKER R8-G2 — H5 still counts metric keys, not evaluable fold content

`execution.py:1425-1468` increments `h5_presence` whenever a contrast key is in
`metrics_with_CIs`. The metric validator explicitly permits `paired_delta=None`,
null Spearmans, and `common_pool_n=0` (`:1388-1404`), so key presence is not the
mechanical admission predicate.

The public runner publishes c11 as `evaluable_folds=4` after one of its four
fold entries is changed to `paired_delta=None`, both Spearmans null, and
`common_pool_n=0`. This leaves only three mechanically evaluable entries but
passes because four keys remain. It is the exact distinction the round-7
smallest correction named: equality to the mechanically derived evaluable
per-fold count, not metric-key presence.

Reproducer: independent probe `test_h5_key_presence_counts_a_non_evaluable_fold`.

Smallest correction: derive each contrast's evaluable seasons from its emitted
metric content using the producer's admission invariant (`paired_delta` present,
with the corresponding finite Spearmans and positive/evaluable pool), require
that set to equal the comparison's contributing/evaluable claim, and reconcile
the excluded-season set as its registered complement. Do not add exclusions to
a key-presence count.

### BLOCKER R8-G3 — F13 recomputation is one-sided and aggregate counts are trusted

`execution.py:1714-1727` validates a flip only inside
`if case_entry[flip_field]`: an impossible asserted `True` is rejected, but an
impossible asserted `False` is trusted. The surrounding fold validation checks
only that aggregate flip counts do not exceed the pool; it never requires them
to equal the sum of case-row booleans.

Two public-runner payloads publish `ok`:

1. 401 yards over five games mechanically flips at the +1-yard/game threshold
   (405), but the case reports `flips_at_plus_1_ypg=False` and aggregate zero.
2. The same case honestly reports `True`, while the fold aggregate remains zero.

Reproducers: independent probe `test_f13_false_negative_flip_publishes` and
`test_f13_aggregate_flip_count_disagrees_with_cases`.

Smallest correction: compute each case's expected minus/plus flip booleans and
require exact equality in both directions; then require both per-fold aggregate
flip counts to equal the sums across boundary cases.

## Checks without findings

- R7-G4 case-fold lane conditioning is enforced: H5 is removed from the allowed
  set outside the registered H5 folds.
- Margin leaves now use closed computed/unavailable schemas and the prior shell
  mutants reject.
- The original nine round-7 reproducers now all reject through the public runner.
- No registration, input, model, provider, output artifact, or frozen boundary
  changed.

## Fresh verification

- Submitted correction + frozen/program/inference/reinforcement bundle:
  **646 passed**, 14 known numerical warnings, exit 0.
- Round-7 adversarial probe: **9 failed**, confirming all original examples are
  repaired.
- New public-runner probe: **4 passed**. Passing is the defect: every test
  asserts an invalid semantic payload still published `run_status=ok`.
- Ruff on all three scoped files plus the probe: clean.
- Strict compile on all three scoped files plus the probe: clean.
- Full-suite rerun was not repeated after the independent public-boundary
  blockers reproduced; the submitted exact-pin tally remains author evidence,
  not a basis for this verdict.

Reproduce:

```bash
PYTHONPATH=. .venv/bin/python3.14 -m pytest -q \
  docs/agent-ledger/evidence/2026-08-15/qb1_green_round8_adversarial_probe_codex_v1.py
```

Expected at these pins: `4 passed`.

## Disposition

**NOT CLEAR.** No study execution, publication, push, or result claim. Per
David's round-8 boundary, no further remediation round is inferred; the run
re-parks for David after these findings are recorded and round 8 closes. H2 QB
rushing remains **UNDER TEST** with no result.
