# A-C clock characterisation catalog review — Codex v7

**Date:** 2026-08-07 ET  
**Layer:** Layer 1 ingestion inventory  
**Reviewed artifact:** `docs/layer-1-data-inventory-catalog.md`  
**Reviewed SHA-256:** `41982b9a79d210d805951f81457802a5fa964c6929c6bc209789af3a2fcf3907`  
**Source evidence:** `ac_open_clocks_measurement_claude_v1.md`, independently CLEAR at
`1e33ba1d3a0927d5071d3e3513df7a1c65e373aeb6bc74ef7305d36af1f18ec4`  
**Verdict:** **NOT CLEAR — three findings.**

The four edited live cells correctly keep both source-publish fields `OPEN`. The N19 rates, grain,
off-season boundary, normalized/raw asymmetry, and N19-only-family ceiling match the cleared source
evidence. No checkbox moved. The remaining defects are reconciliation and claim-boundary defects.

## K1 — HIGH: the edit reinstates the source artifact's withdrawn F1 premise

At catalog lines 1213–1215, the step-3 explanation says:

> “unmeasurable” means the observation series does not exist and must be created.

That is the exact distinction the cleared evidence corrected. Three repeat observations **do** exist:
the 33s, 100s, and 396s pairs. What does not exist is an **adequate governed observation series from
which a recurring provider cadence can be inferred**. The N1–N8 canonical row at line 1193 already
states the corrected form, so the document contradicts itself within nineteen lines.

**Required repair:** replace the step-3 sentence with the cleared formulation: held observations are
insufficient; an adequate governed observation series must be created. Do not say observations or an
observation series are absent.

## K2 — HIGH: the canonical and summary surfaces were not reconciled

The change updates §6A and §6E but leaves live surfaces asserting the pre-characterisation state:

- line 723, canonical §4.4 N19 row: “the upstream change rhythm ... is unmeasured.” This is now
  false: a bounded **normalized observed-change rhythm** is measured, while the **source-publish
  cadence** remains unverified. §4.4 is the document's declared canonical classification table.
- lines 82–86, §1 checkbox C; line 371, §3.1 heading; lines 501–503 and 511–512, Table B-N status;
  and lines 573–576, the current-state summary still reduce both clocks to “unmeasured.” That wording
  erases the new load-bearing distinction: N1–N8 is unmeasurable from held evidence, while N19 has a
  measured change rhythm that does not satisfy its source-publish field.

This is exactly the risk Claude named: a skimmer can read the new §6E measurement while the canonical
table and progress surfaces continue to report the older state. Keeping `OPEN` is correct; reporting
why it is open must also be consistent.

**Required repair:** reconcile every live canonical/summary site, not historical disposition rows.
Use a compact common formulation: both source-publish fields remain `OPEN`; N1–N8 is unmeasurable
from held evidence pending an adequate series; N19 has a bounded normalized observed-change rhythm
that is not a source-publish cadence and does not cover N19-only families. Updating §4.4 retires its
prior whole-table pin and requires a fresh review of that changed cell, not a claim that the old pin
still covers it.

## K3 — MEDIUM: “only by David supplying repeat manual exports” is stronger than the evidence

The repository currently has no automated PlayerProfiler retrieval path: both legacy scripted routes
are retired at current `HEAD`. That supports **“with currently sanctioned capability, measurement
requires repeat manual subscriber exports from David.”** It does not establish that manual export is
the only possible future closure mechanism. The cleared evidence says automated acquisition is
blocked pending sanctioned-access, legal, and reliability proof; it does not say a future sanctioned
route is impossible.

**Required repair:** qualify “only” with the current capability/governance boundary, or state that
manual exports are the only currently sanctioned retrieval path. Preserve that no automated route is
present today and that no build is authorized by this catalog edit.

## Checks and unaffected facts

- Catalog and source-evidence hashes recomputed: **MATCH**.
- N19 measured rates and boundaries match the cleared evidence.
- Both source-publish fields remain explicitly `OPEN`; no §1 checkbox line changed.
- `git diff --check`: clean.
- `scripts/validate_governance.py`: PASS.
- The legacy PlayerProfiler retirement is now committed at `HEAD`; the two executable routes are
  absent. The parked wire paths remain out of this catalog diff.
- No catalog change is committed or pushed by this review.
- H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
