# A-C open-clocks recheck — C1–C3 disposition

**Reviewer:** Codex, independent reviewing lane  
**Layer:** Layer 1 ingestion inventory  
**Artifact:** `ac_open_clocks_measurement_claude_v1.md`  
**Reviewed SHA-256:** `40b8ceabc47dfb1c4a9113c636fbde0d2bc59825394eb6788c10fb1531cc0ede`

## Verdict

**NOT CLEAR** on one new factual finding. C1–C3 are correctly repaired. N19 does **not** satisfy
C's existing pass condition.

## C1–C3 recheck

- **C1 repaired:** the artifact now uses the sufficient claim—one held captured vintage per
  canonical PlayerProfiler stream—rather than inferring provider cadence from local timestamps.
- **C2 repaired:** `0.00` is correctly described as normalized change rate, with raw stability
  explicitly unestablished.
- **C3 repaired:** the player result is keyed by `sleeper_player_id`: 0 removed, 2 added, 36 shared
  IDs changed.

## D1 — the new timestamp-semantics finding compares different executions

Lines 38–46 say the DB ledger and latest status marker disagree about when the **same run** happened
and therefore need timestamp-semantics remediation. The durable records and code show a simpler,
already-defined explanation:

- the latest base/player, gamelog, and PBP markers report every block as `unchanged`;
- their marker `started_at` values therefore belong to later no-op executions;
- `PlayerProfilerStore.apply_block` returns `unchanged` before replacing the `pp_capture` row, so
  the DB `ingested_at` remains the earlier content-changing application time;
- the PBP loader has the same early-return behavior when source hash and mapping version match; and
- roster reports `inserted`, so its marker start and DB ingest timestamp correctly match.

Thus the two timestamps are not competing provenance for one execution. They describe different
events: latest attempted execution versus last content-changing application. The artifact should
withdraw “same run,” “disagree,” and the claimed remediation need. It may record the distinction as
measured behavior, but not as an unresolved timestamp-semantics defect.

The evidence also means “four separate manual runs” is not a complete execution count: there were
at least the four latest marker runs plus the earlier content-changing executions retained in the
DB for base/player, gamelog, and PBP. The inventory-relevant fact remains one held **content
vintage** per canonical stream.

## Ruling on C's N19 pass condition

**N19 remains OPEN.** The existing §6A pass condition requires each source-publish field to be
independently verified or explicitly `N/A`/`not scheduled` with evidence; `UNVERIFIED` leaves the
row open.

This artifact expressly measures a bounded, off-season **normalized change rhythm**, not a
source-publish cadence. It also has no time series for N19-only families such as matchups and the
per-endpoint draft/traded-pick histories. Source publication is applicable—not `N/A`—so partial
normalized evidence cannot satisfy the binary condition.

The correct catalog update, after D1 is fixed, is to replace a blank unknown with the bounded facts
and keep the source-publish field open. Closing it requires either authoritative source semantics
for the endpoint families or a governed observation series that actually measures the required
clock.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
