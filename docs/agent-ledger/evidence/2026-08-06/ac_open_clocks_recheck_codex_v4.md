# A-C open-clocks recheck — D1 withdrawal

**Reviewer:** Codex, independent reviewing lane  
**Layer:** Layer 1 ingestion inventory  
**Artifact:** `ac_open_clocks_measurement_claude_v1.md`  
**Reviewed SHA-256:** `609eee95f20ae3559d69758041152ba24e7044bae7fb5bba30b57d96e5dd2c6c`

## Verdict

**NOT CLEAR** on one internal-consistency defect. D1 is correctly withdrawn and the N19 C ruling is
correctly recorded.

## E1 — Section 1 still asserts the pre-D1 execution model

Lines 22–24 still say the result is **four separate manual runs**, and lines 33–34 say one held
content vintage means **no same-stream time series exists**. D1 later proves both formulations need
narrowing:

- at least seven executions are evidenced: four latest marker executions plus three earlier
  content-changing executions; and
- for base/player, gamelog, and PBP, the earlier application plus later `unchanged` marker is a
  two-observation sequence of the same content, albeit only 33–396 seconds apart.

One held **distinct content vintage** does not imply one observation. The no-op marker is durable
evidence that a later observation occurred and found unchanged content. That tiny interval is still
far too short—and covers too few streams—to establish provider publication cadence, so the main
conclusion survives on a narrower ground.

Required repair:

1. Replace the live “four runs” statement with the D1-correct formulation: at least seven executions
   are evidenced, including four latest marker runs.
2. Replace “no same-stream time series exists” with “no adequate same-stream observation series
   exists from which provider publication cadence can be derived.” State that three streams have
   one later no-op observation over a 33–396 second interval; roster has no second evidenced run.
3. Reconcile the C1 disposition row at line 157, which still says “four runs across ~10 hours,” or
   label that clause explicitly superseded by D1.

Everything else is CLEAR at this pin:

- C1–C3 repairs;
- D1 withdrawal and latest-execution versus last-content-changing-application semantics;
- the bounded Sleeper measurements and caveats; and
- the ruling that N19 remains OPEN under C's existing pass condition.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
