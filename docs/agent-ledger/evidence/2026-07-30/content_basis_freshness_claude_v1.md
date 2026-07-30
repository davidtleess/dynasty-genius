# Content-basis freshness — David's ruling, what it changes, and the compounding pattern

**Claude Code, 2026-07-30, under TW30-WORD-K.** Two David decisions, relayed by Tower at 11:26.
**Declaration + contract work. No producer touched. Nothing here is a commit request.**

**Layer:** 1–2 (what feeds the product and whether it stays fresh).

---

## §1 — The ruling, and why the consequence is bigger than the answer

**The sleep question is answered: NO.** A daily job is not expected to run while the laptop is
asleep. It runs late, on wake, and that is **accepted, not a fault**. Contract v4 §11 Q1 is closed.

**The consequence he took deliberately: freshness is judged by CONTENT, not by whether a job ran.**
*A run that completes and publishes nothing new is not fresh, whatever its exit status and whatever
its timestamp says.*

**This is not a preference — the alternative was measured this morning and it fails.** A
schedule-basis definition would have reported this product healthy **every morning for 33.8 days**
while the model layer did not move: the job fired daily, exited `ok`, and rewrote the file, so every
schedule-and-exit-status signal was green. The content did not change once
(`mean_abs_value_delta = 0.0`). Full mechanism in `valuation_staleness_diagnosis_claude_v1.md`.

## §2 — The definition

**Three inputs, and "did the job run" is not one of them.**

1. **`content_identity`** — a digest over the artifact's *meaningful* content, excluding
   publication metadata. It must change **iff** meaningful content changed. Republishing identical
   content must produce an identical `content_identity`. *(The estate already has this shape:
   `runtime_sha256`, `pvo_sha256`, `payload_hash`, `source_hash`.)*
2. **`observation_timestamp`** — the vintage of the *data*, not the moment of the *write*. Declared
   per artifact at the finest granularity available.
3. **`expected_change_condition`** — the declared circumstance under which content *should* differ:
   what upstream event, at what real rate of meaningful change, **season-aware** (in-season ≠
   off-season, per the compounding lens in `02`).

**The verdict is one of four, and only one is an alarm:**

| Verdict | Condition | Meaning |
| :-- | :-- | :-- |
| `advanced` | `content_identity` changed | The foundation moved. |
| `unchanged_expected` | identical **and** the declared expected-change condition did not occur | Correct stillness — e.g. no NFL games played since the last run. **Not fresh, and not a fault.** |
| **`unchanged_unexpected`** | identical **while** the expected-change condition DID occur | **The alarm.** The pipeline should have moved and did not. |
| `unknown` | no declared `content_identity` or no declared expected-change condition | **Fails toward disclosure, never toward "fresh."** |

**Three rules that follow, and each one is a defect this morning found:**

- **A publication timestamp may never advance a freshness basis.** `source_as_of` records when the
  write happened; it says nothing about vintage. Today it advanced on a 33.8-day-old baseline.
- **Exit status answers a different question.** `ok` means the run completed. It is evidence about
  the *run*, never about the *content*. A `noop` is a completed run that published nothing — which
  is exactly `unchanged_*`, not `fresh`.
- **Absence of drift is not evidence of health.** A surface that reports only when values *move*
  cannot report a pipeline that has *stopped* moving. The What-Changed suppression rule
  (`what_changed/report.py:178-185`, "Silent-unless-threshold-crossed") is that failure mode in
  code: zero drift is precisely the state it treats as nothing to say.

**`unchanged_expected` vs `unchanged_unexpected` is the whole value of the definition**, and it is
the distinction no current surface can make. Both look identical on disk; they are opposite facts.

## §3 — What this changes in the minimum ingestion contract

Not authored as an amendment — contract v4 has four open blocking findings and no revision is
authorised. Recorded so the revision, when it opens, carries it:

