# TW15 QB-1 GREEN round-7 independent review — NOT CLEAR

Date: 2026-08-15 ET  
Reviewer: Codex  
Authority: David wake, `wake codex`, carried by Tower  
Layer: 3 validation/execution; Layers 1–2 remained frozen and outside scope.  
Study execution: **not run**. H2 QB rushing remains **UNDER TEST**.

## Pins reviewed

- `execution.py`: `e29edaf9c4a14f00615d440ccb9c7c25aa7d61eb3a2066de6dea67bfc8cfc905`
- `run_qb1_study.py`: `a7bfd8d0a2ef03b82bd78f1f123bad5852be678bbdc4921de06492f1be6d727d`
- correction contracts: `b4b408e7536ab8a0a88364d7feda2ceb5722d62e5828e3fb3b5b1a0e3082564f`
- request: `5ee8514b0827a2a375a878422454d1bb6cf6f050a1a0c2c96f545a36860d2313`
- independent probe: `b939e7814dd34f8bce9e10669c403c0f77df6117c9be9f0919c2971727949f55`

The scoped diff from the script-owned round-7 open snapshot was limited to the
three authorized files. No registration, frozen RED, model, provider, output,
or execution surface changed.

## Findings

### BLOCKER R7-G1 — the registered total status functions are still not enforced

The gate checks the below-floor direction and a few field-presence conditions
(`execution.py` lines 1171–1208), but does not reproduce or invoke the shipped
total functions already implemented in `status.py`.

The public runner publishes all of these as `ok`:

- model `supported` with a negative delta and negative zero-excluding CI, which
  the registered function requires to be `contradicted`;
- `unsupported_power` with 8/8 folds;
- a model comparison claiming 9 evaluable folds although only 8 exist;
- H5 `market_noninferior` with raw `p_ni=0.99`, caller-typed `ni_met=True`, and
  no `adjusted_p_ni` or one-sided lower bound.

Reproducer: independent probe lines 33–113.

Smallest correction: require the produced status evidence fields
(`adjusted_p`, and for H5 `adjusted_p_ni`, `one_sided_lower_95`, flags), enforce
registered fold totals, construct the canonical payload for
`evaluate_power_and_status`, and require exact equality of emitted
`support_status`/`ni_met`/registered flags. Below-floor unavailable H5 evidence
may keep the explicit special case already used by `contrast_status`.

### BLOCKER R7-G2 — H5 content is keyed but not mechanically reconciled

Three independent bypasses remain:

1. All 12 mandatory contrast×margin keys can exist with every leaf `{}`. The
   use of `leaf.get(...)` at lines 1618–1627 treats absent fields as honest
   nulls, but an empty object carries neither outputs nor an unavailable state.
2. Removing only c11 from one registered H5 fold with no exclusion flag passes;
   lines 1296–1304 check a flag only when all four H5 contrasts are absent.
3. The aggregate check is one-sided (`claimed > present`). A comparison can
   report `evaluable_folds=0` and `unsupported_power` while four non-null c11
   per-fold metric rows remain.

Reproducer: independent probe lines 116–174.

Smallest correction: close every margin leaf. A computed leaf carries all
produced fields; an unavailable leaf carries `state="unavailable"` plus all
three explicit null outputs. Apply named-exclusion handling per missing H5
contrast and require the comparison count to equal the mechanically derived
evaluable per-fold count, rather than merely not exceed metric-key presence.

### BLOCKER R7-G3 — F13 boundary rows remain typed but non-computational

The census arithmetic fixes work, but the boundary gate accepts a 1900 season
with 10,000 rushing yards and `qualifying_games=-10.5` as a ±1-yard boundary
case for a modern test fold. Lines 1493–1503 bind neither the trailing window,
count domain, boundary equation, nor gate/flip values.

Reproducer: independent probe lines 177–217.

Smallest correction: require a positive integer qualifying-game count; season
within the test fold's three trailing seasons; the registered
`abs(rushing_yards - 400) <= qualifying_games` relation; and recompute the
binary/±1 flip booleans from the boundary-season rows.

### BLOCKER R7-G4 — the case lane is not conditioned on its fold

`PRODUCED_LANE_NAMES` includes H5 globally despite its comment saying H5 is
produced only in registered H5 folds. The public runner accepts a reported H5
lane on a 2025 case, although H5 is registered only for 2021–2024 and the
composition cannot produce that lane there.

Reproducer: independent probe lines 220–236. Gate seam: `execution.py` lines
1348–1354.

Smallest correction: compute the allowed lane set from the case fold—H5 only
when `case.fold` is in `registration.h5.folds`.

## Fresh verification

- Submitted correction + frozen/ratchet/reinforcement bundle: **634 passed**,
  14 numerical-boundary warnings.
- Round-6 adversarial probe: **6/6 failed**, confirming the original examples
  are repaired.
- New public-runner probe: **9/9 passed**. Passing is the defect: each test
  asserts an invalid report still published with `run_status=ok`.
- Ruff on the three scoped files plus the probe: clean.
- Strict compile on the three scoped files plus the probe: clean.

Reproduce:

```bash
PYTHONPATH=. pytest -q \
  docs/agent-ledger/evidence/2026-08-15/qb1_green_round7_adversarial_probe_codex_v1.py
```

Expected at these pins: `9 passed`.

## Disposition

**NOT CLEAR.** No study execution, publication, push, or result claim is
authorized. Round 7 is the single David-authorized exception; these four
BLOCKERs return the run to the existing human gate after structured close. H2
QB rushing remains **UNDER TEST** with no result.
