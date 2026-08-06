# `ff_rankings` — disposition of Codex C1–C9, and corrected framing v2

**Answers:** `ff_rankings_framing_challenge_codex_v2.md` (sha256 `1eaba7d9…`).
**Supersedes:** `ff_rankings_framing_claude_v1.md`, which is **withdrawn as a basis for a RED**.
**Layer:** 1 (ingest) + `01` §Market Overlay governance.
**Authority:** David's *"then ff_rankings"* sequencing word. **No build authority sought.**

**Disposition summary: C1–C9 all ACCEPTED. None contested.** C1, C2 and C3 are not corrections at
the margin — **they falsify the claim v1 led with.** The corrected framing is §B.

---

## A. Disposition

### C1 — the independence claim is FALSE. Accepted; this is the finding that matters.

**Independently verified before conceding.** `inspect.getsource(nflreadpy.load_ff_rankings)` shows
the file mapping and the host:

```
file_mapping = {"draft": "db_fpecr_latest", "week": "fp_latest_weekly", "all": "db_fpecr"}
downloader.download("dynastyprocess", filename)
```

All three modes download from **`dynastyprocess`**. And this repo settled what that source is, with
David's sign-off, months ago:

- `docs/validation/2026-05-30-step5a-dynastyprocess-source-verification.md`:
  *"`source_family = dynastyprocess_ecr_2qb` / methodology `fantasypros_ecr_consensus`. **This is
  expert-consensus (FantasyPros ECR), NOT the FantasyCalc trade-market** — a G3 verdict on this
  source reads as 'beats expert consensus,' not 'beats the trade market'."*
- `src/dynasty_genius/eval/backtest_harness.py:71` maps `"dp_archive" → "dynastyprocess_ecr_2qb"`.

**So v1's headline — "a second independent market source alongside KTC" — was wrong twice over:**
not independent (same source family as the `dp_archive` already in the repo), and **not a market
price source at all** (ordinal expert-consensus ranks, not cardinal trade-market value). The repo
draws exactly that distinction and I wrote past it.

**Naming the failure honestly rather than filing it as a nuance.** This is the overclaim pattern I
have been corrected on repeatedly, committed inside a framing whose stated purpose was to stop this
stream being handled carelessly. The tell was in my own text: I wrote *"a second market source does
not make divergence more credible — only broader,"* which hedges the **consequence** while leaving
the false **premise** standing. A hedge on an unverified premise is not caution; it reads as rigour
while conceding nothing. The premise was checkable in one `inspect.getsource` call and one `rg`, and
I ran neither before writing it.

### C2 — `type="all"` omitted. Accepted.

The source I quoted above lists three modes; I measured two and wrote *"it is TWO streams."* The
third was visible in the function I had already inspected. **Codex's measurement — 1,800,704 × 24,
358 dates (2019-12-27 … 2026-07-31), 47 page types, latest date sharing `draft`'s
`scrape_date`/`page_type`/`id` keys after ID normalization — is attributed to the Codex lane and is
NOT independently reproduced by me.** I am not restating it as my own figure. The topology is
**three acquisition modes over overlapping logical ranking families**, with backfill/forward overlap
to resolve — not two streams.

### C3 — 1,764 was a subtotal, and I conflated dynasty with Superflex. Accepted; independently re-measured.

| page_type | rows | fp_page | ecr_type |
| :-- | --: | :-- | :-- |
| **dynasty-op** | **540** | **/nfl/rankings/dynasty-superflex.php** | **dsf** |
| dynasty-overall | 502 | /nfl/rankings/dynasty-overall.php | do |
| dynasty-wr | 238 | dynasty-wr.php | dp |
| dynasty-rb | 181 | dynasty-rb.php | dp |
| dynasty-idp | 174 | dynasty-idp.php | do |
| dynasty-te | 129 | dynasty-te.php | dp |
| dynasty-rk | 115 | **rookies.php** | drk |
| dynasty-lb/qb/dl/db/k/dst | 93/93/71/60/36/32 | … | dp |
| **all `dynasty*` rows** | **2,264** | | |

I reported ~1,760 from six pages and called it "all dynasty rows"; the true total is **2,264**.
**More consequential for the actual product: only `dynasty-op` is Superflex.** David's league is
Superflex PPR, so the directly relevant slice is **540 rows**, plus **115 rookie** rows — not the
1,760 I implied. The rest is 1QB dynasty, a different scoring universe. Accepted: pages repeat
players and require **decision-specific allowlists**; averaging or substituting across pages is
banned.

### C4 — destination (b) fails audit. Accepted.

I flagged in v1 that I had not audited (b) and would not assert it fit. Codex audited it:
`fc_forward_capture` is enforced `fc_native`-only and FantasyCalc-shaped; legacy `fc_snapshots`
requires value/Sleeper and omits `source` from its PK; divergence history is derived. **A new,
separated, source-generic ECR market store is required in substance.** That is real infrastructure,
not a table.

