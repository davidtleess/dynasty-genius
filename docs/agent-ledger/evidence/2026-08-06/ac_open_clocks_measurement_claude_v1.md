# The two open A-C source clocks — measurement attempt

**Author:** Claude Code, implementing lane · **Layer:** Layer 1 (ingest) inventory
**Scope:** the only two items Codex left holding A-C open — **N1–N8 PlayerProfiler** and **N19's
Sleeper endpoint families** source-publish cadence. Codex bounded the next catalog review to exactly
this evidence, so this artifact is produced *before* any catalog edit.

**Nothing here moves a checkbox, edits the catalog, opens a capture, or authorizes a job.**

---

## 1. N1–N8 PlayerProfiler — **UNMEASURABLE from held evidence.** Not merely unmeasured.

**Probe (rerunnable):**

```bash
.venv/bin/python3.14 -c "import sqlite3;c=sqlite3.connect('app/data/playerprofiler.db');\
print([r[0] for r in c.execute('SELECT DISTINCT ingested_at FROM pp_capture')]);\
print([r[0] for r in c.execute('SELECT DISTINCT ingested_at FROM pp_pbp_capture')])"
```

**Result — ~~the entire store is ONE ingest session~~ *(C1)* and ~~exactly FOUR runs~~ *(E1)*, both
WITHDRAWN. At least SEVEN executions are evidenced** — the **four latest marker runs** plus **three
earlier content-changing applications**. My first version treated three `pp_capture` timestamps as
one session and ignored that PBP ran nine hours later; my C1 fix then replaced one wrong count with
another, because a marker run and a content-changing application are **different executions** and I
counted only one of each pair:

| Canonical stream | `ingested_at` (DB ledger) | Status marker `started_at` → `finished_at` |
| :-- | :-- | :-- |
| `player_season` + `medical_history` | `03:46:48.184631Z` | `03:47:21.973024Z` → `03:47:35.370993Z` |
| `roster_week` | `04:19:20.706807Z` | `04:19:20.706807Z` → `04:19:57.889702Z` |
| `gamelog_week` | `04:36:13.117644Z` | `04:37:53.944178Z` → `04:38:30.277860Z` |
| `pbp` | `13:29:49.752376Z` | `13:36:26.369514Z` → `13:36:41.254502Z` |

**The claim that is sufficient AND correct *(E1-corrected)*:** there is **one held CONTENT vintage
per canonical stream**, and **no ADEQUATE same-stream observation series from which a provider
publication cadence could be derived.**

**"No time series" was too strong and is withdrawn.** Observations *do* exist for three streams — an
earlier content-changing application followed by a later `unchanged` marker run is a **two-observation
sequence of the same content**. They cannot yield a cadence for a reason that needs **no assumption about the
provider at all** *(F2)*: they are **three two-point, sub-seven-minute no-change intervals** — too few
and too narrowly spaced to infer a recurring rhythm, so **their no-change result is non-diagnostic**.
*(My first version said the intervals were "far shorter than any plausible provider publication
rhythm." **That invents a minimum provider interval no source establishes** — API and web content can
change asynchronously and at any spacing. The conclusion never needed the invented bound, which is
what made it worth deleting rather than defending.)* **`roster_week` has no second evidenced run at all.**
**One distinct content vintage does not mean one observation** — that conflation is exactly what E1
caught.

**⛔ MY "NEW FINDING" HERE WAS FALSE AND IS WITHDRAWN IN FULL *(D1)*.** I claimed the two records
"disagree about when the same run happened" and called it a provenance defect needing repair.
**They are not describing the same execution, so there was nothing to disagree about.** Withdrawn:
"same run", "disagree", and the remediation claim.

**The mechanism, which I should have read before asserting a defect — verified at `file:line`:**

- `src/dynasty_genius/playerprofiler.py:453-454` — `apply_block` compares a content digest and
  **`return "unchanged"` BEFORE it writes `pp_capture`**. A no-op re-run therefore leaves
  `ingested_at` at the last *content-changing* application.
- `src/dynasty_genius/playerprofiler_pbp.py:410-413` — the identical guard: on a `source_sha256` +
  `mapping_version` match it sets `"unchanged"` and `continue`s before any write.
