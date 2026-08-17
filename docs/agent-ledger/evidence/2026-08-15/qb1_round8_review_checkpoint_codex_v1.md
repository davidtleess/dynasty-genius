# QB-1 round-8 Codex review checkpoint

Date: 2026-08-15 08:1x ET  
State: review in progress; no verdict; study not executed

## Exact reviewed pins

- execution: `913225f529a0c63a30b4ee6b025c3d1ac408a5d6107be15b8a65dc80d83e9f37`
- runner: `ef7a8244d5b141eaa7280f37b269531089f5eeeb6649b230b09fcbe50bde86eb`
- correction contracts: `513ed1bd255c9c62368bcb68f8cacfbfdc3284aa5c9df3a0c8a36affd46b9b58`
- request: `38b49bc9858d1b8e4276990c505a2265172d4ecd0794aee22b515e2e14dec7dd`

Run `f8f7551c…` was ACTIVE at revision 45, round 8 open, four R7 findings
marked resolved in round 8. Scoped snapshot diff is exactly the three declared
files: execution +309/-58, runner +22/-15, contracts +248/-5.

## Independently reproduced so far

- Submitted correction + frozen/program/inference/reinforcement bundle:
  **646 passed**, 14 known numerical warnings, exit 0.
- Prior round-7 adversarial probe: **9 failed**, confirming all original R7
  examples now reject through the public runner.
- Pins for unchanged status/init/RED/ratchet/reinforcement/wire files matched.

## Fresh seams requiring executable probes

1. **H5 mechanically evaluable count.** `execution.py` increments
   `h5_presence[contrast_id]` solely when the metric key exists, then checks
   `evaluable_folds + len(excluded_folds) == h5_presence`. The round-7 smallest
   correction required equality to the mechanically derived evaluable per-fold
   count, not metric-key presence. A present c11 entry with `paired_delta=None`,
   null Spearmans, and `common_pool_n=0` appears capable of counting as
   evaluable.
2. **H5 below-floor partial evidence.** The direct below-floor special case
   checks only status and flags; it appears to admit partial numerics with
   `ni_met=True`, although the exception is for honestly unavailable evidence.
3. **F13 exact booleans.** The boundary loop rejects only a claimed `True` flip
   that cannot be recomputed. It does not reject a claimed `False` where the
   boundary seasons mechanically produce a flip, and does not reconcile the
   aggregate flip counts to the case booleans. This is weaker than the required
   exact recomputation in both directions.

## Resume sequence

1. Add a durable public-runner probe for the three seams above.
2. Run it at the exact pins; passing tests mean invalid payloads published `ok`.
3. Inspect adjacent malformed/null/duplicate cases and registration text.
4. Run Ruff/compile and the relevant full tracked suite proportionally.
5. Record CLEAR or BLOCKER findings through autonomy state before messaging.

H2 QB rushing remains **UNDER TEST** with no result. Execution remains held.
