# Phase A framing v25 — Codex round-25 CLEAR

Date: 2026-08-10 12:40 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v25.md`  
Submitted and reproduced SHA-256:
`f44b5ab008c02206cbcba26dacab6efdfd85fcdc279282207c4ae5e99d7301ff`  
Measured size: 1,138 lines / 95,084 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **CLEAR — no findings.** This clears the Phase A framing review only. It opens no RED,
build, intake, store, scheduler, provider contact, comparison, or surface. David's §8 retention
choice remains a separate hard gate.

## Checks run

1. Diffed v24 to v25. The substantive delta is confined to the v25 title/round-24 disposition,
   replacement of the phantom changed-outcome oracle, and final reply request.
2. Recomputed the artifact SHA and size above; verified the v25 title and live round-24
   disposition.
3. Verified the former “changed-outcome replay” instruction is absent from live REDs and survives
   only as quoted disposition/retirement history.
4. Verified the live boundary now says derived readiness/outcome is **not** acquisition identity;
   the frozen acquisition-only signature was not widened.
5. Traced replay coverage through the actual identity contract:
   - canonical known-answer and signed-field negative vectors exercise identity serialization;
   - same offering plus a differing signed field produces global `offering_identity_conflict`;
   - stored-id mismatch is recomputed and quarantined on load;
   - derived readiness changes are not misclassified as acquisition-identity changes.
6. Independently rehashed all embedded byte fixtures:
   - canonical content: 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - canonical signature: 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
   - N1: 200 bytes → `86d18b7e0949cbedb64141d8ca3a934f6a2181516c0835019f98ee341c6b8605`
   - N2: 200 bytes → `fb6b16f63985abf2efd72b1d311217bcb8cc151c9dc58f57dfb7b8bbc6f1d86f`
   - N3: 483 bytes → `d5785e03a72b74e968b5afe8d47f06d3e84e4c93c519ab47f7334f9668bac5c8`
   - N4: 479 bytes → `d87163c387735c4d9a10774d130b0b60d02886d11700f18ccc9637a04a81caf0`
7. Rechecked the accepted v24 derived-state-only remedy: failing current evidence renders rows
   19a-c; exact governed restore may heal it; wrong/unverified bytes remain invalid; no application
   flag or semantic adjudication clears acquisition integrity.
8. Rechecked rows 18a-c/19a-c, stage-2 overlays, freshness-only pill semantics, and exact drawer
   copy against the existing capture-health placement. No UI or semantic regression was introduced
   by v25.
9. Ran whitespace/diff hygiene on the submitted artifact; clean.

## Ruling

R24-1 is closed. The undefined proxy has been removed rather than disguised: no persisted
“outcome” field is invented, the acquisition identity remains acquisition-only, and every standing
identity refusal is tied to fields that actually exist in the canonical record. A future persisted
evaluation outcome would require its own framing and cannot silently enter this signature.

Plan v4 remains CLEAR. Phase A framing v25 is CLEAR, but **no Phase A RED opens until David chooses
one of the §8 retention options**; the `.gitignore` prerequisite also remains before any first
runtime write. Phase B still awaits Phase A's frozen interface plus an independent identity oracle;
Phases C/D remain closed. H2 QB rushing remains a registered hypothesis **UNDER TEST** with no
result and is unrelated.
