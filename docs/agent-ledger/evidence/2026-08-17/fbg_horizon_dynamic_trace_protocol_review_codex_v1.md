# Footballguys horizon dynamic-trace protocol review — Codex v1

Date: 2026-08-17  
Thread: `fbg-horizon-1`  
Reviewed proposal: David-witnessed runtime trace of Draft Dominator 2026i's league-format and ADP-source selectors against the retained `adp.csv` fingerprints  
Fingerprint script: `docs/agent-ledger/evidence/2026-08-17/fbg_horizon_fingerprint_claude_v1.py`, SHA-256 `ea084a902b7693412f7495cb2b0084b46244c579c5f02e51eacffd44a1af7654`

## Verdict

**(a) The dynamic selector trace is an admissible binding-proof route. Static decompilation or provider documentation is not required if the runtime trace passes the controls below.**

This is a protocol ruling, not a factual-horizon finding. The trace has not run. Until a captured execution passes every control, plan-v2 §1 remains `horizon=unknown` and Phase C remains closed. A passing trace may support an adjudication packet; it does not itself write semantic state or supply David's separate adjudication word.

## Independent fingerprint checks

I ran the submitted script read-only over retained archive SHA-256 `d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c`. Its two top-12 lists reproduce exactly.

I then compared each list against **all 18 ADP fields**, not only the two Sleeper fields:

- `adp_sleeper-sf` is the only field with its exact 12-player ordered fingerprint. Its prefix is already unique after two players. Its first 12 values are exact unique integral ranks 1–12, so no tie-break ambiguity exists.
- `adp_sleeper-1qb` is the only field with its exact 12-player ordered fingerprint. Its prefix is unique after four players. Its first 12 values are exact unique integral ranks 1–12, so no tie-break ambiguity exists.
- No other populated ADP field has either exact top-12 sequence.
- `adp_sleeper-redraft` is empty in this vintage. That fact remains non-dispositive by itself.

Therefore, a correctly controlled runtime observation of both exact ordered fingerprints uniquely identifies the two retained columns among the archive's complete ADP field set. It eliminates the positional/configuration steelman that defeated evidence v1: the provider app itself, not a label census, supplies the selector-to-output mapping.

## Required passing protocol

1. **Bind the running artifact.** Before launch, verify the unpacked app's binary SHA-256 is `d9bc9b2d…`, bundled `adp.csv` SHA-256 is `1f7afcbf…`, and `version.txt` is exactly `2026i`; record the retained archive/receipt provenance. Verify the same resource hashes after the trace. Do not permit an in-app data refresh or silent resource replacement during the observation.
2. **Prove what is being read.** The capture must show either an ADP column sorted ascending with its visible numeric values, or an equally explicit UI state proving the displayed order is the selected ADP source's order. An unspecified/default “board top-12” is insufficient because another ranking or secondary sort could drive it.
3. **Run a reversible positive control in one session.** With the app fully started and no draft picks made:
   - set league format to Superflex and source to `Sleeper Dynasty`; capture the exact `adp_sleeper-sf` ranks 1–12/order;
   - change only league format to 1QB, preserving source and sort; capture the exact `adp_sleeper-1qb` ranks 1–12/order;
   - change only league format back to Superflex and reproduce the first ordering. This A→B→A step defeats stale-board, non-applied-config, and one-way-cache explanations.
4. **Treat redraft as corroboration only.** Selecting `Sleeper Redraft` and observing an explicit no-data state is useful, but it cannot carry the proof. The two positive, unique fingerprints are the binding evidence. Any fallback to another source, retention of the prior list, or ambiguous blank state fails this control without weakening the positive trace.
5. **Capture provenance, not memory.** Prefer one continuous screen recording covering About/version, league format, selected source, explicit ADP sort/value basis, and all A→B→A transitions. If screenshots are used, retain full-frame originals that visibly bind each setting to its result. Record timestamp/timezone, David's witness statement, and SHA-256 for every capture artifact.
6. **Fail closed.** Any rank/name mismatch, hidden or ambiguous sort basis, inability to prove the setting changed, resource-hash drift, update prompt/refresh, or screenshot gap leaves `horizon=unknown`. Do not repair the conclusion by using the empty redraft column, numeric shape, filename morphology, or David's acceptance criterion.

## Why this meets plan-v2 §1

Plan-v2 §1 permits provider-authentic evidence or captured export/UI metadata with hash and retrieval provenance. A hash-bound execution of the provider's own app, with the selected `Sleeper Dynasty` label and Superflex configuration causing the unique retained `adp_sleeper-sf` fingerprint, is direct captured UI behavior. It is stronger than the rejected static structural inference because it observes the selector function rather than inferring it from a non-exhaustive string table.

If the controlled trace passes, the evidence chain is sufficient to present `horizon=dynasty_startup` for David's separate adjudication. If it fails or cannot be captured as specified, the preferred next path is provider-authentic documentation; full disassembly remains optional rather than mandatory.

## Boundary

This review did not execute Draft Dominator, contact Footballguys, mutate the retained object or any store, write semantic state, adjudicate the horizon, or open Phase C.
