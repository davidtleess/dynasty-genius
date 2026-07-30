# Loud-stop design + telemetry mismatch report — TW30-WORD-Z

**Claude Code. Written 2026-07-30 13:15:50 EDT** *(machine clock, pasted).*
**David's word, verbatim:** *"stop the chain on failure."*
**Design + mismatch report. No plist authored, nothing loaded, no producer touched.**

---

## §1 — The decision, and the cost he accepted

**A failed step halts the chain.** Downstream artifacts are not built on a broken upstream.

**Recorded because he was told and chose anyway:** on a failure day **the daily point-in-time capture
does not accrue** — and that accrual is the exact reason Option A was chosen over Option B. **He
traded it deliberately, in one direction, having heard both sides.** It is a decision, not an
oversight. **Nobody may later "fix" it by quietly making the chain continue.**

## §2 — Tower's requirement (Tower's, not David's — challengeable): a stop must be LOUD

**Rationale, which I accept and did not need persuading of:** every instrument caught today failed by
being **quiet**. A chain that halts silently recreates the same disease in a new place — absence of
output read as absence of a problem.

**Design answer — a chain run marker written at START, not only at the end.**

That single choice is what makes the required distinction possible:

| State | How it looks on disk | How it is told apart |
| :-- | :-- | :-- |
| **HALTED-BY-DESIGN** | marker present, `started_at` from **this** run, `status=halted`, `failed_step`, `reason`, `steps_completed` / `steps_skipped` | a run **began** and stopped deliberately |
| **DID-NOT-RUN** | marker's `started_at` is **from a previous run**; no new run record exists | nothing started at all |
| **RUNNING** | `status=running`, `started_at` current, no terminal state yet | distinguishes "in flight" from both |

**Without a start record the two are indistinguishable**, because both present as "no fresh
downstream artifacts." That is the same shape as this morning's findings: **absence of drift is not
absence of movement; absence of output is not absence of a run.**

**Where it must live to satisfy the first condition:** registered in `app/config/report_freshness.json`
with a `timestamp_field`, a `status_field`, and `success_status` — so the health surface **reads it**
rather than the operator discovering the gap. **The registry's existing `status_field` ↔
`success_status` guard applies for free.**

## §3 — MISMATCH REPORT against the pre-registered morning verification

*(`docs/agent-ledger/2026-07-30.md`, telemetry entry 12:58 ET. Tower asked to discover any mismatch
now rather than tomorrow at nine. **There are three, plus one gap.**)*

### 3.1 — HARD MISMATCH: the verification expects two daemons that Option A will not create

Registered SUCCESS criterion: `launchctl list` shows **`com.davidleess.dynasty-league-opportunity`**
as an active daemon. **Under Option A, `league_opportunity` is a STEP IN THE CHAIN, not a labelled
job.** No such label will exist. Registered FAILURE criterion — *"the plist files exist but
`launchctl list` fails to return them"* — **would fire on a correct implementation.**

**The verification would report failure on a working chain.** `roster_capacity` is unaffected: its
cadence is unruled, it stays weekly and separate, so that half of the criterion still holds.

### 3.2 — SERIOUS MISMATCH: the freshness criterion can be satisfied while the defect survives

Registered SUCCESS criterion names `timestamp_field` pointing at a field in
**`universe_pvo_runtime.ready.json`**, *"e.g. `source_as_of`"*.

Two problems, and the second is the dangerous one:

1. **Wrong file.** The `pvo_refresh` registry entry points at
   `app/data/model_capture/pvo_refresh_latest_report.json`, **not** the ready marker. They are
   different artifacts.
2. **`source_as_of` IS THE DEFECT.** It exists in the ready marker (confirmed at the timestamp above)
   and it is **the write-time stamp** that today's diagnosis established **advances on unchanged
   content**. **A change that pointed `timestamp_field` at `source_as_of` would satisfy the registered
   success criterion while preserving exactly the behaviour David authorised fixing.**

The in-scope fix points at **`capture_report.artifact_vintage`** — a **dotted, nested** path, which
the registered criterion ("a valid JSON schema field") may also read as invalid.

### 3.3 — PATH MISMATCH: `feature_csv` is real but two levels deeper than registered

Registered: `pvo_refresh_latest_report.json`'s **`feature_csv.sha256`**. Measured: the field exists at
**`capture_report.provenance.feature_csv`**. The measurement is takeable; **the stated path is not.**

### 3.4 — GAP: the halt distinction is not measured at all

The pre-registration was written at 12:58; **David's stop-on-failure ruling came after it.** Nothing
in the registered measurements distinguishes **HALTED-BY-DESIGN** from **DID-NOT-RUN**.

**So Tower's third acceptance condition is NOT satisfied today.** §2's start-marker design makes it
*satisfiable*, but the verification must be amended to measure it. **Stated plainly, as asked, rather
than assumed away.**

## §4 — What I am NOT doing

Not amending the telemetry lane's pre-registration — **it is theirs, and rewriting another lane's
pre-registered measurements to match my implementation is precisely the bias pre-registration
exists to prevent.** This report goes to Tower; the amendment is theirs to make or David's to rule on.

**No plist authored. Nothing loaded. RED first. Commits remain David's.**
