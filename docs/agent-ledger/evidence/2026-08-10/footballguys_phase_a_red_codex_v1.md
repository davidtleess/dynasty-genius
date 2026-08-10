# Footballguys Phase A RED — Codex v1

Date: 2026-08-10  
Author: Codex, independent RED lane  
Layer: Layer 1 intake plus acquisition-freshness read model  
Authority: David selected framing-v25 retention option `1` (full offsite raw backup).  
Framing pin:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v25.md`  
Framing SHA-256: `f44b5ab008c02206cbcba26dacab6efdfd85fcdc279282207c4ae5e99d7301ff`

## RED artifact

Path: `tests/contract/test_footballguys_phase_a_red.py`  
SHA-256: `1130f2bcde14ef8cc4d4bbba7e8eff8fbf71734a5388116053388b7d8d1bea7f`  
Measured size: 1,322 lines / 55,406 bytes  
Production module named by the contract:
`src.dynasty_genius.sources.footballguys_intake` (deliberately absent at RED).

The RED introduces no production code, provider bytes, runtime namespace, database, scheduler,
network call, GREEN behavior, Phase B/C/D behavior, commit, or push.

## Contract shape

The suite binds one injected production composition seam, `build_contract_driver(...)`, plus pure
archive, identity, time, semantic-reducer, state-reducer, and read-model functions. Expected values
come from test-owned literals and hand-built byte preimages, never production output.

| Section | Cases | Passing anchors | Expected RED failures | Boundary |
| :-- | --: | --: | --: | :-- |
| P0 | 23 | 4 | 19 | framing pin; source registry; daily-control id; narrow ignore; option-1 manifest |
| A | 22 | 0 | 22 | exact nested roles; full 259-entry profile; ZIP hazards; all five caps; decoys |
| I | 24 | 6 | 18 | six known-answer hashes; grammar; acquisition identity; sidecar cordon; semantic reducer |
| S | 51 | 0 | 51 | private namespace/lock; branch traces; crashes; descriptor cleanup; sweep; WAL; transitions |
| C | 55 | 0 | 55 | New York calendar clock; all literal rows; ties; overlays; impossibilities; persistence |
| R | 10 | 0 | 10 | id-addressed composition; global isolation; banned copy; option-1 active mode |
| **Total** | **185** | **10** | **175** | no skip, xfail, or early collection abort |

Option 1 is the only active write branch. The option-3 observation store remains a declared
optional `kind="sqlite"` backup entry and its tests remain only for retention transitions,
cross-store composition, counterpart lookup, and failure cleanup. It is not an active intake mode.

## Independent anchors

Ten tests pass before GREEN:

- the framing bytes match the pinned SHA;
- the narrow future ignore rule does not hide three commit-intended evidence/config/test paths;
- the two positive byte vectors reproduce exactly:
  - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
  - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
- N1–N4 reproduce exactly:
  - `86d18b7e0949cbedb64141d8ca3a934f6a2181516c0835019f98ee341c6b8605`
  - `fb6b16f63985abf2efd72b1d311217bcb8cc151c9dc58f57dfb7b8bbc6f1d86f`
  - `d5785e03a72b74e968b5afe8d47f06d3e84e4c93c519ab47f7334f9668bac5c8`
  - `d87163c387735c4d9a10774d130b0b60d02886d11700f18ccc9637a04a81caf0`

These passing cases prove the RED's external anchors are live; they do not claim GREEN behavior.

## Failing-run census

Command:

```text
.venv/bin/python3.14 -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py
```

Result:

```text
175 failed, 10 passed in 4.60s
```

The 175 failures partition cleanly:

- **19 repository-bound gates:** missing `SOURCE_REGISTRY["footballguys"]`; missing stable
  `daily_control` row; 13 runtime paths still commit-eligible; four durable stores absent from the
  backup manifest.
- **156 production-bound contracts:** the named module is absent, so each archive/identity/store/
  clock/read-model case fails through `_mod()` with no skip. This is the intended pre-GREEN state.

Supporting checks:

```text
uvx ruff check tests/contract/test_footballguys_phase_a_red.py
All checks passed!

.venv/bin/python3.14 -m py_compile tests/contract/test_footballguys_phase_a_red.py
exit 0
```

## What GREEN must not infer

- A passing hash vector is not evidence the provider horizon is known.
- A retained archive is not analysis-ready until the separately governed identity/readiness gates
  pass.
- Option 1 does not activate the observation write branch.
- The status pill counts freshness states only; readiness never changes global health.
- The projection sidecar is identity evidence only; none of its projection values is a market or
  model signal.
- This RED does not open Phase B, the horizon-divergence comparison, the UI component, a scheduler,
  provider contact, commit, or push.

## Standing gates

Phase A GREEN implementation may now be proposed against this RED, but landing and execution stay
separate reviewed acts. The narrow `.gitignore` rule and manifest coverage must precede the first
runtime write exactly as the failing P0 tests require. Phase B awaits Phase A's frozen bundle
interface plus an independent identity oracle; Phase C remains closed on horizon/cohort/estimand;
Phase D remains closed on C plus David. H2 QB rushing remains a registered hypothesis **UNDER
TEST** with no result and is unrelated.
