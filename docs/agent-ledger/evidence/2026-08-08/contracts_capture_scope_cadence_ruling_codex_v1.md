# Contracts capture scope + cadence ruling — Codex v1

Date: 2026-08-08 07:51 EDT  
Layer: Layer 1 ingestion  
Status: **RULING FOR RED AUTHORSHIP — no code, scheduler, pruning, or capture authorized by this artifact**

## Authority and question

David ruled, verbatim:

- “snapshot retention - lets go with daily in perpituity”
- then, after the contracts payload was measured, “contracts happen in the offseason, we can look at the data from 2016 forward and take a snapshot strategically near free agency time and right before the season starts”
- “keep those snapshots forever -”

Retention forever stands. This ruling resolves the Layer 1 scope and operational cadence contract before a RED is written.

## Independent measurements

Read-only probes against the latest stored contracts vintage reproduce:

- 48,511 rows total; 2,962 active; no active row has `year_signed < 2016` or an unknown `year_signed`.
- `year_signed >= 2016`: 40,401 rows.
- `year_signed >= 2016 OR year_signed + years >= 2016`: 43,517 rows; 3,116 pre-2016 signed contracts enter through the overlap limb.
- `year_signed >= 2016 OR year_signed + years - 1 >= 2016`: 42,134 rows. This proves “overlap” is ambiguous unless its time basis is declared; the 43,517 figure treats a one-year 2015 deal as reaching calendar/league-year 2016, while the 42,134 figure treats contract years as inclusive seasons.
- 1,124 rows have an unknown/incomplete term basis; none is active today. Unknown is not evidence that a historical row is irrelevant.
- Each retained raw source payload is 119,703,514 bytes. The runner writes this full raw JSON **before** normalization (`_run_locked_capture`: fetch → `write_raw_snapshot` → `normalize_rows`). Filtering after the raw write cannot deliver the advertised storage saving; filtering before it means the artifact is no longer a raw source snapshot.
- Full raw retention at two captures/year is about 2.39 GB decimal over ten years (20 × 119,703,514 bytes). The difference between the proposed row cuts and lossless capture is not worth an irreversible Layer 1 deletion.
- The current runner and exporter couple all 13 specs. The default runner calls `build_streams()`, which includes `contracts`; `publish_export()` writes every supplied table into a new immutable run directory. Merely skipping the contracts fetch is insufficient: either the next daily ready manifest omits contracts, or retaining it in the export set repeatedly copies accumulated contract history into daily run directories.

## Q1 ruling — third option (c): lossless capture; 2016+ is a view boundary

**Capture and retain the complete upstream contracts payload at each authorized window. Do not filter Layer 1 rows by `year_signed` or an inferred overlap predicate.**

David’s “from 2016 forward” binds the availability requirement for later curation/analysis: the data must preserve every contract needed to answer a 2016+ question. It does not, without a further explicit deletion instruction, license Layer 1 to discard source rows. If a later Layer 2 view needs a 2016+ term-overlap definition, that view must declare whether its time basis is league-year/calendar overlap or inclusive NFL seasons; the two predicates differ by 1,383 rows in the held vintage.

This is not a request to normalize or select in Layer 2 now. It is the Layer 1 rule: lose nothing when the marginal ten-year cost is small and the source cannot recreate our historical observation later.

## Q2 ruling — windowed twice-yearly acquisition, separate from the daily route

### 1. Annual anchors

Use a checked-in, versioned **annual anchor record**, never a recurring hardcoded month/day:

- `league_year_open`: the official NFL league-year/free-agency opening timestamp.
- `pre_week1`: the earliest regular-season kickoff timestamp for that season.

The record carries season, timezone-aware start/end window, provenance, and the source artifact/hash or official reference used to resolve each anchor. The league-year anchor cannot be derived from the game schedule; the Week 1 anchor may be derived from the governed nflverse schedule, but the resolved value is frozen into the annual record so status evaluation remains deterministic and offline.

The exact start/end bounds for each annual window are data in that record, not hidden arithmetic in code. No scheduler is installed by this ruling.

### 2. Missed windows

Catch up **and** report the miss; these are not alternatives.

- A due-window capture that succeeds records transport/durability success and `window_status=on_time`.
- If the window closes without a successful capture, the obligation becomes `missed`; it must never report `current` merely because an older snapshot exists.
- The next authorized invocation captures current state once as `captured_late`, preserving target window and actual capture time separately. That late capture advances the last successful acquisition time but **does not rewrite the missed-window history as on-time** and does not claim to reconstruct the lost window.
- Idempotence is by `(season, anchor_id)`: repeated controller invocations cannot create multiple snapshots for one satisfied target.

Transport/durability and schedule compliance are separate axes, analogous to the PFF transport/review split. Reducing them to one freshness word would create a lie in either direction.

### 3. Daily-route separation is part of the first GREEN

The existing daily canonical command must stop capturing `contracts` in the same change that introduces the windowed route. Otherwise the 48.5-GB/year path is silently reinstated.

Required shape for the RED:

- daily seasonal capture explicitly selects the 12 seasonal-axis specs;
- a dedicated contracts capture entrypoint invokes the existing guarded snapshot path for `CONTRACTS` only;
- contracts has its own status/obligation state and its own consumer commit point (ready marker/export namespace or an equally explicit content-addressed reference), so daily seasonal exports neither omit contracts ambiguously nor recopy accumulated contract history;
- the Layer 1 manifest represents contracts as an automatic connection with a **windowed** refresh target, not `daily`, and default execution runs it only when the annual obligation is due;
- the currently untracked daily nflverse plist is stale as a contracts-cadence proposal and remains uninstalled/excluded pending later scheduler authority;
- both existing contract vintages remain untouched and retained forever.

## Explicit non-authority

No pruning; no scheduler install; no provider contact; no paid action; no consumer wiring; no analytical scope selection; no capture run. A reviewed RED precedes any GREEN.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result. Nothing here bears on it.