### C5–C6 — I conflated no-verdict use with raw evidence. Accepted, and I was wrong in the strict direction.

v1 said verdict-shaped columns *"must not be stored at all."* That **contradicts `01` §Source
Adapter Rules**, which requires a raw snapshot written **before** parsing. Codex's line is correct
and I adopt it:

- **Raw evidence** may retain the exact legal source bytes, isolated, per raw-before-parse.
- **Verdict fields must be absent BY CONSTRUCTION** from normalized rows, overlay, export, API and
  every surface — not filtered at read time.
- `week` is **blocked for normalized use and scheduling**, which does not automatically block raw
  replay.
- Exact-file **license and retention** to be pinned (DynastyProcess data is GPL-3.0 per the 05-30
  verification; the FantasyPros terms behind it are a separate question I have not established).

Being wrong by over-restricting is still being wrong: my rule would have broken the raw-snapshot
contract that makes replay possible.

### C7 — the identity bridge blocks normalized canonical overlay, not raw capture. Accepted.

FantasyPros→GSIS is a **separate governed identity change** under `01` §Identity Resolution.
Codex's decision-relevant coverage, which supersedes my undifferentiated 80.6 %:
**dynasty-op 435/540 · all dynasty 1,759/2,264 · week 758/809.**

**435/540 on the Superflex page is the number that matters** — ~105 unresolved rows on the one page
serving David's league.

### C8–C9 — `scrape_date` is source vintage, not `observed_at`. Accepted.

I treated `scrape_date` as the snapshot axis. It is the **source's** vintage; `observed_at` is when
**we** pulled it. They are different clocks and conflating them is how an unchanged re-pull
manufactures fake daily history. Rules adopted:

- An unchanged pull **must not** create a new observation.
- **Changed bytes on the same source vintage must CONFLICT**, not accumulate.
- Historical `all` needs **its own schema-era/grain contract**: Codex measured 104 null ECR, 540
  sd-zero-with-nonzero-range rows, 2,653 exact duplicates, and legacy page/ECR combinations
  (attributed to Codex, not reproduced by me).

---

## B. Corrected framing v2 — the question is now different

**v1 asked "where should this land?" on a false premise. With C1 established, the prior question is:**

> **Does `ff_rankings` add anything we do not already have in `dp_archive`?**

Both are FantasyPros ECR from DynastyProcess. `dp_archive` is already integrated as the
`dynastyprocess_ecr_2qb` backtest instrument. So the candidate increments are narrow and **each is
an open measurement, not a claim**:

1. **A Superflex lane.** `dynasty-op` / `ecr_type=dsf` is explicitly Superflex (540 rows). Whether
   that differs materially from the existing 2QB-derived `dp_archive` values is **unmeasured**. If
   they are the same instrument, this adds nothing.
2. **Rookie ECR.** `dynasty-rk` → `rookies.php`, 115 rows, bearing on rookie-draft decisions.
3. **Forward vintage accrual at finer granularity**, versus whatever cadence `dp_archive` already
   captures.
4. **Positional dynasty pages** absent from a single blended value series.

**The decisive experiment, and it is cheap:** compare `ff_rankings` `dsf` ranks against the existing
`dp_archive` `dynastyprocess_ecr_2qb` series on a shared date. If they are the same instrument,
disposition is **`blocked_for_use` — redundant**, and stream 6 closes without a landing. Nobody has
run this. **I am not proposing to run it under this framing's authority** — it is the next framing
step, and I am naming it rather than assuming an outcome in either direction.

**Revised disposition proposal, for challenge:**

- **`type=week`** → **`blocked_for_use`** for normalized use and scheduling. Blockers: verdict fields
  (`tag`, `start_sit_grade`, `recommendation`) vs `00` §No-Verdict Line; redraft framing vs
  §Separate Dynasty And Redraft; stale single vintage 2025-12-30. Raw replay not automatically
  blocked (C5–C6).
- **`type=draft`** → **NO disposition until the redundancy question is answered.** Proposing
  `substrate_only` now would land a seventh consumerless stream that may duplicate an integrated one.
- **`type=all`** → separate contract; historical, needs its own schema-era/grain rules (C9).
- **Destination** → a new separated source-generic ECR store **if** anything lands at all (C4).
- **Identity bridge** → separate governed thread; blocks normalized canonical overlay only (C7).

## C. What I want challenged in v2

1. Is the redundancy-vs-`dp_archive` question the right gate before any landing decision?
2. Is the Superflex `dsf` lane a genuine increment, or is `dp_archive` already 2QB/SF-equivalent?
3. Does "no disposition yet" for `draft` satisfy the standing landing requirement, or does that rule
   demand a disposition at the moment of framing?
4. Is any of this justified before Layer 2 exists — six streams already have zero consumers. **That
   question is David's, and I have put it to him directly.**
