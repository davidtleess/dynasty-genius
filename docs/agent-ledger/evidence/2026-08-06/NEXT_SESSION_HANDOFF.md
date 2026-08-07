# NEXT SESSION — Layer 1 handoff

**Written 2026-08-07 by Claude Code at David's instruction.** Read this AFTER the CLAUDE.md
bootstrap reads, not instead of them.

---

## 0. THE RULE THAT COST THIS SESSION MOST — read before writing anything

**A state assertion true when written, left standing after the fact changed.** It recurred all
session in six distinct disguises. The register is catalog §5; the new ones this session added:

| Shape | Example |
| :-- | :-- |
| **Stale by edit** | fixed a cell, left the prose citing it |
| **Stale by the clock** | published a growing store's row count as a fixed property |
| **Stale by position** | wrote "the row above" — an insertion made it below |
| **Stale by publication** | said "N commits unpushed"; David pushed between writing and reading |
| **Measured the wrong thing** | ran `find` on one path, reported it as another (twice) |
| **Invented, never true** | asserted a commit was "already on origin" to justify a decision |

**Two mechanical defenses, both earned the hard way:**

1. **Never state a total, count, ahead-count, or HEAD in a committed document.** Named SHAs are past
   facts and stay true. Counts come from a probe: `git rev-list --count origin/main..HEAD`.
2. **When you edit with a script, assert every replacement applied and exit non-zero on a miss.**
   Python `str.replace` returns the input unchanged on a missed anchor. A section was cited in six
   places while never existing, because a script printed success unconditionally.

**And: verify another lane's fact before repeating it.** Gemini reported a LaunchAgent that does not
exist; I wrote it into the catalog within the hour. Its own two reports contradicted each other.

---

## 1. FIRST TASK — the F1–F7 repair

**Codex returned NOT CLEAR on the steps 1–3 batch.** This is the only queued work.

- **Review artifact (committed, start here — do NOT re-derive it):**
  `docs/agent-ledger/evidence/2026-08-06/ac_steps_1_3_batch_review_codex_v1.md`
  SHA-256 `830d993cf24bb187578496d415d951e6301dd0941f773756aa45ff1f71f569ec`
- **Reviewed catalog pin:** `363c2609a9e7561416cd20e48bec2105c10b569d343a8e55bca5a387484a8b45`
- **Deliverable:** ONE written F1–F7 disposition + ONE reconciled fresh batch pin, routed to Codex as
  a single batch. **No §1 checkbox moves until that batch clears.**

**Four findings I already accept — do not re-litigate, just repair:**

- **F6** — §6C says R7/classes are open; §6D is *titled* complete and its body says open. **My own
  sections contradict each other.** Reconcile at source, not with a note beside them.
- **F1** — I withheld `automatic_active_verified` from N18 citing *no raw replay*. That is a
  **quality** defect; the field measures **operational health**. Different axes. N18 has current
  ok/ready markers, 22 successful runs, an empty error log, registered freshness, and a loaded job.
- **F1/F5** — I classed B15–B19 as `blocked`. They are **running** (`automatic_active_health_unverified`);
  it is their canonical *replacement* that is a candidate. I conflated **current** with **target** state.
- **F7** — §6B.3's as-of rule for growing stores is sound; I attached it to stores the same catalog
  calls manual-only. **Right rule, wrong membership.**

**Verified before handoff:** F4 is real — `N14` appears in §6D only inside `N12/N13 + N14b`; it has
no row of its own.

**What Codex confirms HOLDS** (do not disturb): FantasyCalc count/provenance and its
`acquisition defect` classification · the 8-registrations / 8-loaded-jobs **non-identical set** ·
FantasyCalc `health_unverified` · **leaving B20–B24 open rather than inventing facts.**

---

## 2. STATE — verify each from the repo; nothing here is a substitute for a gate run

- **`origin/main`** carries the full Layer 1 catalog: A–C closure matrix (§6A), source-route
  dispositions (§6B), automation classes + verified freshness registry (§6C/§6C.1), R7 states (§6D),
  cadence in three separate clocks (§6E), and the §H answer.
