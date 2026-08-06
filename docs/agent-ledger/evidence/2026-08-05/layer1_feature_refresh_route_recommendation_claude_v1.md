# Layer 1 Feature-Refresh Route — Claude lane position + consolidated recommendation (v1)

**Authored:** 2026-08-06 (ET), Claude Code. **Revised v2** after Codex NOT CLEAR — findings A1–A4
accepted in full, none contested. *(A4: dates in this file are ET unless a UTC `Z` suffix is shown.)*

> ## ✅ STATUS — COMPLETE. THREE LANES, ALL RECOMMEND OPTION A.
> **Claude** (this artifact) · **Codex** (`layer1_feature_refresh_route_pressure_test_codex_v3.md`) ·
> **Gemini** (`../2026-08-06/gemini_option_a_pressure_test_response.md`, under David's narrow
> explicit exception to its charter — *"tell gemini to pressure test it and recommend something as
> well"* — **not** a permanent restoration of a judgment lane).
>
> *(A1 history, kept: my v1 forbade Gemini a verdict and was wrong to; my escalation to David was
> written without knowledge of his word to Codex.)*
>
> **⚠ THREE-LANE UNANIMITY ON AN OPTION THE PRINCIPAL ALREADY LEANS TOWARD IS THE STRONGEST
> POSSIBLE YELLOW FLAG** under `02` §Falsification #4. See §6 for what was actually checked and
> §6.6 for **what would still change the answer** — stated so David can test the recommendation
> rather than take it.
**David's order:** *"I think the streams should flow into our layer 1 - what would be the point of a
different surface? im not sure i understand the choice. i want you, codex and gemini to pressure test
the idea and then come back with a recommendation."*

**Companion artifacts (independent lanes, read before consolidating, per `02` §Falsification #3):**
- Codex: `layer1_feature_refresh_route_pressure_test_codex_v3.md`
- Gemini (Operations & Telemetry — facts only, no verdict requested or given): telemetry report
  delivered 2026-08-06 in pane `dynasty:1.3`, summarized in §5 below.

---

## 0. Recommendation

**Option A, for all five streams.** `player_stats`, `rosters`, `snap_counts`, `pbp` and
`participation` each get one canonical Layer 1 capture route; the 09:15 Feature Refresh reads a
governed last-good bundle and makes no external provider call.

**Both binding lanes independently reached A on different evidence.** That convergence is recorded
as a yellow flag under `02` §Falsification #4 and checked in §6 — it is not politeness, and it is
explicitly *not* deference to David's stated lean. The decisive argument (§2) is one neither lane
held at the start and it is not a governance argument.

**This is a planning recommendation. It authorizes nothing** — no capture, store, scheduler, loader,
consumer, model use, commit or push.

---

## 1. What is actually true today (measured this session)

| Fact | Measurement |
| :-- | :-- |
| The five reads | `scripts/run_feature_refresh.py::_load_source` calls `nfl.load_player_stats/_rosters/_snap_counts/_pbp/_participation` directly |
| NGS does **not** | same function reads NGS from the last-good local export |
| `snap_counts` is **already both** | `app/data/nflverse_usage.db::player_snap_count` = **253,106 rows**, seasons 2016–2025, carrying `dg_player_id` + `identity_status` |
| What is recorded of a run | ONE sha256 (`compute_source_hash`) over all five frames + seasons window + package version + builder config + TE artifact hashes |
| Where it lives | `app/data/features_runtime/feature_refresh_latest_report.json`, `_latest` (overwritten), rewritten only on a non-noop run |
| Raw snapshots of the five | **FOUR lack raw capture** (`player_stats`, `rosters`, `pbp`, `participation`). **`snap_counts` DOES** — 129 JSON snapshots, **1,120,520,543 bytes**, in `app/data/nflverse_usage/raw` *(A2, Codex; reproduced by me)* |
| Registry coverage | `SOURCE_REGISTRY` holds **20** entries; **none** declares these five loader frames as the daily job uses them |
| Job history | 39 fires: **4 `ok` · 34 `noop` · 1 `refusing to publish`** |

---

## 2. The strongest argument — established repository precedent, in this same job

**A3 (Codex, accepted). My v1 called this "David already ruled this exact question" and that was an
OVERCLAIM — the same defect class as attributing agent-authored codification to his authority.**
Commit `1131d102` (2026-07-31) proves the migration: within this same 09:15 job, NGS was converged
onto one canonical adapter reading a **local last-good export** instead of live provider calls, on
the reasoning recorded in `_load_source`:

> NGS comes from the LAST-GOOD LOCAL EXPORT, not from three live calls inside the 09:15 scheduled
> chain … Three network round-trips in the critical path were three new ways the morning halts, with
> no cached fallback despite the registry declaring `failure_behavior="use_cached"`.

**But David's preserved words in that commit are *"do it properly"* and *"work with the team - go
forward on all 4."*** He authorized the work; **the local-last-good shape was the lanes' engineering
decision** (the commit records it as "Codex's required shape"). So the correct claim is:

**Option A is David-ratified repository precedent for this exact job and this exact failure mode —
NOT his explicit technical selection of A over B.** Weaker than v1 claimed, and still the strongest
structural point available: B is the state this job was moved *out of*, and `01` §Source Adapter
Rules was the stated reason.

**The failure mode is not hypothetical.** On **2026-08-02** the job logged `refusing to publish:
dynamic source probe found no loadable season at 2026 or 2025 … Failed to download
…pbp_participation_2021.parquet: … Read timed out.` A live provider timeout aborted a derivation that
had nothing to do with that season. Gemini independently dated it and confirmed the adjacent
2026-08-03 run recovered. Under A, capture fails in isolation and derivation runs from last-good
while disclosing staleness.

---

## 3. Steelman of Option B, and why each strand fails

**B1 — volume.** The real case for B, and my own named weakest point going in. Now measured.
Codex measured the job's actual default window (2018–2025): **pbp 152.24 MiB, 80.41% of 189.32 MiB
total**. I measured a wider 2016–2025 window: pbp 198.0 MB of ~246 MB. Same picture, different
window and units — not a conflict.
*Fails because it argues about representation, not lineage.* Codex sent a conditional request for
`play_by_play_2025.parquet` with the observed ETag and got **HTTP 304, zero payload** — so an A
capture checks partitions without re-downloading unchanged bytes. B, by contrast, re-downloads
everything every run (nflreadpy 0.1.5 caches in memory only, and each fire is a fresh process). On
volume, **B is the more expensive option today**, not the cheaper one.

**B2 — the derived candidate is what matters, so raw capture is redundant.**
*Fails on diagnosis.* The single combined `source_hash` cannot say which of the five inputs changed,
so it cannot distinguish a provider correction from a code or config change.

**B3 — the data is publicly re-fetchable, so replay needs no capture. (The strongest surviving
anti-A argument, and I am not claiming it is fully closed.)**
Partly right: for a genuinely immutable published asset, re-fetching reproduces the bytes. But the
provider serves an `ETag`, which exists precisely because assets can change; and the 2026-08-02
incident shows a *past* season's asset was not reliably retrievable at all. `01` §Source Adapter
Rules independently requires "write a raw snapshot before parsing when feasible" regardless of
re-fetchability.
**Named residual, unmeasured by any lane: how often nflverse revises an already-published season
parquet.** That number does not change the A/B choice — it sets retention policy (how often
content-addressed capture creates a new version). The measurement that settles it is recording
per-season parquet content hashes on successive days.

---

## 4. The sharp case — `snap_counts` is already both routes

Canonical stream B4 holds 253,106 identity-resolved rows and has **zero production consumers**;
the same source is also pulled live every morning. **One of those two routes is the duplicate
today, whichever way this is decided.** Under B, we would be choosing to keep captured,
identity-resolved data permanently unused, or delete it.

Codex ran the decisive experiment: over the Feature Refresh window, live source and canonical export
both hold **exactly 205,354 rows**, value-identical across all 16 columns after sorting (only an
intentional Int32/Int64 widening on `season`/`week` differs). It then substituted canonical B4 for
the live frame in a read-only assembly holding all other inputs fixed: both candidates were
**2,743 rows × 39 columns and value-identical**. That makes `snap_counts` the correct first
migration — the parity is measured, not assumed.

---

## 5. Gemini's operational slice (facts only — no verdict requested or given)

- 39 fires dated: 12 noop (Jun 28–Jul 9) · ok Jul 10 · 20 noop (Jul 11–30) · ok Jul 31 · ok Aug 1 ·
  **refusing Aug 2** · ok Aug 3 · noop Aug 4 · noop Aug 5. **Independently confirms my 4/34/1 counts.**
- `feature_refresh.err.log` is 0 bytes.
- The `2026-08-03T13:38:58Z` report timestamp is expected noop behaviour, **not** a stalled job —
  confirming my reading rather than my having assumed it.
- **`feature_refresh` is registered `"cadence": "weekly"` with `"dormant_ok": true` while the job
  fires DAILY at 09:15.** A job-fire vs freshness-policy mismatch, exactly the distinction the plan's
  row contract separates.
- **No freshness registration exists for any of the five source datasets.**

---

## 6. Adversarial check on the convergence

`02` §Falsification #4 makes a frictionless unanimous result a yellow flag, and David's stated lean
toward A makes deference the specific risk here. Checks run:

1. **Different evidence bases.** Codex: ETag/304 probe, byte table, the B4 substitution experiment,
   the JSON-envelope 37.12× expansion finding. Claude: the 2026-07-31 NGS precedent, the 39-fire log
   distribution, the registry gap, the one-way-hash replay analysis. Neither lane's conclusion rests
   on the other's measurements.
2. **My prior position was tested and partially corrected, not confirmed.** I went in claiming
   "nothing recorded what the provider served." That was **too strong**: a combined `source_hash`
   *is* recorded. The claim survives only in the weaker, correct form — *something is recorded, but
   nothing replayable*. Recorded rather than smoothed.
3. **My first proposed argument was killed.** Volume favours A, not B — the opposite of what I
   expected when I named pbp as my weakest point.
4. **B3 is left open rather than dismissed**, with the measurement that would settle it named.
5. **Gemini's lane agreed independently, and I am NOT passing two of its claims through unchecked**
   — a third concurring lane is a reason to audit harder, not to relax:
   - It says rebuildable assets are excluded from the backup manifest *"to prevent upload timeouts."*
     **The exclusion is real; the stated REASON is Gemini's inference and is not established** — and
     "upload timeout" is the very mechanism this session already withdrew for want of evidence (only
     `upload_failed:<path>` was ever observed). **Do not let it re-enter through a telemetry report.**
   - It describes the recovery run as *"still uploading the 2.2 GiB package."* **Measured: the upload
     phase COMPLETED — 509 objects — and the run is in its restore drill.** Minor, corrected here so
     the figure is not carried forward wrong.
   Its substantive operational findings (no reliability advantage to live reads, the `snap_counts`
   double-route, failure isolation, the 37× JSON penalty, uniform lineage) **corroborate** Codex and
   me from the operations seat and are consistent with what both lanes measured independently.
6. **The check was not sufficient.** Codex then returned **NOT CLEAR** on this artifact with four
   findings, two of them HIGH, all accepted without contest: I forbade Gemini a verdict against
   David's direct word (A1); I asserted "no raw snapshots exist" when `snap_counts` has 129 of them
   totalling 1.12 GB (A2 — my search looked for *directories* named after the streams, so the method
   could never have found flat per-stream files, and I stated the negative confidently anyway); and
   I overclaimed David's authority on the decisive argument (A3). **A self-run adversarial check
   caught none of these. The independent lane caught all three** — which is the §Falsification #4
   point, demonstrated on this document rather than quoted in it.

---

### 6.6 What would still change the answer — stated so this can be tested, not just accepted

Three lanes agreeing does not make A right. These are the things that would move it, with who could
settle each:

1. ~~**If nflverse season parquets turn out to be genuinely immutable once published**, then
   re-fetching reproduces the bytes and the replayability argument — the single strongest case for A —
   weakens sharply. **Nobody measured this.**~~
   **✅ MEASURED AND CLOSED 2026-08-06 — IT RESOLVED IN FAVOUR OF A.** Codex ran the test; I
   reproduced it independently against the GitHub release API. **Season URLs are MUTABLE assets.**
   The 2018-season files carry asset timestamps *years after* the 2018 season:
   `play_by_play_2018.parquet` created **2025-04-30**, `stats_player_week_2018.parquet` created
   **2025-04-30**, `snap_counts_2018.parquet` created **2025-10-06**. A stable URL is **not** a stable
   artifact.
   **⇒ B3, the strongest anti-A argument, is DEAD.** Re-fetching does not reproduce what the provider
   served; "we can always re-download it" was false. **This is the open question that could have
   overturned the recommendation, and it strengthened it instead.**
   **BOUNDARY, stated because the temptation is to over-read it:** this proves **mutability only**.
   It does **not** establish a revision *rate*, *which* rows changed, or *why*. **No semantic
   revision-rate claim is made or licensed.**
   **Retention consequence:** capture must be **content-addressed and must KEEP PRIOR ACCEPTED
   VERSIONS when bytes change** — a freeze-at-season-key scheme would silently lose the earlier
   vintage. *(Codex's conclusion, adopted.)*
   *(Discrepancy recorded rather than smoothed: Codex reported `stats_player_week_2018.parquet`
   overwritten **2026-07-10**; my own probe returned **2025-04-30**. I have used my measurement and
   flagged the difference to Codex. **The conclusion is unaffected either way** — a 2018 asset
   stamped in 2025 already proves mutability.)*
2. **If the retention contract lands on option (b)** — accepting that only the provider's current
   version is recoverable — then capturing raw bytes buys much less, and A's shape should shrink to
   normalized captures rather than content-addressed raw. **That is David's ruling, not a lane's.**
3. **If the storage ceiling David sets is below what content-addressed `pbp` needs**, A must be
   re-scoped rather than partially implemented. `pbp` is 80% of the bytes.
4. **Per-stream mixture:** Gemini calls a mixture *"operationally incoherent."* Read precisely, all
   three lanes agree on **one authoritative route per stream**; what Codex and I proposed varying is
   **capture policy and migration order**, not route. If David reads the sequencing in §7.2 as a
   permanent mixed route, that is a misread we introduced and should be corrected, not defended.

**What none of the three lanes can settle:** whether Layer 1 should absorb this work at all right
now. **That is sequencing, and `05` §1 makes it David's alone.** No lane asserted otherwise here.

## 7. What this does not decide — David's calls

1. **A retention contract, which A forces and B hides.** The backup manifest currently excludes
   `app/data/nflverse_usage.db` as rebuildable and does not protect `app/data/nflverse_usage/raw`
   (~5.2 GiB). Either (a) protect content-addressed exact source bytes as replay evidence, or
   (b) accept explicitly that only the provider's current version is recoverable. Codex and I both
   recommend (a), after the backup recovery succeeds and with a numeric ceiling.
   **This is now sharper because of A2:** `snap_counts` already carries **1.12 GB of raw JSON
   history that nothing protects**, at ~37× the size of the equivalent Parquet bytes. The retention
   question is not hypothetical future cost — it is unprotected data on disk today, and it is the
   strongest argument against simply reusing the existing raw-snapshot shape for `pbp`.
2. **Sequencing.** `snap_counts` first (parity measured); `pbp` last, behind the retention design —
   it is 80% of the bytes and must not hold up the other four.
3. **The `01` §Source Adapter Rules gap is real either way.** None of the 20 registry entries
   declares these five as the daily job uses them. Option A closes it; Option B requires the
   amendment be written and ratified, not merely implied.
4. Storage/transfer ceilings, and the enablement word for any job.

---

**Boundaries.** Planning only. Phase B and Layer 2 remain CLOSED. `contracts` is `substrate_only`
with zero product-store rows. `ff_rankings` is `blocked_for_use` on redundancy/priority, not licence.
**H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