- The markers confirm it: `gamelog`, `pbp` and base/player report **every block `unchanged`**;
  **`roster_week` reports `inserted`** — which is exactly why roster is the one stream whose two
  timestamps match to the microsecond.

**The correct, measured semantics — recorded as a fact, NOT a defect:**

| Record | What it means |
| :-- | :-- |
| status marker `started_at`/`finished_at` | the **latest execution**, content-changing or not |
| `pp_capture` / `pp_pbp_capture` `ingested_at` | the **last content-changing application** |

Both are correct and they answer different questions by design.

**Consequence for the execution count *(D1, extended by E1)*:** "four separate manual runs" is **not
a complete execution count**. At least **seven** executions are evidenced — the four latest marker
runs plus the three earlier content-changing applications whose `ingested_at` precedes their marker.
**Those three pairs are also the only repeat observations we hold, and their 33–396s spacing is why
they cannot yield a cadence.** The inventory-relevant fact is unchanged: **one held CONTENT vintage
per canonical stream.**

**Miss accounting (`02` §Falsification #6).** I inferred a defect from a timestamp mismatch **without
reading the code path that produces the timestamps.** The mismatch was real; the defect was invented
to explain it. This is the same shape as the `static_pinned` error earlier today — a plausible reading
asserted before the mechanism was checked — and it is the second time in one session that stating a
claim precisely enough to be checked is what got it killed.

**Conclusion.** A cadence is a property of **two or more observations of the same thing at different
times**. We hold **one CONTENT vintage per stream**, and the only repeat observations are the three
33–396s pairs above — **present but inadequate**, which is a different statement from absent. The
timestamps we do hold are **our capture/execution events, not the provider's publications** —
treating them as a publish rhythm would be the exact R3 error already accepted as a finding for
N19 (T2).

**Therefore the honest catalog value is not "unmeasured pending effort" but "UNMEASURABLE from held
evidence."** Distinguishing these matters: the first implies someone merely has to look; the second
says **the held observations are INSUFFICIENT, and an adequate governed observation series must be
created** *(F1 — this read "the observation does not exist and must be created", which contradicts
E1's own finding that three repeat observations do exist. The absent object is an **adequate
series**, never the observations)*.

**What measuring it would require — designed, NOT proposed for execution:** repeated retrieval of the
same PlayerProfiler resource on a fixed clock, with content hashing and change detection across at
least two intervals. **That is a forward capture against a source classified `blocked`** (automated
acquisition blocked pending sanctioned-access, legal and reliability proof). **It needs David's word
and is not opened here.**

---

## 2. N19's Sleeper endpoint families — **PARTIALLY MEASURABLE, and measured.**

N19 itself is a single 2026-07-19 capture, so it has the same one-vintage problem. **But N18 reads
the same upstream families daily and retains 22 snapshots**, giving 21 consecutive intervals.

**Probe (rerunnable):** hash each top-level section of
`app/data/league_runtime/runs/*/snapshot.json` and count intervals where the hash changes.

**Window: 22 snapshots, 2026-07-16 → 2026-08-06, 21 intervals — entirely OFF-SEASON.**

| Section | Changed | Rate | Reading |
| :-- | --: | --: | :-- |
| `players` | 21/21 | 1.00 | **Genuine daily churn.** Last interval, **keyed by `sleeper_player_id` *(C3)*: 0 IDs removed · 2 added · 36 shared IDs whose row content changed**; `total_players` 12,209 → 12,211. *(My first version reported "36 only earlier / 38 only later", which is a **full-row symmetric difference** — it conflates a changed attribute on an existing player with a player entering or leaving the universe. Two different facts, and the row-difference number cannot distinguish them.)* |
| `league` | 21/21 | 1.00 | **⚠ MISLEADING WITHOUT THE DETAIL — the ONLY key that ever changes is `daily_waivers_last_ran`**, a Sleeper-side daily counter. **League configuration itself did not change once in 21 intervals.** Reporting "league changes daily" would be true and useless |
| `coverage` | 13/21 | 0.62 | **OUR derived metric**, not an upstream family — it moves when `players` moves |
| `rosters` | 9/21 | 0.43 | Genuine |
| `draft_state` | 6/21 | 0.29 | Genuine |
| `users` · `future_picks` · `defaults` | 0/21 | 0.00 | No change in the window (`future_picks` is derived) |
| `lineage` | 21/21 | 1.00 | **Provenance hashes OF the upstream payloads** — a valid *indicator* that upstream changed, not an independent family |

### Boundaries — each one narrows the claim

1. **This measures the NORMALIZED snapshot, not raw endpoint bytes.** The evidence is **asymmetric**:
   a normalized change **proves a relevant input changed**; normalized **no-change does NOT prove raw
   endpoint stability**, because normalization can mask a difference. **The raw stability rate is not
   established by anything here.** *(C2 — my first version called `0.00` "an upper bound on
   stability". That is the wrong quantity: `0.00` is an **observed normalized change rate**, and a
   change rate is not a bound on stability at all. The correction matters because the wrong phrasing
   would license reading `0.00` as evidence of a static source.)* This is the same absent-raw-replay
   gap the catalog already records against N18.
2. **The window is 22 days and entirely off-season.** In-season rates for `rosters`, `draft_state`
   and `players` will differ. **Do not extrapolate a season-round cadence from it.**
3. **N19 covers families N18 does not** — matchups, and per-endpoint drafts/traded-picks histories.
   **For those there is genuinely no observation series of any kind** — not merely an inadequate one —
   and this measurement says nothing about them.
4. **A change rhythm is not a publish cadence and not a job clock** (R3). Nothing here proposes a
   local schedule.

---

## 3. What this does and does not do to A-C

- **N19:** moves from a blank `UNVERIFIED` to a **measured, bounded, off-season change rhythm for the
  families N18 covers**, with the families it does not cover explicitly still open.
- **N1–N8:** moves from `UNVERIFIED` to **`UNMEASURABLE from held evidence`** — precisely: repeat
  observations **exist but are inadequate** (three pairs spaced 33–396s; `roster_week` has none), so
  no provider publication cadence is derivable *(E1 — "no observations" would be the wrong reason for
  the right classification)*. The measurement that would resolve it is designed and its authorization
  gate named.
- **⛳ C PASS RULING RECEIVED — N19 REMAINS OPEN.** I asked; the reviewer ruled against the reading
  most favourable to me. §6A requires an **independently verified source-publish field, or an
  evidenced `N/A`/`not scheduled`**; `UNVERIFIED` stays open. This artifact measures a **bounded
  off-season NORMALIZED CHANGE RHYTHM, which is not a source-publish cadence**, and has **no time
  series at all for N19-only families**. Publication is **applicable**, so `N/A` is not available
  either. **The catalog may record the bounded facts, but the source clock stays OPEN.**
- **Neither clock is closed and no checkbox moves.**

**H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**

---

## 4. Disposition — Codex review v2, C1–C3

**Review:** `docs/agent-ledger/evidence/2026-08-06/pr157_post_merge_and_open_clocks_review_codex_v2.md`
SHA-256 `cc38b9d784505647bad08fee6ce1f9df9bf6f266a25da9342d2321df8bc77d4b`

**All three ACCEPTED, none contested. Each was reproduced against the repo before acceptance.**

| # | Finding | Disposition |
| :-- | :-- | :-- |
| **C1** | "one ingest session" not established — four separate runs | **ACCEPTED, reproduced — and this row is itself SUPERSEDED BY E1.** ~~Four runs across ~10 hours~~ · ~~no same-stream series exists~~. The corrected statements are **≥7 evidenced executions** and **no ADEQUATE observation series**. Left visible rather than rewritten, because a disposition row that silently acquires a later correction is how a review trail stops being auditable |
| **C2** | `0.00` is an observed normalized change rate, not stability | **ACCEPTED.** Boundary rewritten. **A change rate is not a bound on stability**, and the old phrasing would have licensed reading `0.00` as evidence of a static source |
| **C3** | 36/38 is full-row symmetric difference, not ID difference | **ACCEPTED, reproduced.** Keyed by `sleeper_player_id`: **0 removed, 2 added, 36 shared-changed.** Grain now stated explicitly |

**Codex independently reproduced** every Sleeper section-change rate, confirmed `players` 21/21 and
`rosters` 9/21 are not list-order artifacts, and confirmed `league` changes only at
`settings.daily_waivers_last_ran`.

**Unchanged by this round:** **neither source-publish clock is closed**, no catalog edit has been
made, and no checkbox has moved. **H2 QB rushing remains a registered hypothesis UNDER TEST with no
result.**

### D1 — Codex recheck v3

**Review:** `docs/agent-ledger/evidence/2026-08-06/ac_open_clocks_recheck_codex_v3.md`
SHA-256 `32e3624dbc52b1f118987565dfaa8ffd4db6cc3bfdd4f712ced014b640a375ac`
**C1–C3 confirmed correctly repaired** at pin `40b8ceab…`.

| # | Finding | Disposition |
| :-- | :-- | :-- |
| **D1** | The timestamp-semantics finding is **false** — the records describe different executions | **ACCEPTED AND WITHDRAWN IN FULL, after independently verifying the refutation at `playerprofiler.py:453-454` and `playerprofiler_pbp.py:410-413`, and confirming the marker block statuses.** A finding I published gets the same rigour on the way out as on the way in. Replaced with the correct semantics and the corrected ≥7 execution count |

**Standing after this round:** **neither source-publish clock is closed**; **N19 stays OPEN by the
reviewer's ruling**; no catalog edit made; no checkbox moved. **H2 QB rushing remains a registered
hypothesis UNDER TEST with no result.**

### E1 — Codex recheck v4

**Review:** `docs/agent-ledger/evidence/2026-08-06/ac_open_clocks_recheck_codex_v4.md`
SHA-256 `b37d2bc151ef12eb5b0fa8889cd3d74276a5a779b14c37c155548e889bd8afd3`
**D1 withdrawal and the N19 C ruling confirmed correct** at pin `609eee95…`.

| # | Finding | Disposition |
| :-- | :-- | :-- |
| **E1** | §1 still said "exactly four runs" and "no same-stream time series", contradicting D1's ≥7 executions | **ACCEPTED, all three repairs.** `four` → **≥7 evidenced executions**; "no time series" → **"no ADEQUATE observation series"**, naming the three 33–396s repeat intervals and roster's absent second run; the C1 disposition row **visibly superseded rather than rewritten** |

**Why E1 existed at all — worth recording.** My D1 repair fixed the paragraph the reviewer pointed at
and **left the section above it asserting the superseded count.** That is the **stale-by-edit** shape
from catalog §5, committed *inside a correction to a different instance of the same defect family*.
**A fix is not complete until the whole document agrees with it** — the post-fix sweep exists for
exactly this, and I did not run one after D1.

**Standing:** **neither source-publish clock is closed**; **N19 stays OPEN**; no catalog edit; no
checkbox moved. **H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**

### F1–F2 — Codex recheck v5

**Review:** `docs/agent-ledger/evidence/2026-08-06/ac_open_clocks_recheck_codex_v5.md`
SHA-256 `362cf3c245384e9d9595d47637ba49435ea95319d1e82582550df6b4417789d7`
**E1's three repairs confirmed correct** at pin `ed0814b9…`.

| # | Finding | Disposition |
| :-- | :-- | :-- |
| **F1** | "the observation does not exist and must be created" contradicts E1 | **ACCEPTED.** The absent object is an **adequate observation series**, never the observations. Corrected to "held observations are insufficient; an adequate governed series must be created" |
| **F2** | "far shorter than any plausible provider publication rhythm" invents a minimum provider interval | **ACCEPTED, and the sentence is deleted rather than softened.** No source establishes a lower bound on provider change spacing, and content can change asynchronously. The conclusion **never needed it**: three two-point, sub-seven-minute no-change intervals are **too few and too narrowly spaced to infer a recurring cadence**, so their no-change result is **non-diagnostic** |

**What F1 and F2 have in common, and why they arrived together.** Both are **surplus rationale** —
reasoning added to make a correct conclusion feel better supported, which instead attached an
unsupported claim to it. F1 overstated absence; F2 invented a provider property. **The classification
`UNMEASURABLE` was right in both versions; twice the argument for it was doing work the evidence did
not authorise.** The failure mode is not a wrong answer but a **right answer carrying uncited freight**
— and the freight is what a later reader would cite.

**Standing:** **neither source-publish clock is closed**; **N19 stays OPEN**; no catalog edit; no
checkbox moved. **H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