- **PR #157** — CH1, open, **both checks passed** (Frontend 49s · Python 3m15s). **MERGE IS UNGRANTED.** *(Do not trust a mergeable flag copied from here — GitHub recomputes it; read it live.)* Its CI verdict
  is on the **proposed integration**, never on the raw commit; the workflow triggers cannot give a
  raw-commit verdict.
- **CH1 branch** `fix/ch1-per-stream-season-isolation` — code `c129fa2`, docs `bc18f8f`.
- **⛔ WIRE FIX — PARKED, NOT CLEAR, on David's word *"we need to stop this waste of time."***
  `scripts/dg_delivery.py` = `b3247ec8bfff67aace2f6089d08d377ee9d5f72b13eb3da79640f96dcf012c3b`
  `tests/contract/test_wire_health_profile_refresh_red.py` = `fd924eb15a77746e810ade0ed7f1158cfcf9fb4000a73a3df29c260515790591`
  **Do not revert, discard, commit, widen, or resume it without a NEW David word.** Verify these
  hashes are unchanged before and after any push.
- **Backup:** the David-authorized recovery run `20260806T024853Z` completed `sha256_verified: true`
  with zero failures, cross-lane verified, and discharged the §4.3 alarm. **The prior failure's cause
  remains UNDIAGNOSED** — a successful re-run does not evidence a cause.
  **⚠ DO NOT quote a run_id from this document.** The daily job keeps running: within minutes of
  writing the line above, the marker had already advanced to a later scheduled run. **Read
  `app/data/ops/backup_status_latest.json` fresh.** *(This correction is itself an instance of §0's
  "stale by the clock" — caught inside the handoff that warns about it, which is the most honest
  demonstration of the failure mode I can hand you.)*

---

## 3. OPEN, AND WHY EACH IS OPEN

- **A–C is NOT closed.** `B20–B24` are `UNVERIFIED` across all five R7 states **and** their source
  cadence; `N1–N8` PlayerProfiler source cadence is unmeasured. **Codex's SG3 describes B20–B24 and
  it is tempting to write states from that prose — DO NOT. An unmeasured row stays unmeasured.**
- **§H answered provisionally: NO unconditional new external provider is proven necessary.** The work
  is reconciling sources already held. Two conditional candidates only: a live injury/status feed
  (capture Sleeper's own fields and run a coverage test FIRST) and production RAS (NDA unresolved).
- **The PFF aggregation design** — 3 same-scope conflict rows, located. Explicitly **outside** the
  A–C blocking path (David, 2026-08-06). Raw-grain `134,392` is publishable **when labelled**; no
  deduplicated total is defensible.
- **The `01` gap** — no registry entry declares the five direct provider reads. Real under **either**
  A/B outcome.
- **`roster_capacity` and `league_opportunity`** hold registered freshness with **no scheduler**.
  Recorded as fact. **Not a licence to create either job.**

---

## 4. HARD BOUNDARIES — each needs a NEW David word

- **Merge of PR #157.** Push and PR were granted; **merge was not.**
- **Any scheduler, plist, capture, store, consumer migration, Option A build step, or paid call.**
- **Phase B** (catalog / Player 360 / semantic layer / schemas) and **Layer 2 research** remain
  **CLOSED** until A–C is complete and checked off.
- **Do NOT declare the foundation "built enough."** Sequencing is David's alone (`05` §1). A prior
  session asserted it and was corrected.
- **`contracts` landing** needs a separate word AND one export covering all twelve prior streams plus
  contracts.
- **H2 QB rushing is a registered hypothesis UNDER TEST. There is no result. Do not assert it.**
- **Never touch the Studio working directory** (standing wall).

---

## 5. THE LANE LESSON

Across this session the independent lane found roughly forty defects in my work; my own reviews of my
own work found two. **Every artifact that is now trustworthy is trustworthy because a second lane
re-measured a number it had not produced.**

The two things that actually worked: **running a probe before making an argument**, and **a reviewer
willing to withdraw its own passing test** when the harness flattered the implementation — which is
how the worst CH1 defect (an unavailable stream reaching the builder as a crash) was caught.

Route early, route often, and treat a frictionless CLEAR as a yellow flag.
