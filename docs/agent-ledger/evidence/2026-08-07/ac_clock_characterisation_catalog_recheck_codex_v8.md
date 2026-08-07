# A-C clock characterisation catalog recheck — Codex v8

**Date:** 2026-08-07 ET  
**Layer:** Layer 1 ingestion inventory  
**Reviewed artifact:** `docs/layer-1-data-inventory-catalog.md`  
**Reviewed SHA-256:** `35855a62bfe3d3a3c17778e731db10dba3979972c285375d7736761a11e523dd`  
**Prior review:** `ac_clock_characterisation_catalog_review_codex_v7.md`, SHA-256
`57a3e51c9578f2514237264efaba9e18ab3bb42c6e9dea989d14b7c0e83ff03f`  
**Verdict:** **NOT CLEAR — K1–K3 are repaired; three residual findings L1–L3 remain.**

## K1–K3 disposition verification

- **K1 repaired:** the step-3 explanation now says the held observations are insufficient and an
  adequate governed series must be created. It explicitly preserves the three 33s/100s/396s repeat
  observations.
- **K2 repaired at the six named surfaces:** both source-publish fields remain `OPEN`; N1–N8 is
  unmeasurable from held evidence; N19's bounded normalized observed-change rhythm is not a
  source-publish cadence and excludes N19-only families. The §4.4 N19 cell now carries the correct
  distinction and declares its old pin retired.
- **K3 repaired:** the manual-export statement is qualified to today's sanctioned capability and
  explicitly does not claim a future sanctioned route is impossible.

## L1 — HIGH: §1 still makes installation a condition of inventory closure

Catalog lines 83–87 say two gates keep checkbox C open: (1) the clocks are “proposals, not installed
jobs”; and (2) the two open source-publish fields.

The first is not a gate under the catalog's own closure rule. §6A line 865 says each field may be
independently verified **or explicitly `N/A` / `not scheduled` with evidence**, and its authority
column says **pinning ≠ scheduling**. Earlier M3 also separated inventory closure from remediation.
Requiring installed jobs here makes A-C completion depend on scheduler enablement that the agreed
sequence places after inventory closure.

**Required repair:** keep “planning targets are not installed jobs” as a boundary, not a closure
gate. Checkbox C is open because the two source-publish fields remain unresolved (and any separate
independent-review requirement the matrix actually states), not because proposed jobs are not yet
installed.

## L2 — HIGH: a live paragraph still asserts a retired whole-table CLEAR

Catalog line 502 says `§4.4 (whole-table CLEAR at this pin)`. The same fresh edit changes §4.4's N19
cell, and lines 724 and 1449–1450 correctly say that edit retires the earlier whole-table CLEAR pin
and requires fresh review.

Both cannot stand. Until this review clears the changed N19 cell, the current §4.4 bytes are not
whole-table CLEAR.

**Required repair:** restate line 502 as “§4.4 was whole-table CLEAR at the prior pin; the N19 cell
was subsequently edited and awaits the fresh review named in §6F.6,” or equivalent. Do not call the
current bytes CLEAR before the verdict exists.

## L3 — MEDIUM: two live canonical/classification rows still say a retired shadow route exists

Current `HEAD` retires both executable legacy PlayerProfiler HTTP routes. The repaired §6E row and
K3 disposition correctly state that no automated retrieval path exists in the repo today. But:

- §4.4 N1–N8 row, line 717: “a shadow HTTP POST route exists”; and
- §6C PlayerProfiler row, line 974: “A shadow HTTP route exists.”

Those are stale current-state claims, not historical disposition text. They contradict the K3 repair
and can mislead the automation classification rationale.

**Required repair:** say the two unsanctioned shadow routes were retired on 2026-08-07; the class
remains `blocked` because no sanctioned automated acquisition exists and any future automated route
still requires sanctioned-access/legal/reliability proof. Preserve history in §6F/ledger, not as a
present-tense route.

## Checks and boundaries

- Fresh catalog and prior-review hashes recomputed: **MATCH**.
- K1–K3 factual repairs verified against the independently cleared source evidence.
- N19 §4.4 changed-cell content is factually correct; the issue is the still-live clearance claim.
- No checkbox line changed; both clocks remain `OPEN`.
- `git diff --check`: clean. `scripts/validate_governance.py`: PASS.
- Parked wire paths remain outside this edit.
- No commit or push is cleared. H2 QB rushing remains a registered hypothesis **UNDER TEST** with no
  result.
