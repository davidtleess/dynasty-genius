# CFBD QB ingest repair — failing RED contract (Codex v1)

## Scope and authority

Layer 1 ingest and Layer 2 publication-contract tests only. This RED encodes the G1-G6 repair
boundary independently reproduced by Claude and Codex, plus G7 from the provider's supported
endpoint parameters. No production code, API data call, source artifact, active model input, or
consumer wiring changed.

Test artifact: `tests/contract/test_cfbd_qb_ingest_red.py`.

## Contract encoded

| Gate | Failing behavior now | Required behavior |
| --- | --- | --- |
| G1 response identity | the first QB in a mixed response is selected | resolve one player; bind stats/PPA/WEPA by provider ID |
| G2 request semantics | timeout becomes an empty result | named request failure distinct from valid no-data |
| G3 collision | two distinct QBs may publish one complete same-season vector | refuse publication pending review |
| G4 scale and plausibility | source `PCT=0.652` becomes `0.00652`; `0.00594` publishes | preserve fractional scale and reject implausible qualifying values |
| G5 coverage and retention | 0% sack-rate and a 100%→25% YPA drop publish | refuse fully dark declared families and material regression |
| G6 raw fidelity | normalized `qb_stats_*` dicts and scalar `tpa_*` files count as raw | persist unmodified responses before normalization; reject derivatives as raw |
| G7 endpoint contract | unsupported `playerName` is sent to three endpoints | send supported filters only and filter response rows by resolved ID |

G3 is deliberately a fail-closed audit alarm, not a claim that equal values mathematically prove
misattribution. G4 corrects one sentence in the Claude evidence: `[0,1]` alone does not reject
`0.00594`. The deterministic current transform and stored output show the provider returned
fractional PCT values that were divided by 100 again. The RED uses `0.652 → 0.652` as the scale
contract and separately requires a qualifying-QB plausibility publication gate.

## Provider-contract basis

Current public CFBD Swagger metadata was read without invoking a data endpoint. It confirms:

- `/player/search`: `searchTerm`, `year`, `team`, `position`;
- `/stats/player/season`: year/conference/team/week/season-type/category, with no player-name or
  player-ID filter, and player identity in each response row;
- `/ppa/players/season`: supports `playerId`;
- `/wepa/players/passing`: year/team/conference/position, with athlete identity in each row.

The installed CFBD OpenAPI 5.13.2 client independently exposes the same signatures.

## RED census

Command:

```text
.venv/bin/python3.14 -m pytest -q tests/contract/test_cfbd_qb_ingest_red.py
```

Result: **11 failed**, each at its intended missing contract boundary:

1. G1 selects YPA 4.1 from the wrong first player instead of 8.9 for the resolved player.
2. G4 returns completion `0.00401` from the wrong row and double scaling, not `0.652`.
3. G7 sends unsupported `playerName` to `/stats/player/season` and never resolves identity.
4. G2 swallows `httpx.TimeoutException` and does not raise a request failure.
5. G6 writes no unmodified player-stat response before normalized QB caching.
6. G3 publishes two identical complete QB vectors.
7. G4 publishes `completion_pct=0.00594`.
8. G5 publishes a 0%-coverage sack-rate family.
9. G6 accepts a normalized `qb_stats_*` dict as raw.
10. G6 accepts a scalar `tpa_*` derivative as raw.
11. G5 publishes a material YPA coverage regression from 100% to 25%.

Baseline command:

```text
.venv/bin/python3.14 -m pytest -q tests/test_cfbd_qb_adapter.py tests/contract/test_cfbd_foundation_refresh.py
```

Result: **29 passed, 2 skipped**. The new RED did not disturb the pre-existing suite.

Static checks: `uvx ruff check tests/contract/test_cfbd_qb_ingest_red.py` and `git diff --check`
pass after import ordering. No live integration test ran.

## GREEN boundary

Claude owns production implementation. The GREEN may choose internal structure freely as long as
the observable G1-G7 behaviors pass. The RED intentionally does not require a named raw-snapshot
function parameter or a specific response-envelope schema.

Consumer promotion/copy, another paid refresh, and re-running the past bakeoff remain out of scope.
A later blast-radius audit established that the defective fields were dropped before the Phase 20
fit and no model artifact changed, so this RED addresses foundation correctness and future-use risk,
not a contaminated promoted model. QB rushing remains **UNDER TEST** and is not used as evidence or
premise here.

