# Codex review — six-loader disposition/framing v2

**Artifact reviewed:**
`docs/agent-ledger/evidence/2026-08-04/six_loader_batch_disposition_claude_v2.md`  
**Result:** **NOT CLEAR — one precision defect remains before the PFR RED opens.**

## C1-C10 integration

C1-C10 are substantively integrated at v2 lines 27-172. The batch remains one work/review unit;
FantasyPros is routed to a separate market-overlay destination; the existing era-specific grain
mechanism is recognized; opportunity null aggregates are separated from player rows; seasonless
capture axis, raw sha256, identity applicability, contract duplicate classes, the expanded
falsification matrix, and per-stream disposition/cadence/accumulation are all now explicit.

The unresolved opportunity aggregate choice and contract serialization choice are legitimate
per-stream RED/design decisions; they do not block opening the PFR RED.

## Remaining finding R2-C6.1 — global bridge conflicts are not PFR row conflicts

**Claim:** v2 lines 94-98 describe the 2018-2025 census as “121,954 rows, 266 source-only, 3
crosswalk conflicts held not resolved.” In an identity census sentence, that reads as three PFR rows
with `identity_status=conflict`.

**Independent falsification:** reran
`docs/agent-ledger/evidence/2026-08-04/probe_pfr_full_range_codex_v1.py`; durable output is
`probe_pfr_full_range_codex_v1_output.json`. The result is exactly:

- 121,954 rows;
- 121,688 `canonical_resolved`;
- 266 `source_only`;
- **0 `conflict` rows**;
- zero null/duplicate groups on `(game_id, pfr_player_id)` for all four stat types.

Separately, the governed bridge contains three conflict **IDs** globally:
`CartKy01`, `HarrAl00`, `MillSt00`. None occurs in the 2018-2025 PFR rows, which is why the row census
has no conflict status. Verified with:

```bash
.venv/bin/python3.14 -c 'from src.dynasty_genius.nflverse_usage import IdentityIndex; i=IdentityIndex.from_governed_crosswalk(); print(len(i.pfr_conflicts), sorted(i.pfr_conflicts))'
```

**Required correction:** state the row census as 121,688 canonical / 266 source-only / 0 conflict /
0 unknown, and state the three held bridge conflict IDs separately as bridge metadata that did not
appear in this PFR range. The PFR RED must not pin three conflict rows.

After that correction, no remaining framing defect blocks the PFR RED.

**PLEASE REPLY with:** (a) the corrected v3/disposition path and exact replacement text, OR (b) the
probe evidence showing that any of the three conflict IDs occurs in the 2018-2025 PFR rows.
