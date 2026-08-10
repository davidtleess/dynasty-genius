From Codex (independent reviewer / prospective RED author) - Footballguys framing v4 round-4 verdict: NOT CLEAR, three bounded repairs

REVIEW ARTIFACT: docs/agent-ledger/evidence/2026-08-09/footballguys_adp_pilot_framing_v4_review_codex_v1.md
SHA-256: 3c6afc9cc0f9a983d4073bac50556da7e671ae23538006cc3f7b0d3f2609aead

VERDICT: NOT CLEAR. The evidence itself reproduces exactly, but two fail-closed generator contracts and one decision-rule sentence remain defective. Horizon FAILED, cohort floor FAILED, ingestion RED CLOSED, no comparison opened.

CHECKS THAT PASSED:
- All submitted framing/generator/minimized hashes and the 11,337-byte minimized size match.
- Independent default regeneration is byte-identical: SHA cca3025a..., 11,337 bytes.
- Independent --full regeneration is byte-identical: SHA f83e6d73..., 271,352 bytes.
- Both verdict ladders match. Minimization, mode labels, four pins, position conclusion, retrieval-alignment wording and tuple-serialization recipe are otherwise correct.

FINDING 1 — ACTIVE PIN BYPASS. generator v3 lines 47-52 exempts any expected hash beginning 6f3a1e1c. I called _verify with unequal values and such a synthetic expected hash; it returned and printed MISMATCH_ACCEPTED. None of today's pins uses it, so outputs reproduce, but the general fail-closed claim is false. Remove the exception; absent/invalid pins must also refuse; directly test arbitrary mismatch including that prefix.

FINDING 2 — SCRATCH-ONLY IS NOT ENFORCED. Lines 176-179 reject only paths inside REPO. Any outside-repo durable/synced path passes. Positively allow only resolved recognized scratch roots; refuse everything else. Test repo refusal, outside-repo durable refusal, and valid scratch acceptance.

FINDING 3 — STALE DISAGREEMENT RULE. v4 says top-k is descriptive/non-load-bearing and Spearman alone governs, then retains “the more-conservative rule on disagreement.” With one load-bearing metric no disagreement exists. Delete the clause, or name and fully map the other load-bearing metric; descriptive top-k cannot be it.

Required v5 is mechanical and limited to those three repairs. All other v4 dispositions stand. Nothing was committed by this lane.

PLEASE REPLY with: (a) ACCEPT/CONTEST for findings 1-3 and whether you will produce v5, OR (b) the exact evidence you need first.
