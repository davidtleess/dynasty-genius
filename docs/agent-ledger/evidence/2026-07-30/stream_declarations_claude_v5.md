# Stream Declarations — v5 (corrections to v4; the enumeration itself is unchanged where uncontested)

**Claude Code, 2026-07-30, written 12:1x ET.** David's word: *"answer 1: do the enumeration."*
**v1 (7) · v2 (5) · v3 (6) · v4 (6) — 24 findings, all accepted, none challenged.**
Priors on disk, hashes **re-verified 2026-07-30 12:10 ET**: v1 `7bdd5653…82407e`, v2 `c951883c…1a840a`,
v3 `7297f09b…4962a`, v4 `4e238259…c9d858`. **v4 remains the base; this version carries its corrections
and everything not corrected here stands as v4 states it.**

**Two standing rules from today apply to this document and are stated at the top because I broke both:**

1. **An uncleared artifact never governs.** v4 §199-202 said an uncleared artifact of mine "governs."
   It does not. **David's word governs; a cleared artifact may bind; a draft binds nothing however
   well argued.**
2. **Anchoring is a requirement.** Every observation carries a measured clock time. No windows.

---

## §0 — Corrections to v4

| # | v4 defect | Correction |
| --: | :-- | :-- |
| 1 | `feature_refresh` trigger listed "manual via orchestrator" | **FALSE — removed.** `refresh_league_intelligence.py:23-34` PHASE_STEPS names 17.1, 17.2, 21, 17.3, 18.3, 17.4, 17.5 — **`run_feature_refresh.py` is not among them**, and a repo-wide scan finds no other caller. I generalised league capture's orchestrator path onto a pipeline that has none. |
| 2 | "five paths leave NO durable record" | **Overstated — corrected in §1.** |
| 3 | The realized `OSError` guarantee | **Corrected in §2.** |
| 4 | Exclusive "request only" and exact "five request-bearing streams" under a graph declared incomplete | **Corrected in §3.** |
| 5 | "content_basis_freshness_claude_v1 governs" | **Corrected — an uncleared artifact governs nothing** (top of this file). |
| 6 | v3 prior's on-disk state unanchored | **Corrected — all four prior hashes re-verified at 12:10 ET** (header). |

## §1 — The silent-failure inventory, corrected

**What v4 claimed:** five paths leave **no durable record**. **What is true:** every scheduled job's
plist sets `StandardOutPath` and `StandardErrorPath` (verified in
`ops/launchd/com.davidleess.dynasty-model-pvo-refresh.plist`, read 12:07 ET), so a propagating
exception lands as a traceback in a log file. **Rows 1–4 are therefore not recordless.**

**The accurate claim, and it is still the finding:** rows 1–4 leave **no durable STRUCTURED status,
report or marker** — nothing a health surface, a consumer, or another agent reads. A traceback in an
append-only text log is a record no machine consults.

| # | Pipeline | Failure | Corrected status |
| --: | :-- | :-- | :-- |
| 1 | league capture | non-`CaptureError` from the Sleeper fetch | stderr log only; **no status marker** |
| 2 | feature refresh | upstream `ConnectionError` | stderr/stdout log only; **no report** |
| 3 | FC capture | non-httpx exception from `fetch_json` | stderr log only; **no report** |
| 4 | realized outcome | exception in `_resolve_season_week()` | stderr log only; **no marker, no report** |
| 5 | realized outcome | **termination between ok-marker and publish** | **genuinely recordless — and worse: the marker asserts `status=ok` for a scorecard that does not exist** |

**Row 5 remains the sharpest and is unchanged by this correction.**

## §2 — The realized acceptance guarantee, corrected again

v4: the guarantee "holds for `OSError`-class failures." **Still an overclaim.** Publish-failure
recovery depends on a **successful marker rewrite** — and if that rewrite itself fails, the code
raises `MarkerWriteError`. **So the guarantee holds only when the marker rewrite succeeds**, which is
the same class of assumption as the original defect: a truth surface relied upon while it may itself
be unwritable.

## §3 — Trigger sets, without exclusivity or exactness

v4 removed completeness claims from the counts and then kept exclusive labels ("request only") and an
exact tally ("five request-bearing streams") **derived from a graph the same document calls
known-incomplete.** Corrected:

| Streams | Triggers OBSERVED (never "only") |
| :-- | :-- |
| 2, 4, 5, 7 | scheduled · manual |
| 1, 8, 9 | scheduled · request · manual |
| 3, 6 | scheduled · request · manual |
| 10, 11 | request **observed**; no scheduled or manual path found by my traversal |

**At least five streams carry a request-time path** (1, 3, 6, 8, 9). *At least* — the traversal that
produced this table has already missed a path twice, so the number is a floor and the labels describe
what was observed, not what exists.

## §4 — Everything else stands as v4 states it

The unit floors, the four filled pipeline forms, the consumer graph and its declared blind spot, the
freshness mechanics, the contract-v4 arithmetic (two of six addressed, four open), and the declared
unknowns are **unchanged and uncontested by this review round**. §5 of v4 is amended only by rule 1
above: the content-basis freshness definition is **David's ruling**, and the artifact describing it
is a draft that binds nothing until cleared.
