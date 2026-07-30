# TWO ESCALATIONS — the scheduling work cannot proceed as scoped

**Claude Code. Written 2026-07-30 13:51:17 EDT** *(machine clock, pasted).*
**Review verdict TW30-WORD-Z: NOT CLEAR, six blockers. ALL SIX ACCEPTED, none challenged.**
**No RED is authorable and that is correct.** Nothing loaded, no plist authored, no producer touched.

---

## ESCALATION 1 — Problem 3 has no correct answer inside its own framing

**My proposed fix was wrong, and the disproof is decisive.** I proposed pointing `timestamp_field` at
`capture_report.artifact_vintage`. **Reproduced from the capture store at the timestamp above
(`model_forward_capture_raw`, 37 capture dates):**

| capture_date | artifact_vintage | semantic_output_hash |
| :-- | :-- | :-- |
| 2026-06-26 | `2026-06-26T13:30:08Z` | `1ea7207f8b9e` |
| 2026-06-27 | `2026-06-27T13:30:03Z` | `1ea7207f8b9e` |
| 2026-06-28 | `2026-06-28T13:45:09Z` | `1ea7207f8b9e` |
| … through 2026-07-03 | **advances every day** | **identical every day** |

**`artifact_vintage` is a rebuild-time stamp.** Pointing freshness at it is **the mtime disease under
another field name** — the reviewer's phrase, and the data says exactly that.

**The deeper finding: the registry's freshness model is TIMESTAMP-SHAPED, and this artifact needs a
CONTENT IDENTITY.** The producer already computes two — `semantic_output_hash` and `provenance_hash`
— and they behave correctly: identical across the frozen window, and moving on 07-28/29/30 when the
population actually churned.

**So "point it at a real content field" cannot be satisfied by any timestamp field that exists.** The
honest fix is a **content-identity freshness capability** — which is precisely David's content-basis
ruling, and is a larger change than the one authorised. **Escalated, not attempted.**

## ESCALATION 2 — the chain cannot be made coherent without splitting a producer

**Confirmed from source:**

- **PVO consumes the marker-pinned league snapshot** —
  `build_universe_pvo_batch.py:29` (`SNAPSHOT_PATH = load_league_set_for_root(ROOT).paths["snapshot.json"]`), read at `:360`.
- **League capture publishes the snapshot AND the PVO-derived artifacts ATOMICALLY AS ONE SET** —
  `league_capture.py:213` (`contents = {"snapshot.json": payload, **derived}`), where `derived`
  comes from a chain that itself calls `resolve_pvo_source`.

**So the two producers are mutually dependent, and every whole-job ordering leaves one edge stale.**
My "league capture after PVO" rule **moves the stale edge; it does not remove it.**

**The coherent stage order** (the reviewer's, and I agree): fetch/validate snapshot → build PVO from
**that** snapshot → derive league artifacts from **that** PVO and the **same** snapshot → publish the
coherent league set.

**That requires splitting league capture's fetch stage from its derive stage — a PRODUCER CHANGE**,
which collides head-on with the standing boundary *"no producer touched."*

**I am not resolving that collision.** It is David's scope to widen or not.

## What is accepted from the review, in full

1. **Stop-on-failure is binding** — no continue-on-error RED is permissible. Agreed.
2. **The three telemetry mismatches + the missing halt measurement reproduce.** Agreed.
3. **START-MARKER BLOCKER accepted.** A start record proves a run *began*; it cannot separate a live
   `running` process from one killed or hung before terminal rewrite, and a prior marker is not
   intrinsically DID-NOT-RUN without current time plus the expected schedule occurrence. **The health
   evaluator also collapses every non-success status to `producer_failed`**, so `running` either
   greens an abandoned run or reds a healthy one. **My design was under-specified and the correction
   is right:** atomic `run_id` + expected occurrence, atomic start/terminal writes, explicit
   `ok`/`halted` schemas, a heartbeat/lease/ruled deadline for `interrupted_or_stuck`, defined health
   mappings for all four states, and per-attempt history rather than a singleton overwritten at start.
4. **Content-basis blocker** — Escalation 1.
5. **Chain-graph blocker** — Escalation 2.
6. **Contract defects accepted:** assert **DAG partial-order edges**, not an invented total order
   between independent roots; `refresh_league_intelligence.py` is **callable but not scheduled**, so
   my duplicate-execution row had a false premise; chained `scheduled_time_local` semantics are
   undefined; label-collision scope is **all installed labels**, not eight; and **no roster-capacity
   job exists to "stay" weekly — it must be CREATED at its registered cadence**, which my wording
   assumed away.

## Position

**No RED should be authored until David rules on both escalations.** A RED written now would encode
either a false freshness guarantee or an incoherent graph, and would then be used as evidence that
both were fine.
