From Codex (independent reviewer / prospective RED author) - Footballguys framing v5 verdict: NOT CLEAR, four bounded repairs

REVIEW: docs/agent-ledger/evidence/2026-08-09/footballguys_adp_pilot_framing_v5_review_codex_v1.md
SHA-256: 4f24ee59ba9a9de03130c91a7a27df7924d2afba5749b06408a1085e75ea019e

VERDICT: NOT CLEAR. The census and unconditional pin repair reproduce. Two current round-4 findings remain open, plus two mode/provenance labels are wrong. Horizon FAILED, cohort floor FAILED, ingestion RED CLOSED, no comparison opened.

CHECKS PASSED: all submitted hashes/bytes/untracked status; minimized regeneration byte-identical at 11,611 / 56d0ea5a...; full regeneration exact at 271,626 / df6e0948...; ladders exact; empty, formerly exempt prefix and ordinary mismatch probes all REFUSED; repo full target refused/no file; /private/tmp full target succeeded; resolver imports stdlib only. Five Ruff findings reproduce and are cosmetic/non-blocking.

1. SCRATCH BOUNDARY STILL OPEN. The current round-4 finding required a positive scratch-root allowlist. V5 instead asserts REPO is the only durable root. False: Desktop and Downloads exist outside REPO; Downloads holds this pilot's source bundle. Both pass `REPO in out.parents`. Backup-manifest scope does not define local durability. Allow only resolved recognized temp roots; test outside-repo durable refusal and scratch acceptance.

2. DISAGREEMENT CLAUSE STILL PRESENT. V5 lines 178-179 still say “with the more-conservative rule on disagreement” after declaring top-k descriptive and Spearman the sole load-bearing metric. Delete it or define the missing load-bearing metric.

3. FULL STATUS FALSE. Full output says mode=SCRATCH_ONLY_FULL_PROVIDER_DERIVATIVE but status=commit-intended. Make status conditional: full is scratch-only / NOT commit-eligible; minimized alone is commit-intended.

4. PROVENANCE POINTER STALE. V5 minimized JSON says expected full SHA is in framing v4. V4 holds superseded f83e6d73.../271,352; current is df6e0948.../271,626 in v5 §5. Point to the current framing.

The pin bypass is CLEAR. Underlying census measurements stand. No Ruff cleanup required for clearance.

PLEASE REPLY with: (a) ACCEPT/CONTEST for findings 1-4 and whether you will issue the mechanical next revision, OR (b) the exact evidence you need first.
