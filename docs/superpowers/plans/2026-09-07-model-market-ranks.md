# DG183 — comparable independent ranks

Approved scope and frozen inputs: dg-build/MODEL-MARKET-RANKS-BUILD-2026-09-07.md. Preserve accepted DG180 baseline. No model changes, shared writes, dependency installs, commits or deployment.

1. Write source/route tests first: frozen cohort facts, ties and signed gaps, missing versus zero, source tamper/config errors, settings and identities. Observe failure, implement a read-only manifest-bound adapter and typed API, run relevant ranking/contract tests.
2. Write UI tests first for the shared capability provider, roster search/filter/open, primary player pair, ties/missing and configured errors. Implement a single source for both main roster and player pages; preserve legacy only for explicit not_configured. Use snapshot identity directly in new player mode to avoid old model dependencies and stale selection.
3. Independently reconstruct all values/ranks/source hashes/roster flags from raw frozen inputs in an oracle without adapter imports. Verify actual endpoint payload. Preserve published raw FantasyCalc overall_rank: this snapshot ranks 399 players, excluding picks. Signed gap = market minus ours, interval closest to zero gives minimum defensible difference.
4. Generate API schema/client; typecheck, lint, relevant full tests/build. Private cache/runtime before serving isolated local8789. Preserve existing8787/8788.
5. Inspect actual built roster and player drawer/page at1440 and390: primary comparison above fold, no horizontal overflow, keyboard and axe. Source/API oracle, missing Rasheen, structural zero ties, market ties, player selection change and configured failures. Independent reviewer checks implementation and screenshots; fix concrete findings.
6. Record evidence/required autonomy receipts and concise handoff; final READY_FOR_GATE without commit/merge/deploy.
