# Morning chain design + RED contract — TW30-WORD-V (Option A)

**Claude Code. Written 2026-07-30 12:57:59 EDT** *(machine clock, pasted).*
**David's word, verbatim:** *"go with option A, and make league_opportunity daily."*
**Design + RED contract only. No plist authored, nothing loaded, no producer touched.**

**Layer:** 1–2. **roster_capacity's cadence is UNRULED and therefore unchanged — an unruled item is
not an invitation.**

---

## §1 — The measured dependency graph

Every edge below was read from source at the timestamp above, not inferred from the clock times.

| Consumer | Consumes | Evidence |
| :-- | :-- | :-- |
| PVO refresh | Engine B feature runtime | `build_universe_pvo_batch.py:32-33,243-245` |
| **league capture** | **the PVO runtime** | `run_league_snapshot_capture.py:45-68` — `_production_derive` calls `resolve_pvo_source` |
| market divergence | the PVO runtime + FC capture | `run_market_divergence_refresh.py:50-52` (`resolve_pvo_source`) |
| **league opportunity** | **league capture output + market divergence** | `build_league_opportunity_map.py:15,22,24` |
| roster capacity | PVO + Sleeper snapshot | producer docstring (read-only simulator) |

**Correct topological order:** FC → feature refresh → PVO → league capture → market divergence →
league opportunity → what-changed.

## §2 — THREE ordering inversions, not one

The clock schedule encodes this graph wrongly in three places:

| # | Inversion | Current clock | Status |
| --: | :-- | :-- | :-- |
| 1 | PVO consumes features while the feature job may still run | 09:15 → 09:30 | **Named by Tower; the reason for this change** |
| 2 | **league opportunity** consumes market divergence, but is registered **before** it | 09:35 vs 09:40 | **Found while framing; Tower ruled its ordering is part of this change** |
| 3 | **league capture consumes the PVO runtime, but runs TEN MINUTES BEFORE IT** | 09:20 vs 09:30 | **FOUND HERE. Not previously named by anyone.** |

**Inversion 3 is surfaced, not silently absorbed.** It sits inside the cluster Option A reorders, so
a correct chain necessarily fixes it — there is no way to author the chain in dependency order and
leave it inverted. **But it was not in David's three problems and I am not treating an implication as
an authorisation.** Tower's ruling requested: does the chain cover it, or does it stop and route?

**If it is covered, note what it means:** the daily league snapshot — David's own roster, the twelve
teams, the derived posture and value matrix — has been built against **yesterday's** valuation every
day. That is the same defect as problem 1, one layer over, and it was not on anyone's list.

## §3 — The chain, as Option A

**Pattern already in the repo:** `refresh_league_intelligence.py` runs `PhaseStep` entries in
dependency order by subprocess and is the shipped precedent David's Option A points at.

**Proposed shape — one daily job invoking a sequence in topological order**, replacing the separate
per-step `StartCalendarInterval` triggers for the chained members. **`roster_capacity` stays a
separate weekly job** (its cadence is unruled) ordered after the chain's daily window.

**The design question the RED must settle, not me:** what happens when a step fails mid-chain.
Today's separate jobs are independent — a feature failure does not stop the PVO capture. A chain
couples them. **Both behaviours are defensible and the choice is a product decision**: stopping
protects downstream artifacts from being built on a failed upstream; continuing protects the daily
PIT accrual that Option A was chosen to preserve. **I have not chosen. It goes to David with the
verdict.**

## §4 — RED contract

**In scope:** launchd plist(s) under `ops/launchd/`, an orchestration entry point if the RED requires
one, and `app/config/report_freshness.json` for `league_opportunity`'s cadence (`weekly` → `daily`)
and its `scheduled_time_local`. **Out of scope and untouched:** every producer, the model, the SQL,
and the artifacts under review.

**Rows the RED must cover:**

1. **Topological order is asserted, not implied by clock arithmetic.** A test that would still pass if
   two steps were swapped is not testing the fix.
2. **Inversion 2 cannot survive:** `league_opportunity` must run **after** market divergence. A
   configuration placing it earlier must fail the test.
3. **Inversion 3 cannot survive** *(if Tower rules it in scope)*: league capture must run **after**
   PVO.
4. **No duplicate execution.** `league_opportunity` already runs as PhaseStep 17.5 of
   `refresh_league_intelligence.py`. A design that both chains it and leaves the orchestrator path
   live must be caught — **two jobs producing one artifact is the failure Tower named as worse than
   absence.**
5. **`Label` uniqueness** against the eight labels already present in `~/Library/LaunchAgents`.
6. **Every `ProgramArguments` path exists** — the nonexistent-path failure, asserted per path.
7. **The registry and the scheduler must agree:** `league_opportunity` declared `daily` must not be
   scheduled weekly, and vice versa. The declaration/aim mismatch is the defect class of this whole
   morning.
8. **`roster_capacity` is byte-unchanged** — cadence unruled.
9. **Mid-chain failure behaviour is asserted explicitly**, whichever way David rules, so the
   behaviour is a decision on the record rather than an emergent property.
10. **Nothing in the RED loads, reloads, or mutates a job on the machine.** Loading is a separate
    explicit step, verified afterwards by reading back what `launchctl` actually holds — **never by an
    exit code.**

## §5 — What this does not claim

It makes nothing fresher and no answer more correct. It makes one report **daily**, one chain
**ordered**, and — if ruled in scope — one inversion **visible**. `decision_supported=False` is
untouched. **No producer behaviour changes.**