| Contract element | Change |
| :-- | :-- |
| §11 Q1 (laptop asleep) | **CLOSED by David.** Lateness is recorded as a fact; it is not a fault, and it is not the freshness signal. |
| §11 Q2 (`freshness_hours` semantics) | **Demoted, not answered.** Whatever it meant, an interval no longer decides freshness. It may still describe an expected-change *cadence* — an input to §2's third element, not a verdict. |
| §6 stream declaration | Add `content_identity` + `expected_change_condition`; `declared_cadence` stops being a freshness authority. |
| §4 run record | `scheduled_for` vs `started_at` stays (lateness is a recorded fact), and **`content_identity_before` → `content_identity_after`** joins it, so a no-publish run is visible in the record itself. |
| §7 per-check declaration | Every check declares `expected_target_set` (see §4). |
| N2 (zero fails only when zero is unexpected) | Generalises: **`unchanged` fails only when unchanged is unexpected.** Same rule, one layer up. |

## §4 — The compounding pattern David asked for

He framed the SQL re-point as the **first instance of a compounding approach**, not a point fix, and
asked whether aiming our checks at what matters can be made repeatable. It can, and the pattern is
already half-written in the contract:

> **Every check declares its `expected_target_set` — and a check that executes against an empty or
> unexpected target set REPORTS, it does not pass.**

The SQL job is the canonical failure: it audited `resources/`, which holds **zero** `.sql` files,
printed *"passed for 0 SQL file(s)"*, exited 0, and did so daily. **It was not broken — it was aimed
at nothing, and nothing is indistinguishable from clean when the target set is undeclared.** That is
the same shape as `unchanged_expected` vs `unchanged_unexpected` one level down: **absence of
findings is not evidence of compliance, exactly as absence of drift is not evidence of freshness.**

**The repeatable pattern, in three parts:**

1. **Declare the aim.** Every check names the target set it is supposed to cover.
2. **Reconcile expected vs executed.** A run reports what it actually covered; a mismatch is a
   finding, not a silent pass. *(Contract N1.)*
3. **Empty is a report, never a pass.** Zero targets, zero rows, zero findings — each is a fact
   about the check's aim before it is a fact about the estate.

**Instance 1 is the SQL re-point** (§5). **Two further instances are visible and are NOT opened
here:** `pvo_refresh` registered with no timestamp/status field so mtime governs its health, and
capture-health covering **one** enumerated ingestion stream of ≥18. Both are the same defect —
a check whose real coverage is far narrower than its green signal implies. **Named for David's
sequencing, not started.**

## §5 — Instance 1: the SQL governance re-point (executed, bounded)

**David's word: re-point at the real SQL, report-only.** Change made to
`.github/workflows/codex_audit.yml` only:

- **Aim:** `infrastructure/src/sql` + `resources` (4 governed `.sql` files, **including
  `refresh_genius_state.sql`, which rebuilds the source-of-truth table** — the layer-2 artifact that
  put this in scope).
- **Report-only:** `continue-on-error: true`, job renamed **REPORT-ONLY**, plus a run-summary step
  (`if: always()`) so findings are visible without opening a log. **It cannot block CI.**
- **Verified locally before the change and after:** aimed at `resources` → *"passed for 0 SQL
  file(s)"*, exit 0. Aimed correctly → **exit 1, two findings**, both in
  `infrastructure/src/sql/migrations/002_remove_jeanty_nfl_player.sql`: an `anchors` mutation with no
  corresponding `data_driven_override_log` entry, and a `CASE` expression keyed on player-name
  literals. **NOT FIXED, per David's explicit instruction. They route to Tower, then to him.**
- **`refresh_genius_state.sql` is in the aim and produces no finding** — because this auditor polices
  the cliff *number* and is silent on the *prohibition* on encoding a binary cliff at all. **The
  re-point does not touch that layer-2 question, which David has reserved for its own consideration.**
- **The stale retirement note that called this workflow a "KNOWN GREEN NO-OP" is marked superseded
  in place**, with the warning restated in its new form: **a green run of a report-only job is not
  evidence of compliance, because the job cannot fail.**

**Not done, deliberately:** no empty-target-set guard was added to `codex_audit_sql.py`. It is the
right mechanism for §4 part 3 and it is beyond the bounded word given. **Proposed, not built.**
