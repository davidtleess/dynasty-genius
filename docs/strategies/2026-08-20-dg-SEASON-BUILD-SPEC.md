# Dynasty Genius — Season Readiness Build Spec

**Revision 2 · written 2026-08-20 (Thursday) · pressure-test amendments PT-1..PT-8 applied · Kickoff 2026-09-10 20:20 ET · Freeze 2026-09-04 EOD.**

19 committed tickets plus one conditional. 11 build days, of which 10 are allocated. Every path, line number and measurement below was re-verified against the live repo today; the commands are in each ticket.

---

> ## ✅ READY — the three blockers are resolved
>
> Two independent verifiers checked this revision. All three findings are **applied into the ticket
> bodies below**, on David's rulings of 2026-08-20. Nothing is outstanding.
>
> **B1 · SR-09 was going to destroy SR-00 — fixed.** SR-00 adds 11:30/14:00 retries to two plists on
> Day 1; SR-09 step 7 was going to retire **those exact two** on Day 6, silently reverting the
> sprint's cheapest protection with no error and no alert. Two reviewers found this independently.
> **David: *"isn't it obvious that we need put the smoke alarm back up? yes - put it back up."***
> Applied as SR-09 step 7 **b-EXCEPTION**: the chain takes the 09:00 slot only; the two SR-00 plists
> are **edited, not retired** — 09:00 stripped, 11:30 and 14:00 kept, left loaded as retry-only jobs.
> **Four plists retire, not six.** SR-09 cannot close until a live 11:30 retry is observed firing
> after the chain lands; the proof commands are in its verification block.
>
> **B2 · The fabrication guard was one field short — fixed.** `daily_diff.py:354` (`xvar_delta`) was
> guarded; **line 353 (`dvs_pct_delta`) runs the identical `None -> 0.0` path** and was not. Guarding
> one leaves the same ~468-row fabrication armed through the other. **David: *"agreed."*** SR-14 now
> guards **both 353 and 354**; `_float` itself stays unchanged, as it has other callers.
>
> **B3 · SR-18 removed, per David's existing ruling.** One agent reinstated League Activity as an
> in-sprint conditional; the coverage verifier read the decision record, caught the contradiction and
> pulled it back out. League Activity is a **committed deliverable for week 1 of the season (on or
> before 2026-09-17)**, not sprint work. Its ticket body is retained below verbatim as the post-freeze
> spec; the D9 go/no-go checkpoint is cancelled.
>
> ### Applied at the same time (found by the verifiers, non-blocking)
> - **SR-10a step 1 moves to D4**, beside SR-11 — the single `app/config/capture_cadence.json` block,
>   verified clean in git and not among the other lane's four dirty BUILD-3 files. Steps 2-5 stay D7.
>   Without this, detection still lagged risk for `market_divergence_history`, the one store with four
>   measured holes.
> - **SR-09 LANDS by EOD Fri 08-28; it CLOSES on D8** once SR-19 has exercised it against a real
>   refusal. Three live mornings run in between — say both dates, they are not the same milestone.
> - **SR-19 called a flag SR-09 was never asked to build** (`--runtime-override`). Add it to SR-09
>   step 1's CLI contract, or rewrite SR-19 against `--steps-from` with a scratch step table.
> - **SR-10a's external blocker gains a fallback:** if the BUILD-3 lane has not handed over its four
>   dirty files by 09:00 on the scheduled day, pull SR-13 (0.5d, no dependencies) forward and take
>   SR-10a on D9.
> - Corrected inline: the symbol is `_INPUT_RELATIVES` (line 46), not `_DEFAULT_INPUTS`.
>
> **Day budget:** 10.0 committed − 1.5 (SR-18, per David's ruling) = **8.5 days against 11**, leaving
> **2.5 days of slack** across D9-D11. The healthiest margin this spec has carried, and the pressure
> test showed 1.25 days was one surprise from failing.


## Headline

By kickoff David gets, on Day 1 and before anything else, a **same-day retry** on the two jobs that are actually bleeding — a plist edit that recovers the dominant observed failure at near-zero risk. Then a capture chain that runs in dependency order and **fails soft rather than halting wholesale**, an nflverse job pointed at 2026, exit codes that can report failure, the store with four measured holes finally monitored, and — for the first time in this product's life, and **before** the riskiest change rather than after it — a 10:30 notification that names the store and the date when something is missing.

Plus an app that starts on its own, a Morning Room headline aimed at **his own 26 roster movers** instead of league-wide churn he does not act on, a Trade Lab search that stops offering Brock Purdy for "brown", an archive that finally records xVAR after 57 days of nulls **without fabricating 468 model moves the morning it lands**, a guard against the TE constant edit an earlier brief instructed, and the end of the false staleness alarm that fires six mornings out of seven.

**Committed work is 10.0 days against 11. Day 11 is deliberately unallocated** — it is the single surprise buffer, and a hard freeze with zero buffer is how goal 1 fails.

---

## Freeze date

**2026-09-04, end of day Friday.** Hard freeze; after it only Tier 0 changes land — a change without which a capture job does not run or writes wrong data.

The daily chain runs once per calendar day, so confidence in a scheduler change is bought in calendar days, not working hours. Freezing Fri Sep 4 leaves 11 working days (Fri 08-21 → Fri 09-04, verified by counting weekdays) and yields six consecutive unmodified cycles: Sat 09-05 … Thu 09-10.

**Three Tuesdays matter, not one.** Three of the twelve jobs run Tuesday-only — verified with plutil: `league-opportunity-map` `{'Weekday': 2, 'Hour': 9, 'Minute': 35}`; `roster-capacity-audit` and `realized-outcome-scoring` both `{'Weekday': 2, 'Hour': 10, 'Minute': 0}`. **Tue 08-25 and Tue 09-01 are inside the build window; Tue 09-08 is inside the frozen window.** Revision 1 claimed "Sep 8 is the ONLY post-change Tuesday" — true only because of its own sequence, and false the moment the sequence changed. This revision lands SR-09 by end of Fri 08-28, buying a second exercise of the three weekly jobs on **Tue 09-01, inside the window where a finding is still a fix.**

Refusing the freeze to buy four more build days is how goal 1 fails: SR-09 rewires the morning chain and SR-11 adds a new agent, both Tier 2, and a Tier 2 mistake discovered on Sep 11 is a permanent hole in a store whose gaps cannot be backfilled.

One stated exception: pushing commits to origin (SR-01) is not a product change and is not frozen.

---

## WHAT DAVID GETS BY KICKOFF

**Goal 1 — nothing is lost.**
- A **same-day retry at 11:30 and 14:00** on `market-divergence-refresh` and `model-pvo-refresh`, landing Day 1 (SR-00). The dominant observed loss is a prior-date abort — a timing race against a source that never fails — recovered completely from the DB-resident 09:00 snapshot with no network call. Provably a no-op on healthy days.
- One 09:00 job runs the six morning producers **in dependency order with named edges**, so a late start can no longer create a permanent hole and one producer's network flake can no longer take the morning down with it (SR-09).
- nflverse captures 2026 instead of re-downloading 2023-2025 (SR-06). Both new capture jobs can report failure (SR-07). The 13-day transaction gap is recovered (SR-08).
- `market_divergence_history` — the store with four measured holes — is registered and monitored (SR-10a).
- **At 10:30 every morning, a macOS notification names the store and the date when something is missing** (SR-11). It lands on Day 4, **before** the chain rewire.
- The season rollover the six soak cycles structurally cannot exercise is rehearsed by hand before the freeze (SR-19).

**Goal 2 — nothing is wrong.**
- The archive starts recording xVAR after 57 days of nulls — **and does not fabricate ~468 model moves on the morning it lands** (SR-14).
- Trade Lab stops showing results for the query you typed three characters ago (SR-15).
- A contract test blocks the TE constant edit that would introduce an 8.4% distortion where none exists (SR-13).

**Goal 3 — something is useful.**
- The app starts on its own and survives a reboot (SR-12).
- The headline is aimed at **his own roster** — 26 movers, largest name shown — with league-wide 456 kept as an honest secondary line (SR-16).
- The Morning Room stops crying wolf: the weekly `league_opportunity` artifact is judged against its declared cadence instead of a flat 24-hour threshold (SR-20).

## WHAT HE DOES NOT GET

- **No 39-trade replay.** The largest block of value in the draft and the hardest cut. It contributes nothing to goals 1 or 2 and is not calendar-gated — exactly as valuable on Sep 20 as on Sep 9.
- **No xVAR unclamp (was SR-17).** Dropped this revision. Two of its three named consumers are the exact sites Product Law Ruling 10 forbids ranking by a scalar; the third is trade side-value, reached ~2x a season. A Tier 1 rescale of every xVAR he sees, to improve an ordering the product's own law says should not exist, is not what the last 1.5 days of a capture-reliability sprint are for.
- **No event-stream freshness for `league_transactions` / `nflverse_usage` (SR-10b).** Deferred: the cadence analyzer cannot hold them without a new store kind. Those two stores stay unmonitored this season.
- **No consensus/market lane, no DynastyProcess data.** Zero of the 39 trades have a local point-in-time market snapshot; the probe needs a 10.89 GB clone on the laptop that must capture reliably for 17 weeks.
- **No P90 constant refresh** (under 1% effect on every unclamped player; rescales 27,021 archived DVS rows mid-season). **No `market_divergence_rebase` cutover** (rewrites ~37% of divergence classifications).
- **No performance work beyond the search fix.** `/api/health` still costs ~16s cold on the first open of the day.
- **The `posture_label` contradiction stays.** `team_posture.david_posture = REBUILDING` against `team_value.david_value_summary.posture_label = UNCLASSIFIED`, both on the same surface. Real, unfixed, named here so it is not lost.
- **No architecture migration.** Off-season, per the ruling.

---

## THE CALENDAR

Today is **Thursday 2026-08-20**. Day 1 is **Friday 2026-08-21**, not Monday.

```
BUILD (11 working days)                      FROZEN — soak only (6 capture cycles)
Fri 08-21  D1  SR-00 SR-02 SR-04  (SR-01 ✅ done 08-20)       Sat 09-05  unmodified cycle 1
Mon 08-24  D2  SR-03 SR-05 SR-06             Sun 09-06  unmodified cycle 2
Tue 08-25  D3  SR-07 SR-08     ← Tuesday 1   Mon 09-07  unmodified cycle 3
Wed 08-26  D4  SR-11  ← THE ALERT, FIRST     Tue 09-08  cycle 4 ← Tuesday 3: confirmation
Thu 08-27  D5  SR-09 (1 of 2)                Wed 09-09  unmodified cycle 5   run of the three
Fri 08-28  D6  SR-09 (2 of 2) ← CHAIN LANDS  Thu 09-10  KICKOFF 20:20 ET     weekly jobs
Mon 08-31  D7  SR-12 SR-10a
Tue 09-01  D8  SR-14 SR-19  ← Tuesday 2: FIRST post-chain exercise of the three weekly jobs
Wed 09-02  D9  SR-13 SR-15  ← SR-18 go/no-go checkpoint, end of day
Thu 09-03  D10 SR-16 SR-20
Fri 09-04  D11 ← BUFFER (unallocated) · FREEZE, end of day
```

**Why this order and not revision 1's.**

1. **SR-00 is first** because it is the cheapest thing in the document and it protects the store that is actually bleeding. Every morning it does not exist is a morning it cannot save.
2. **SR-11 moved from D7-D8 to D4, ahead of SR-09.** Revision 1 scheduled the only detection channel this product will ever have *after* the change that retires six LaunchAgents, leaving 4-5 live capture mornings in which a brand-new single point of failure wrote to irreplaceable stores with no way to tell David it had failed. **Detection precedes risk.**
3. **SR-09 lands end of D6 (Fri 08-28), before Tue 09-01.** It changes the wall-clock position of the producers `league-opportunity-map` reads at its fixed 09:35 slot. Landing before Sep 1 gives the three Tuesday-only jobs two post-change exercises instead of one.
4. **SR-14 sits on D8 so its transition morning (Wed 09-02) is a build day** — the one morning where the `None → real` xVAR transition is observable.

**If David starts Monday 08-24 he has 10 build days, not 11.** SR-18 falls off entirely and the buffer is consumed; the first surprise then costs SR-20, then SR-16, in that order.

---

## THE DAY BUDGET — the arithmetic

| Ticket | Size | Tier | Goal | Note |
|---|---|---|---|---|
| SR-00 Same-day retry insurance | 0.25 | 2 | 1 | **NEW** (PT-5) |
| SR-01 Push the 12 unpushed commits | 0.10 | 0 | — | |  ← ✅ DONE 2026-08-20
| SR-02 Track plists, back up `ops/launchd`, fix XML | 0.25 | 0 | 1 | |
| SR-03 Freeze date + rollback tiers | 0.25 | — | — | David's word |
| SR-04 Unstick the frontend gate | 0.25 | 0 | 3 | |
| SR-05 Battery-sleep option | 0.25 | — | 1 | David's word |
| SR-06 nflverse capture → current season | 0.50 | 0 | 1 | |
| SR-07 Real exit codes on both new producers | 0.50 | 0 | 1 | |
| SR-08 Recover the transaction gap | 0.50 | 0 | 1 | |
| SR-11 The daily gap alert | 1.00 | 2 | 1 | **moved to D4** (PT-2) |
| SR-09 Dependency-ordered, fail-soft chain | 2.00 | 2 | 1 | **rewritten** (PT-4) |
| SR-12 Make the app openable at all | 0.50 | 2 | 3 | |
| SR-10a Register `market_divergence_history` | 0.50 | 0 | 1 | **split** (PT-3), was 1.5 |
| SR-14 xVAR archive + the fabrication guard | 0.75 | 0 | 2 | **amended** (PT-1), was 0.5 |
| SR-19 Season-rollover rehearsal | 0.25 | 0 | 1 | **NEW** (PT-4b) |
| SR-13 Block the TE lambda edit | 0.50 | 0 | 2 | |
| SR-15 Trade Lab search correctness | 0.50 | 0 | 2 | |
| SR-16 Morning Room hero → his own roster | 0.50 | 0 | 3 | **re-aimed** (PT-6) |
| SR-20 Cadence-aware staleness | 0.50 | 0 | 3 | **NEW** (PT-8) |
| **COMMITTED** | **10.00** | | | |
| SR-18 League Activity strip | *1.50* | *0* | *3* | **CONDITIONAL** (PT-7 replaces SR-17) |

```
0.25 × 7   (SR-00, 01, 02, 03, 04, 05, 19)              = 1.75
0.50 × 9   (SR-06, 07, 08, 10a, 12, 13, 15, 16, 20)     = 4.50
0.75 × 1   (SR-14)                                      = 0.75
1.00 × 1   (SR-11)                                      = 1.00
2.00 × 1   (SR-09)                                      = 2.00
                                                COMMITTED 10.00 days
                                                AVAILABLE 11.00 days
                                                   BUFFER  1.00 day (D11)
```

**Reconciliation against revision 1 (9.75 committed, 1.25 buffer):**

```
  9.75  revision 1 committed
+ 0.25  SR-00   NEW — same-day retry insurance (PT-5)
- 1.00  SR-10   split to SR-10a (1.5 → 0.5); SR-10b deferred (PT-3)
+ 0.25  SR-14   amended — the None-guard and its regression test (PT-1)
+ 0.25  SR-19   NEW — season-rollover rehearsal (PT-4b)
+ 0.50  SR-20   NEW — cadence-aware staleness (PT-8)
─────
 10.00  revision 2 committed
```

Every scheduled day sums to exactly 1.00 (D1-D10); D11 is 0.00. The conditional line is unchanged in size: SR-17's 1.5d left it and SR-18's 1.5d took it. Neither was ever in the committed total.

**Why the buffer is 1.0 and not 0.** Seven of these nineteen tickets touch a producer that writes to a store whose gaps cannot be backfilled (SR-00, SR-06, SR-07, SR-08, SR-09, SR-14, SR-19) and four are Tier 2 (SR-00, SR-09, SR-11, SR-12). The freeze is hard. An 11-day sprint with 11 days committed has no answer to the first thing that goes wrong, the thing that goes wrong will be a Tier 2 capture change, and the cost is a permanent hole.

**Why SR-18 does not fit.** It needs 1.5 days; the buffer is 1.0. On plan it does not ship. It ships only if the sprint arrives at the end of D9 with SR-00 through SR-15, SR-19 and SR-20 all complete **and at least a half-day banked**, leaving D10+D11 = 2.0 days for SR-16 (0.5) + SR-18 (1.5) — zero slack before a hard freeze. **The checkpoint's default answer is no.**

---

# WEEK 1 — Fri 08-21 → Fri 08-28 (6 build days)

## DAY 1 (Fri 08-21) — buy the insurance, then clear what blocks everything else · 0.85d

> **SR-01 is already done** — pushed 2026-08-20 (`63bac58..ce7b540`), remote level with local, zero
> laptop-only commits. Its 0.15d is released back to slack, not to new work. Day 1 opens on **SR-00**,
> which is the ticket that actually matters here.


**Also on D1, not a ticket:** open the conversation with the lane holding the uncommitted `BUILD-3` work in `system_capture_health_models.py` (+124 lines), `system_capture_health.py` (+11), `test_system_capture_health_t1.py` (+20), `_t4.py` (+16). Those are SR-10a's and SR-11's primary files. It takes days to resolve a cross-lane conflict and one minute to ask on the first morning. Hand SR-03 and SR-05 to David this morning so his answers are back for D2.

---

### SR-00 · Same-day retry insurance — 11:30 and 14:00 on the two jobs that bleed · S · 0.25d · **Tier 2** *(NEW — PT-5)*

> **Lands Day 1, first, before SR-09 and independent of it.**

**Why.** The dominant observed failure is not a source outage. It is a **prior-date abort** — a timing race against a source that never fails — and a same-day retry recovers it completely.

1. `market_divergence_history` is missing **2026-07-10, 07-12, 07-17, 08-12**; `model_forward_capture_raw` is missing **2026-08-12**; `fc_forward_capture_raw` is complete at 58/58.
2. `grep -c market_source_prior_date app/data/logs/market_divergence_refresh.out.log` returns exactly **2**, both on the mornings the FC capture fired furthest off-slot (+162 min on 07-17, +102 min on 08-12).
3. The abort is **correct**: `run_market_divergence_refresh.py:217` is `if str(latest) != now.date().isoformat(): raise _MarketSourceError("market_source_prior_date")`, where `latest` is `SELECT MAX(snapshot_date) FROM fc_forward_capture_joinable WHERE source = ?` (line 178).
4. **And it is recoverable by running again the same day.** `_read_market_from_fc_pit` (line 166) reads the market side out of `fc_forward_capture.db` — **no network call**. Once the late FC snapshot has landed at 11:42, an 11:30-or-later rerun finds `latest == today` and succeeds against the same bytes.

On 07-17 and 08-12 the data existed on disk, in the right store, by late morning. Nothing re-read it.

**Provably a no-op on a healthy day.** Both stores are idempotent by construction:
- `market_divergence_history` — `PRIMARY KEY (player_id, capture_date)` with `ON CONFLICT … DO UPDATE SET` (`run_market_divergence_refresh.py:393-415`; its docstring at line 29 calls it an "idempotent per-date upsert").
- `model_forward_capture_raw` — `INSERT OR IGNORE` on `PRIMARY KEY (capture_date, source, semantic_output_hash, provenance_hash, player_key)` (`model_forward_capture_store.py:27-32, 221`), with `artifact_vintage` in `_VOLATILE_COLUMNS` (line 55) and the comment *"a same-key re-append that differs only by a volatile field (e.g. a re-regenerated PVO's captured_at) is an idempotent no-op rather than a false conflict."* **The immutability model was designed for re-runs.**

The recompute is deterministic within a day because both inputs are pinned: the FC snapshot is immutable per date, and `run_feature_refresh` fires once at 09:15.

**Why two retries.** 11:30 is the fast recovery. 14:00 is the backstop, and covers the one race 11:30 introduces — both jobs fire in the same minute, so a divergence run can meet a PVO runtime mid-republish. That case is already handled: `resolve_pvo_source` is the fail-closed verified-runtime-or-seed resolver (`run_market_divergence_refresh.py:342-344, 510-515`), so the outcome is a clean `pvo_source_not_ready` abort with a status marker, never a corrupt write. Do not stagger; the second retry is the fix.

**Files** — both **tracked** (`git ls-files ops/launchd/`), **clean**, and installed as **symlinks** into `~/Library/LaunchAgents/`, so the repo file *is* the live agent:
- `ops/launchd/com.davidleess.dynasty-market-divergence-refresh.plist` (`StartCalendarInterval` at line 27)
- `ops/launchd/com.davidleess.dynasty-model-pvo-refresh.plist` (`StartCalendarInterval` at line 44)

That tracked-and-symlinked pair is why this goes first: rollback is `git checkout` on two files plus one unload/load, and it does not wait on SR-02.

**The plist syntax — confirmed, and this repo has no precedent for it.** `man launchd.plist` declares the key as `StartCalendarInterval <dictionary of integers or array of dictionaries of integers>` and states *"Multiple dictionaries may be specified in an array to schedule multiple calendar intervals."* All 12 plists currently use the single-`<dict>` form — `grep -A3 StartCalendarInterval ops/launchd/ | grep -c '<array>'` returns **0**. **SR-00 introduces the first array form, so validate it rather than assuming it.** Correct shape: `<key>StartCalendarInterval</key><array><dict>…</dict><dict>…</dict><dict>…</dict></array>`, the existing `<dict>` becoming the first element unchanged.

One behaviour note from the same man page, in our favour: *"If multiple intervals transpire before the computer is woken, those events will be coalesced into one event upon wake from sleep."* A laptop asleep 09:00-15:00 produces **one** catch-up run, not three.

**Steps.**
1. In the pvo plist (line 44), convert `StartCalendarInterval` from `<dict>` to `<array>` of three dicts: existing `{Hour 9, Minute 30}`, then `{Hour 11, Minute 30}`, then `{Hour 14, Minute 0}`. Change nothing else.
2. Same in the market-divergence plist (line 27): keep `{Hour 9, Minute 40}`, add `{Hour 11, Minute 30}` and `{Hour 14, Minute 0}`.
3. **Validate with `plutil` AND `plistlib` before loading.** An array form `plutil` accepts and `plistlib` does not would silently break SR-11's schedule audit.
4. `launchctl unload` then `launchctl load` each. Symlinks, so no copy step and no drift.
5. Commit the two plists **alone**. Do not sweep the 64 dirty files in.
6. **Verify by a real run today**: pre-image digest, let 11:30 fire, post-image digest, confirm identical.

**Verification.**
```
plutil -lint ops/launchd/com.davidleess.dynasty-model-pvo-refresh.plist \
             ops/launchd/com.davidleess.dynasty-market-divergence-refresh.plist    → OK for both

./.venv/bin/python3.14 -c "import plistlib;
[print(p.split('dynasty-')[1][:24], plistlib.load(open(p,'rb'))['StartCalendarInterval'])
 for p in ['ops/launchd/com.davidleess.dynasty-model-pvo-refresh.plist',
           'ops/launchd/com.davidleess.dynasty-market-divergence-refresh.plist']]"
   → each prints a LIST of three dicts, e.g.
     model-pvo-refresh.plist [{'Hour':9,'Minute':30},{'Hour':11,'Minute':30},{'Hour':14,'Minute':0}]

launchctl list | grep -E 'dynasty-(model-pvo|market-divergence)'   → both present, exit status 0

# THE NO-OP PROOF — run BEFORE 11:30 and again AFTER the 11:30 fire.
./.venv/bin/python3.14 -c "
import sqlite3, hashlib
c=sqlite3.connect('file:app/data/market_divergence_history.db?mode=ro',uri=True)
rows=list(c.execute(\"select player_id, decision_supported, payload_json from market_divergence_history where capture_date=date('now','localtime') order by player_id\"))
print(len(rows), hashlib.sha256(repr(rows).encode()).hexdigest()[:16])"
   → today, before:   12222 7deb11f17867ff8f
   → after the retry: SAME count, SAME digest.  A changed digest on a healthy day means
     the recompute is not deterministic — stop and investigate before the 14:00 fire.

# THE GAP INVARIANT — run daily from here on (referenced by every later ticket)
./.venv/bin/python3.14 -c "
import sqlite3, datetime
for db,t,col in [('app/data/market_divergence_history.db','market_divergence_history','capture_date'),
                 ('app/data/model_forward_capture.db','model_forward_capture_raw','capture_date'),
                 ('app/data/fc_forward_capture.db','fc_forward_capture_raw','snapshot_date')]:
    c=sqlite3.connect('file:'+db+'?mode=ro',uri=True)
    ds=sorted({str(r[0])[:10] for r in c.execute('select distinct '+col+' from '+t) if r[0]})
    d0=datetime.date.fromisoformat(ds[0]); d1=datetime.date.fromisoformat(ds[-1]); h=set(ds)
    print(t,'MISSING',[(d0+datetime.timedelta(days=i)).isoformat()
          for i in range((d1-d0).days+1)
          if (d0+datetime.timedelta(days=i)).isoformat() not in h])"
   → today: market_divergence_history MISSING ['2026-07-10','2026-07-12','2026-07-17','2026-08-12']
            model_forward_capture_raw MISSING ['2026-08-12']
            fc_forward_capture_raw    MISSING []
   → NO NEW DATE may join any list, for the rest of the season.
```

**Done looks like.** Both plists carry three intervals, both parse in `plistlib`, both agents loaded, and a real 11:30 fire left `market_divergence_history` byte-identical for today's `capture_date`. A morning where the FC snapshot lands at 11:42 now still produces a divergence row.

**Rollback.** `git checkout --` the two plists, then unload/load each. Seconds, complete, available before SR-02 lands.

---

### SR-02 · Track the two live plists, back up `ops/launchd`, fix the illegal XML comment · S · 0.25d · Tier 0 *(draft: RISK-2)*

**Why.** Three verified defects in one place.
1. `git status --porcelain ops/launchd/` returns `?? com.davidleess.dynasty-league-transaction-capture.plist` and `?? com.davidleess.dynasty-nflverse-usage-capture.plist`. Both are the **symlink targets** for loaded LaunchAgents. A `git clean -fd` dangles both and the two newest capture jobs stop with no error surface.
2. `backup_manifest.json` has 43 `required` + 4 `optional` entries and **zero under `ops/`**. The schedule definitions for all 12 jobs — now including SR-00's retry intervals — are backed up nowhere.
3. `plistlib.load` fails on the transaction plist: `ExpatError: not well-formed (invalid token): line 29, column 5`. Line 29 contains `` `--current-season-only` `` inside an XML comment; a double hyphen is illegal there. `plutil` and `launchd` tolerate it, so any Python schedule audit — including SR-11's — silently cannot read that job.

**Files.** `ops/launchd/com.davidleess.dynasty-league-transaction-capture.plist`, `ops/launchd/com.davidleess.dynasty-nflverse-usage-capture.plist`, `app/config/backup_manifest.json`.

**Steps.**
1. Fix line 29: reword `` `--current-season-only` `` to `` `current-season-only` `` inside the comment. Do not touch `ProgramArguments`. (The market-divergence plist already models the convention: *"XML comments may not contain a double hyphen, so flags are named without their dashes."*)
2. `git add` the two plists and commit them **alone**.
3. Add `{"path": "ops/launchd", "required": true, "kind": "directory"}` to the `required` array. **Match the live shape, which carries three fields** — verified against `{'path': 'app/data/league_runtime/runs', 'required': True, 'kind': 'directory'}`. (Revision 1 gave a two-field shape; that was wrong.)
4. Confirm the six live symlinks still resolve and the agents are still loaded.

**Verification.**
```
git status --porcelain ops/launchd/   → empty
git clean -nd | grep -c launchd       → 0
./.venv/bin/python3.14 -c "import plistlib,glob;[plistlib.load(open(p,'rb')) for p in glob.glob('ops/launchd/*.plist')];print('all 12 parse')"
                                      → all 12 parse   (today: ExpatError)
./.venv/bin/python3.14 -c "import json;d=json.load(open('app/config/backup_manifest.json'));print(len(d['required']), [e for e in d['required'] if e['path'].startswith('ops/')])"
                                      → 44  [{'path': 'ops/launchd', 'required': True, 'kind': 'directory'}]
launchctl list | grep -c dynasty      → 12
```

**Done looks like.** Nothing under `ops/launchd` is untracked, all 12 plists parse with plistlib, `ops/launchd` is a required backup entry, 12 agents still loaded.

> **Prerequisite for SR-09 and SR-12.** Until the plists are committed and backed up, a launchd mistake in those tickets has no rollback. SR-00 is the deliberate exception: its two targets were already tracked before this ticket started.

---

### SR-01 · Push the branch · S · 0.1d · Tier 0 — ✅ **DONE 2026-08-20** *(draft: RISK-6)*

**Why — corrected 2026-08-20, and the correction is the reusable part.**

The original ticket said "push the 12 unpushed commits" and described twelve commits of product work
living on one laptop. **That overstated the exposure by roughly six times, and the error is one worth
naming because it is easy to repeat.**

`git rev-list --left-right --count origin/main...HEAD` returned `3	12`, which does mean **12 ahead,
3 behind** — an earlier brief had that direction inverted and acting on it would have been backwards.
But *ahead of `origin/main`* is **not** the same question as *unpushed*. Measured:

```
git rev-list --count origin/main..HEAD                        → 13   (ahead of main)
git rev-list --count origin/feature/outcome-loop-week1..HEAD   →  2   (actually laptop-only)
```

**Eleven of those commits were already safe on the remote feature branch.** They were unmerged, not
unbacked-up. Only two existed nowhere but the laptop, and one of those was the same day's closeout.

**The lesson for the rest of the sprint:** `origin/main...HEAD` answers *"how far is this branch from
trunk?"* It does **not** answer *"is my work backed up?"* For that, always ask
`origin/<current-branch>..HEAD`. On a machine whose cockpit backup has never succeeded, those two
questions get confused easily and only one of them is about data loss.

Real exposure was therefore two commits, not twelve — still worth pushing immediately, but a two-minute
housekeeping item rather than the day-one emergency the original framing implied.

**Files.** None edited. Repo `the product repo root`, branch `feature/outcome-loop-week1`.

**Steps.**
1. Confirm the direction yourself: `git rev-list --left-right --count origin/main...HEAD`.
2. `git push origin feature/outcome-loop-week1`. Push the **branch**, not main.
3. **Do NOT merge or rebase onto `origin/main` during this sprint.** Pulling 3 unreviewed commits into the tree that runs the daily capture chain is a Tier 2-equivalent change with no soak budget. The 3 behind stay behind until the freeze lifts.
4. Leave the dirty files alone — they belong to other lanes.

**Verification.** Run after pushing — these are the actual results from 2026-08-20:
```
git ls-remote --heads origin feature/outcome-loop-week1   → ce7b540...  (matches local HEAD)
git rev-list --count origin/feature/outcome-loop-week1..HEAD              → 0
git status --porcelain | wc -l                             → 58, unchanged (other lanes' files)
```

**Done looks like.** `origin/feature/outcome-loop-week1` is level with local HEAD and zero commits
exist only on the laptop. The dirty working tree is untouched.

> **✅ CLOSED 2026-08-20.** Pushed `63bac58..ce7b540`, a clean fast-forward, no force. Remote and local
> both at `ce7b540`; laptop-only commits now **0**; all six `docs/strategies/2026-08-20-*` documents
> confirmed present on the remote tree. **Day 1 begins at SR-00.**

---

### SR-04 · Unstick the frontend gate — one stale JSON blocks every UI change for the season · S · 0.25d · Tier 0 *(draft: MR-2)*

**Why.** `frontend/src/styles/rawCssAuditBaseline.json` line 67 records `"raw_hex": 7` for `realized-outcome/RealizedOutcomeScorecard.css`, and line 207 records `"totals": {"raw_hex": 17`. The live CSS has 0 and 10 — someone tokenized that file and never updated the census. The file is **committed**, so this is drift, not in-flight work. `rawCssAudit.test.js:112` asserts `readBaseline()` equals `currentReport()` exactly, and `npm run gate` chains `typecheck && lint && test && banned-language && build`. This one JSON fails the gate for **every** frontend change for the rest of the season. SR-15, SR-16 and SR-18's frontend half all need it green.

**Files.** `frontend/src/styles/rawCssAuditBaseline.json`

**Steps.**
1. Line 67: `"raw_hex": 7` → `"raw_hex": 0`.
2. Line 207, in `totals`: `"raw_hex": 17` → `"raw_hex": 10`.
3. Change nothing else. The other six counters (`raw_oklch` 69, `raw_rgb` 0, `raw_spacing_values` 71, `raw_radius_values` 30, `raw_font_size_values` 45, `non_token_font_families` 0) all match today and are a deliberate debt ledger.
4. **Do not** weaken the assertion or add a tolerance. The test's entire value is that it is exact.

**Verification.**
```
cd frontend && npx vitest run src/styles/rawCssAudit.test.js   → Test Files  1 passed (1)
cd frontend && npm run gate                                     → runs to completion, no failures
```

**Done looks like.** `npm run gate` is green, so SR-15, SR-16 and SR-20 can ship without fighting an unrelated census.

---

## DAY 2 (Mon 08-24) — David's two decisions, then make nflverse honest · 1.0d

### SR-03 · David adopts the freeze date and the four-tier rollback policy · S · 0.25d · **NEEDS DAVID'S WORD** *(draft: RISK-4)*

**Why.** The daily chain runs once per calendar day; confidence in a scheduler change is bought in calendar days. Three of the twelve jobs run **Tuesday only**, so full coverage requires the schedule to cross a Tuesday **after** the change lands. Without a stated freeze every lane assumes it has until Sep 10, goal 1 gets zero soak, and a capture break lands where the loss is permanent.

**Files.** None. This is a decision.

**Steps — present these, get his yes.**
1. **Hard freeze: end of day Friday 2026-09-04.** Build window Fri 08-21 → Fri 09-04 = 11 working days. Soak = 6 consecutive unmodified cycles (Sat 09-05 … Thu 09-10) including Tue 09-08.
2. **Three Tuesdays, not one.** Aug 25 and Sep 1 are build days; Sep 8 is a soak day. This revision lands SR-09 by Fri 08-28 so the three weekly jobs are exercised on **Sep 1 (fixable) and Sep 8 (confirmation)**. Tell him that is a deliberate change from the first draft, which gave them one shot.
3. After the freeze, admit **only Tier 0**: a change without which a capture job does not run or writes wrong data.
4. Classify every change into a rollback tier; refuse Tier 3 for the rest of the sprint.
   - **Tier 0** — code only, no persisted output. Rollback = `git revert` + restart. Seconds, complete.
   - **Tier 1** — constants and thresholds. Artifacts already written keep the new scale. **Nothing in this revision is Tier 1** — SR-17 was the only Tier 1 ticket and it is dropped.
   - **Tier 2** — launchd / ops. **SR-00, SR-09, SR-11, SR-12.** SR-09/11/12 are reversible only once SR-02 has landed; **SR-00 is the exception and is reversible immediately**, because both plists it edits are already tracked and symlinked.
   - **Tier 3** — schema change, identity re-keying, archive rewrite. Not reversible without a full GCS restore against 15 GB of stores of which the nightly backup covers 3.1 GB. Closed by the scoping ruling; it stays closed.
5. One stated exception: pushing commits to origin is not a product change and is not frozen (SR-01).

**Verification.** David's yes on the date, in writing. Mechanical check:
```
git log --since=2026-09-05 --oneline -- src/ app/ scripts/ ops/
   → after the freeze, only commits whose subject starts fix(capture)
```

**Done looks like.** David has said yes to 2026-09-04, and every ticket can name its tier before it starts.

---

### SR-05 · David picks a battery-sleep option · S · 0.25d · **NEEDS DAVID'S WORD** (sudo, his laptop) *(draft: CAP-4)*

**Why.** `pmset -g sched` confirms `wakepoweron at 6:00AM every day` is live. But `pmset -g custom` shows Battery Power ` sleep                1` — a **one-minute** idle-sleep timer. The Mac wakes at 06:00 and idle-sleeps at 06:01, fourteen minutes before the 06:15 nflverse job and twenty-nine before the 06:30 transaction job. AC Power is `sleep 0`, so this is a **battery-only** exposure — the travel case, and travel Sundays and Mondays are when live waivers and weekly outcomes land.

**Files.** None edited. Machine power configuration.

**Steps — present the options, David picks.**
- **Option A** — `sudo pmset -b sleep 30`. Covers the 06:15 and 06:30 jobs after a 06:00 wake. Costs battery when the lid is open and idle.
- **Option B** — change nothing; rely on launchd's missed-interval catch-up. Safer than it was: SR-00's retries and SR-09's single sequenced job both mean a late wake still produces a same-day capture. The cost is that the capture is stamped at wake time, which SR-09 step 5 now records honestly rather than hiding.
- **Option C** — have the SR-09 chain runner hold `caffeinate -i` for its own duration only. Narrow; does not help a job that never starts.
- **Never `sudo pmset -b sleep 0`.** Never sleeping on battery flattens the machine overnight and loses more days than it saves.

**Verification.**
```
pmset -g custom | sed -n '/Battery Power/,/AC Power/p' | grep ' sleep '
   → today: sleep 1        after Option A: sleep 30
pmset -g sched | grep wakepoweron
   → wakepoweron at 6:00AM every day   (SR-11 asserts this daily — some macOS updates
                                        clear `pmset repeat` and nothing today would notice)
```

**Done looks like.** Either the battery idle-sleep window covers the 06:15/06:30 jobs, or David has explicitly accepted catch-up semantics knowing SR-00 and SR-09 make them survivable.

---

### SR-06 · nflverse capture is hardcoded to 2023-2025 — it would capture zero 2026 usage for 17 weeks · S · 0.5d · Tier 0 *(draft: CAP-1)*

**Why.** `scripts/run_nflverse_usage_capture.py:29` is `DEFAULT_SEASONS = (2023, 2024, 2025)` and line 53 makes it the argparse default (`parser.add_argument("--seasons", nargs="+", type=int, default=list(DEFAULT_SEASONS))`). The LaunchAgent passes no `--seasons` (verified: `ProgramArguments` is exactly `[.venv/bin/python3.14, scripts/run_nflverse_usage_capture.py]`). Measured: `select season,count(*) from nflverse_capture group by season` returns 2016…2025 and **nothing for 2026**. From 2026-08-21 this job runs at 06:15 every morning for 17 weeks, re-downloads three finished seasons, and never fetches a single 2026 snap count, NGS row, injury report or depth chart. In-season usage *is* the new data the season produces.

**Files.** `scripts/run_nflverse_usage_capture.py` (line 29 literal, line 53 argparse default); `src/dynasty_genius/nflverse_usage.py` (per-stream `min_season` guards).

**Steps.**
1. Add `def current_nfl_season(now: date) -> int:` returning `now.year if now.month >= 3 else now.year - 1`. The season labelled 2026 runs Sep 2026 → Feb 2027, so a January 2027 date must still resolve to 2026. Derive from the clock; do not pin another literal.
2. Make the argparse default `[current_nfl_season(date.today())]` — **current season only**. 2023-2025 are final; refetching ~800 MB of settled data every morning is pure cost. Keep `--seasons` as the backfill escape hatch.
3. Treat an empty current season as a **healthy no-op**, not a failure. nflverse publishes nothing for 2026 until games are played, and SR-07 is about to make this job's exit code real — without this it alarms every morning for three weeks, and SR-11 turns every alarm into a notification David sees.
4. Streams with `min_season` guards (FTN charting, `min_season=2022`) already skip cleanly.
5. Run it once by hand after the change so week 1 is not its first live exercise.

**Verification.**
```
./.venv/bin/python3.14 -c "import sys,datetime;sys.path.insert(0,'scripts');from run_nflverse_usage_capture import current_nfl_season as f;print([f(datetime.date(*d)) for d in [(2026,8,20),(2026,9,15),(2027,1,20),(2027,3,1)]])"
   → [2026, 2026, 2026, 2027]

./.venv/bin/python3.14 -c "import sqlite3;c=sqlite3.connect('file:app/data/nflverse_usage.db?mode=ro',uri=True);print(list(c.execute('select season,count(*) from nflverse_capture group by season order by season')))"
   → today: 2016..2025, no 2026 row
   → after the fix + one live in-season run: includes ('2026', N) with N >= 5
```

**Done looks like.** `nflverse_capture` carries 2026 stream rows, and `select count(*) from player_snap_count where season='2026'` is greater than zero within 48 hours of the first 2026 game.

---

## DAY 3 (Tue 08-25) — make the new producers honest and close the transaction gap · 1.0d

*First Tuesday inside the build window. The three weekly jobs run this morning under the OLD arrangement — capture their log output as the pre-change baseline for the Sep 1 comparison.*

### SR-07 · Both new season-critical producers return exit 0 unconditionally · S · 0.5d · Tier 0 *(draft: CAP-2)*

**Why.** `scripts/run_league_transaction_capture.py:175` is a bare `return 0` reached regardless of what `status` contains. `scripts/run_nflverse_usage_capture.py:75` is the same. These are the two jobs installed 2026-08-20 to cover the season's live waivers and weekly usage — the two highest-churn in-season streams — and **neither can ever report failure to launchd**. Every other producer gates its exit: `run_market_divergence_refresh.py:737` and `run_fc_forward_capture.py:108` are both, verbatim, `return 0 if report.get("status") == "ok" else 1`. Exit codes are the input to SR-09's dependency edges and SR-11's alert, and SR-11 lands the day after this.

**Files.** `scripts/run_league_transaction_capture.py` (line 175); `scripts/run_nflverse_usage_capture.py` (line 75 — leave line 67 alone).

**Steps.**
1. Replace line 175 with a status-gated return matching the house pattern at `run_market_divergence_refresh.py:737`. **Read what `run_transaction_capture` / `run_chain_transaction_capture` actually put in `status` before choosing the healthy set.** Do not guess.
2. Same for line 75, using the `status` / `totals` dict already built above it. Leave the `--summary` path at line 67 returning 0 — read-only and healthy by definition.
3. Decide explicitly what a **partial** capture means: 5 streams requested, 3 succeeded. A partial must not exit 0 silently. Put the rule in the code, not a comment.
4. Do not invent a third exit convention. 0 = healthy, 1 = anything else. **SR-09's dependency edges read these as booleans and nothing else.**

**Verification.**
```
./.venv/bin/python3.14 scripts/run_nflverse_usage_capture.py --summary >/dev/null; echo $?
   → 0   (read-only path still healthy)

./.venv/bin/python3.14 scripts/run_league_transaction_capture.py --current-season-only \
    --league-id 0 --db-path "$SCRATCH/probe.db"; echo $?
   → NON-ZERO.  Today this exact command prints 0.
```
(`--league-id`, `--db-path`, `--current-season-only`, `--summary` are all real flags — verified at `run_league_transaction_capture.py:143-150`.)

**Done looks like.** A capture run that fetches nothing, or only some of its streams, exits non-zero. A clean run exits 0.

---

### SR-08 · Recover the 13-day transaction gap and settle the contradiction about it · S · 0.5d · Tier 0 *(draft: FIX-1 [Goal 1])*

**Why.** Two in-repo declarations contradict each other. `src/dynasty_genius/sources/daily_control.py:235-236` says transactions are *"not recoverable by re-reading: the endpoint serves current state, not an archive."* `app/config/backup_manifest.json` excludes `app/data/league_transactions.db` with the opposite reason: *"Rebuildable from public Sleeper API; not irreplaceable."*

**The store settles it.** `select season, ingested_at from league_season_capture` returns 2023, 2024 **and** 2025 all stamped `2026-07-31T02:16:40`, and the earliest transaction row is `2023-07-26T13:36:48`. Three years — 505 + 560 + 500 movement rows — arrived from Sleeper in one 2026 backfill. **The endpoint IS an archive.**

Two consequences. The 13-day gap is recoverable by one command (`max(created_at)` for 2026 is `2026-08-05T09:28:42`, 133 movement rows). And the backup exclusion is **correct** — acting on the daily_control note would add a GB-scale store to a backup that already fails 9 runs in 49.

**This ticket is also SR-18's data source.** The League Activity strip reads `league_transaction_movement` and cannot say anything true until this store is current.

**Files.** `scripts/run_league_transaction_capture.py`; `src/dynasty_genius/sources/daily_control.py` (lines 235-236); `app/config/backup_manifest.json` (leave the exclusion as-is).

**Steps.**
1. **Recover first.** `./.venv/bin/python3.14 scripts/run_league_transaction_capture.py --summary`
2. Only then correct the note at 235-236: Sleeper serves per-leg transaction history for the league chain, so re-reading recovers missed days.
3. **Keep the residual risk honestly rather than deleting the warning.** A transaction is re-readable, but the free-agent pool state and pending-waiver context *at the moment it was processed* are not served by that endpoint and are genuinely one-shot. If that is what the note was protecting, say so precisely instead of over-claiming about the transactions themselves.
4. Keep the `backup_manifest.json` exclusion. Do not add this store to a backup that fails 18% of runs.

**Verification.**
```
./.venv/bin/python3.14 -c "import sqlite3;c=sqlite3.connect('file:app/data/league_transactions.db?mode=ro',uri=True);print(list(c.execute(\"select max(created_at), count(*) from league_transaction where season='2026'\")))"
   → today:  ('2026-08-05T09:28:42.353000+00:00', 72)
   → after:  max within 24 hours of now

./.venv/bin/python3.14 -c "import sqlite3;c=sqlite3.connect('file:app/data/league_transactions.db?mode=ro',uri=True);print(list(c.execute(\"select transaction_type, action, count(*) from league_transaction_movement where season='2026' group by 1,2 order by 3 desc\")))"
   → today: free_agent/drop 35, waiver/add 28, waiver/drop 16, trade/pick_acquire 14,
            trade/pick_send 14, trade/add 12, trade/drop 12, commissioner/add 1, commissioner/drop 1
   → after: same shape, higher counts
```

**Done looks like.** The 2026 transaction store is current to today. The note and the manifest reason say the same true thing, and neither over-claims.

---

## DAY 4 (Wed 08-26) — the alert, BEFORE the risk · 1.0d

> **The single biggest sequencing change in this revision.** Revision 1 put SR-11 on days 7-8, *after* SR-09. That left 4-5 live capture mornings in which a brand-new single-point-of-failure chain wrote to irreplaceable stores with no way to tell David it had failed — with the spec's own words, in this ticket, being *"nothing in this repo can notify David."*

### SR-11 · The daily gap alert — the only detection channel that will exist · M · 1.0d · **Tier 2** *(draft: CAP-6)*

**Why.** **Nothing in this repo can notify David.** `grep -rnE "osascript|terminal-notifier|display notification|smtplib|sendmail" scripts/ src/ --exclude-dir=.oa3` returns **zero matches**. Every failure found in this investigation was silent: the 08-12 capture gap, the two `market_source_prior_date` aborts, the two `refusing to publish` exits in `feature_refresh.out.log`, the 9 failed backup runs out of 49, the 2026-08-18 realized-outcome failure. Each is in a log or a store, and none reached him. This ticket converts every other monitoring fix into something that changes an outcome — and it now lands two days before the chain rewire rather than three days after it.

**Files.** NEW `scripts/run_capture_gap_alert.py`; NEW `ops/launchd/com.davidleess.dynasty-capture-gap-alert.plist`; reads `app/api/routes/system_capture_health_models.py`, `app/data/ops/backup_status_latest.json`, and (from D6) the SR-09 chain report.

**Steps.**
1. **Call the inspectors directly** — `load_capture_cadence(config_path=...)` (`system_capture_health_models.py:241`) and `inspect_capture_store(...)` (line 644). Do **not** require the API server to be running, or the alert dies exactly when the server is down. **Check first whether the other lane's uncommitted +124 lines in this module have landed** (raised on D1); if not, import against the committed surface and note the coupling.
2. **One line per problem, and nothing at all when everything is clean.** Silence must mean healthy; a daily "all good" trains him to ignore it.
3. Deliver where he sees it without opening the app: `osascript -e 'display notification ...'` plus a plain-text file at a fixed path. No new dependency.
4. Schedule **10:30**, after the 10:15 backup, so one run covers 06:15, 06:30, the 09:00 chain and the backup. **It does NOT cover SR-00's 11:30/14:00 retries — by design.** The 10:30 alert reports the morning's state; if a retry then recovers the day, the next morning's alert is silent and the gap invariant confirms it. An alert that waits until 14:30 to report a 09:00 failure is worse than one that reports at 10:30 and is sometimes overtaken by good news.
5. Cover the failure classes this investigation actually found, by name:
   (a) a store missing yesterday's date;
   (b) a producer that exited non-zero (SR-07 and SR-09 make this readable);
   (c) **a chain step recorded `failed` or `skipped_upstream_failed` in the SR-09 report** — from D6 this is how a fail-soft chain stays honest, because a chain that carries on past a failure must still say a failure happened;
   (d) `app/data/ops/backup_status_latest.json` `status != "completed"` — the marker exists and today reads `completed`, 636 files, 3,107,327,429 bytes; the log shows **40 completed / 9 failed** all-time, an 18% failure rate nobody is told about;
   (e) `pmset -g sched` no longer showing the 6:00 AM wake (SR-05).
6. Keep it dumb and dependency-free. An alerting system that can itself fail silently is worse than none.

**Verification.**
```
./.venv/bin/python3.14 scripts/run_capture_gap_alert.py --dry-run
   → names the 2026-08-12 hole in market_divergence_history (after SR-10a registers the
     store; before that, the model_forward_capture 08-12 hole) and prints nothing else
     if nothing else is wrong

./.venv/bin/python3.14 scripts/run_capture_gap_alert.py      → a visible macOS notification

# prove silence-when-clean: point it at a scratch config whose only store is
# fc_forward_capture (58/58, zero missing)
   → prints nothing, exits 0

# prove it reads a failure it cannot see today: hand-write a scratch chain report with
# one step {"exit_code": 1} and one {"status": "skipped_upstream_failed"}
   → names both, one line each
```

**Done looks like.** On a morning where a capture was missed or a chain step failed, David gets a notification naming the store and the date before he opens anything. On a clean morning he gets nothing. **And it exists before SR-09 does.**

---

## DAYS 5-6 (Thu 08-27, Fri 08-28) — the chain · 2.0d

### SR-09 · Replace six wall-clock plists with one dependency-ordered, FAIL-SOFT chain · L · 2.0d · **Tier 2** *(draft: CAP-3 — substantially rewritten)*

**The single largest permanent-loss fix in this sprint, and the single largest permanent-loss RISK in it. Both halves are real, which is why the design changed.**

> **Deadline, not preference: this must land by end of day Friday 08-28.** SR-09 changes the wall-clock position of the producers `league-opportunity-map` reads at its fixed 09:35 slot. Landing before **Tue 09-01** gives the three Tuesday-only jobs two post-change exercises — Sep 1 inside the build window, where a finding is a fix, and Sep 8 in the soak, where it is a confirmation.

#### Why the chain
1. **Off-schedule runs are common.** Parsing `retrieved_at` from `app/data/logs/fc_forward_capture.out.log`, 7 of 57 daily captures fired more than 15 minutes off the 09:00 slot — 07-08 +104 min, 07-09 +28, 07-11 +127, 07-12 +66, 07-17 +162, 08-12 +102, 08-13 +28.
2. **market-divergence-refresh is pinned at 09:40 and fail-closes** when its FC source is from a prior date. `grep -c market_source_prior_date` returns exactly **2**, both on the +162 and +102 minute days.
3. **The result is permanent.** `market_divergence_history` is missing `07-10, 07-12, 07-17, 08-12`; `model_forward_capture_raw` is missing `08-12`; `fc_forward_capture_raw` is complete at 58/58. The FC store rejects backfill by design.

The abort is correct. The defect is that a fixed 40-minute wall-clock gap is the only thing sequencing the chain. (SR-00 covers the retry half on Day 1; SR-09 covers the sequencing half.)

#### Why it must fail SOFT — the measured case, not the theoretical one

`app/data/logs/feature_refresh.out.log` (54 lines, appended across runs) contains **two `refusing to publish` exits**, both `return 1` paths:

```
line 36: refusing to publish: dynamic source probe found no loadable season at 2026 or 2025
         (upstream likely unavailable): Failed to download
         https://github.com/nflverse/nflverse-data/.../pbp_participation_2021.parquet:
         HTTPSConnectionPool(host='release-assets.githubusercontent.com', port=443): Read timed out.
line 47: refusing to publish: source stream(s) unavailable after bounded retry — participation
```

Line 36 is the `ConnectionError` branch at `run_feature_refresh.py:344`. Line 47 is `_StreamsUnavailable`, raised at `run_feature_refresh.py:179`. **Both are a GitHub asset download timing out.** `run_feature_refresh` is the chain's most network-fragile step and it has already failed at least twice.

**And on both mornings nothing downstream was lost.** All four `market_divergence_history` holes trace to prior-date aborts, not to a feature_refresh failure. The reason is already in the codebase:
- `resolve_feature_source` (`src/dynasty_genius/features/feature_source.py:66-76`) resolves the feature CSV to *"a verified runtime if published, else the committed seed."* When `run_feature_refresh` publishes nothing, `run_pvo_refresh` → `build_universe_pvo_batch` resolves to the **seed** and produces a valid, slightly-staler-featured PVO.
- `resolve_pvo_source` (`run_market_divergence_refresh.py:342-344`) is the same pattern one layer up.

**A wholesale-halt chain would override a designed fallback and convert a handled degradation into a permanent hole.** On a morning like line 36's, a halting chain skips `run_league_snapshot_capture`, `run_pvo_refresh`, `run_market_divergence_refresh` and `run_what_changed_report` — losing that date in `model_forward_capture_raw` and `market_divergence_history` forever — because a parquet file on GitHub timed out. The current uncoupled arrangement absorbed that twice with zero loss. **A rewrite that is worse than what it replaces on the failure mode that has actually occurred is not a fix.**

#### The dependency edges, named

Not "stop on failure." Each step declares its **hard** upstreams. A step runs unless one of its declared hard upstreams failed; a soft upstream's failure is recorded and the step runs anyway.

| # | Step | Hard upstreams | Rationale, verified |
|---|---|---|---|
| 1 | `run_fc_forward_capture` | *(none)* | Live FantasyCalc fetch. Head of the chain. |
| 2 | `run_feature_refresh` | *(none)* | Independent nflverse pull. **Has no hard dependents.** |
| 3 | `run_league_snapshot_capture` | *(none)* | Live Sleeper capture via `build_sleeper_universe_snapshot` (`run_league_snapshot_capture.py:1-11, 35-40`). **No upstream in this chain at all. Must always run.** |
| 4 | `run_pvo_refresh` | *(none — feature_refresh is SOFT)* | Falls back to the committed feature seed via `resolve_feature_source`. Its docstring: *"NEVER runs the full league-intelligence chain or any feature/training/model producer."* |
| 5 | `run_market_divergence_refresh` | **step 1 only** | Market side reads `fc_forward_capture.db` (`:166-217`); model side goes through `resolve_pvo_source`, which falls back to the seed. Without step 1 it would abort `fc_forward_capture_empty`/`market_source_prior_date` anyway — skipping is faster and honest, not a policy choice. |
| 6 | `run_what_changed_report` | *(none)* | Reads the FC DB, the model DB and the league runtime artifacts; `assemble_structural_context` states *"A missing artifact degrades only its own section (`unavailable`), never the whole context"* (`report.py:207-221`). **Always runs, always last** — a report of a partly-failed morning is what David needs to see. |

**The one hard edge is 1 → 5. Everything else is soft.** What the chain buys is the ordering guarantee: launchd fires each missed `StartCalendarInterval` once on wake with **no ordering guarantee**, so six separate catch-ups can land in any order or concurrently. One job gets exactly one catch-up and runs its steps in order regardless of start time. **That was always the fix; halting was never part of it.** A skipped step is recorded `skipped_upstream_failed`, never `ok` and never `failed`; SR-11 reads that state by name.

#### Files
All six verified present; all six already carry `WorkingDirectory: the product repo root`:
- `ops/launchd/com.davidleess.dynasty-fc-snapshot.plist` (09:00) — **copy**
- `ops/launchd/com.davidleess.dynasty-feature-refresh.plist` (09:15) — **copy**
- `ops/launchd/com.davidleess.dynasty-league-capture.plist` (09:20) — **symlink**
- `ops/launchd/com.davidleess.dynasty-model-pvo-refresh.plist` (09:30 + SR-00's 11:30/14:00) — **symlink**
- `ops/launchd/com.davidleess.dynasty-market-divergence-refresh.plist` (09:40 + SR-00's 11:30/14:00) — **symlink**
- `ops/launchd/com.davidleess.dynasty-what-changed-report.plist` (09:45) — **copy**
- NEW `scripts/run_daily_chain.py`, NEW `ops/launchd/com.davidleess.dynasty-daily-chain.plist`, NEW `ops/launchd/retired/`

#### Steps
1. Write `scripts/run_daily_chain.py`: one process running the six producers **in order** as subprocesses, using the **exact argument vectors the plists carry today**. Dumped verbatim (`$P` = `the product repo root`):
   ```
   1. $P/.venv/bin/python3.14 $P/scripts/run_fc_forward_capture.py
        --db-path $P/app/data/fc_forward_capture.db
        --report-path $P/app/data/capture/fc_forward_capture_latest_report.json
   2. $P/.venv/bin/python3.14 $P/scripts/run_feature_refresh.py
   3. $P/.venv/bin/python3.14 $P/scripts/run_league_snapshot_capture.py
        --runtime-root $P/app/data/league_runtime
   4. $P/.venv/bin/python3.14 $P/scripts/run_pvo_refresh.py
        --runtime-dir $P/app/data/valuation_runtime
        --capture-db-path $P/app/data/model_forward_capture.db
        --report-path $P/app/data/model_capture/pvo_refresh_latest_report.json
        --capture-report-path $P/app/data/model_capture/model_forward_capture_latest_report.json
   5. $P/.venv/bin/python3.14 $P/scripts/run_market_divergence_refresh.py
        --latest-path $P/app/data/valuation/universe_market_divergence_latest.json
        --coverage-latest-path $P/app/data/valuation/universe_market_divergence_coverage_latest.json
        --history-db-path $P/app/data/market_divergence_history.db
        --fc-forward-capture-db-path $P/app/data/fc_forward_capture.db
        --fc-source fc_native --fc-settings-hash e27351d720e9fcf0
        --marker-path $P/app/data/valuation_runtime/market_divergence_refresh_status_latest.json
        --report-path $P/app/data/valuation_runtime/market_divergence_refresh_latest_report.json
   6. $P/.venv/bin/python3.14 $P/scripts/run_what_changed_report.py
   ```
2. **Encode the edges as data, not control flow.** A literal table in the module: `("run_market_divergence_refresh", hard_upstreams=("run_fc_forward_capture",))` and every other step with `hard_upstreams=()`. A reader must see the whole graph in one screen and a future change must be a one-line table edit. **Do not write `if step_failed: break`.**
3. **A step whose hard upstream failed is `skipped_upstream_failed`, not `failed`, not `ok`.** Three states, distinguishable in the report, because SR-11 alerts on two of them.
4. Emit one JSON report per run at a fixed path: every step, its exit code, status, duration, wall-clock start, and the chain's own start. Chain exit code non-zero if **any** step is `failed` — a fail-soft chain still reports failure; it just does not amplify it.
5. **Preserve the point-in-time truth the wall clock hides.** Record actual start versus the 09:00 target so a capture that ran at 11:42 is stored as one that ran at 11:42. SR-10a surfaces that as drift. *(This also fixes something the log cannot settle today: `feature_refresh.out.log` is append-only stdout with no timestamps, so its two recorded failures cannot be dated from the log alone.)*
6. Install **one** plist at 09:00 pointing at the chain, as a **symlink** so a repo edit is the live edit. Keep 06:15/06:30 separate (no downstream dependents), keep 10:15 backup separate (must run even if the chain failed), and **keep the three Tuesday-only jobs separate and untouched** — they are not in the chain, and a seventh Tuesday-only step is scope this sprint cannot soak.
7. **Retire the six superseded agents WITHOUT destroying the rollback.**
   > Revision 1 said *"unload the six superseded agents and remove their plists in the same change."* That contradicts the Tier 2 definition set four tickets earlier, because deleting the files removes the only working copy of six schedule definitions, and six of the twelve installed agents are **copies, not symlinks**, so `~/Library/LaunchAgents` holds no recoverable original either. Restoring would mean archaeology in git history during a freeze. **That is not a rollback.**

   a. Before touching anything, snapshot the live state: `launchctl list | grep dynasty > ops/launchd/retired/PRE-SR09-launchctl.txt` and `plutil -convert json -o ops/launchd/retired/PRE-SR09-schedules.json ops/launchd/*.plist`. Commit both.
   b. `git mv` the six plists into `ops/launchd/retired/`. **They stay tracked, stay inside the `ops/launchd` backup entry SR-02 added, and stay byte-identical.**

   **b-EXCEPTION — SR-00's retries survive this step. David's ruling, 2026-08-20: "put it back up."**
   Two of the six plists — `com.davidleess.dynasty-market-divergence-refresh.plist` and
   `com.davidleess.dynasty-model-pvo-refresh.plist` — carry the 11:30 and 14:00 retry entries SR-00
   added on Day 1. Retiring them wholesale silently reverts the sprint's cheapest protection, with no
   error and no alert.

   **Do this instead:** the new chain plist takes over the **09:00** slot only. The two SR-00 plists
   are **edited, not retired** — strip their 09:00 `StartCalendarInterval` entry, keep 11:30 and 14:00,
   and leave them loaded as standalone retry-only jobs. They remain byte-verifiable and independently
   rollback-able.

   *Why this shape and not folding retries into the chain:* the alternative (a `--retry-only` mode on
   `run_daily_chain.py` with a three-entry array) is architecturally cleaner but adds new code paths to
   the single riskiest ticket in a sprint whose first goal is "nothing is lost." Not retiring two files
   adds nothing to SR-09's blast radius. The slight inelegance of two mechanisms is a one-season cost
   and is cleaned up by the off-season architecture work.

   **SR-09 cannot close until a live 11:30 retry has been observed firing AFTER the chain landed** —
   see the added verification line below. Four plists retire, not six.
   c. `launchctl unload` the six agents and remove the six entries from `~/Library/LaunchAgents/`.
   d. **Do not delete `ops/launchd/retired/` until after the freeze lifts.** Put that sentence in a `README` inside the directory so a tidying pass cannot quietly undo it.

   Rollback becomes: `git mv` the six back, re-symlink or re-copy, `launchctl load`, `launchctl unload` the chain. Minutes, no history spelunking.
8. **The rollover this chain has never seen is SR-19's job, and it is not optional.** Do not close SR-09 without it.

#### Verification
```
./.venv/bin/python3.14 scripts/run_daily_chain.py --dry-run
   → prints the six steps in dependency order, each with its hard upstreams, and touches
     nothing.  Confirm: git status --porcelain unchanged, no mtime change under app/data/

# THE FAIL-SOFT PROOF — the test that separates this design from revision 1's.
# Scratch step table with step 2 (feature_refresh) replaced by `python3.14 -c "raise SystemExit(1)"`.
./.venv/bin/python3.14 scripts/run_daily_chain.py --steps-from "$SCRATCH/steps_fail2.json" --dry-run=false
   → step 2 status "failed", exit_code 1
   → steps 3, 4, 5, 6 ALL status "ok"      ← revision 1's design would show them skipped
   → chain exit code NON-ZERO

# THE HARD-EDGE PROOF — replace step 1 (fc_forward_capture) with the same failing stub.
   → step 1 "failed"
   → step 5 status "skipped_upstream_failed", exit_code null
   → steps 2, 3, 4, 6 ALL "ok"
   → chain exit code NON-ZERO

# the gap invariant — before and after every subsequent day (full command in SR-00)
   → NO NEW DATE may join any list, for the rest of the season

# the retirement is reversible
ls ops/launchd/retired/          → FOUR plists, PRE-SR09-launchctl.txt, PRE-SR09-schedules.json, README
                                   (market-divergence-refresh and model-pvo-refresh are NOT here —
                                    they stay live as retry-only jobs, per b-EXCEPTION)

# B1 PROOF — SR-09 does not close without this. Run the morning AFTER the chain lands:
pmset -g sched                                    → wakepoweron 6:00AM still present
launchctl list | grep -E "market-divergence|model-pvo"
                                                  → BOTH still loaded
plutil -convert json -o - ~/Library/LaunchAgents/com.davidleess.dynasty-market-divergence-refresh.plist \
  | python3 -c "import json,sys; print([ (e.get('Hour'),e.get('Minute')) for e in json.load(sys.stdin)['StartCalendarInterval'] ])"
                                                  → [(11,30),(14,0)]   — 09:00 gone, retries intact
grep -c "$(date +%Y-%m-%d)" app/data/logs/market_divergence_refresh.out.log
                                                  → at least 2 entries (09:00 chain run + 11:30 retry)
git status --porcelain           → clean under ops/
launchctl list | grep -c dynasty → 8   (12 − 6 retired + 1 chain + 1 gap-alert from SR-11)
```

**Done looks like.** One 09:00 job runs the six producers in order; its report shows each step's exit code, status, duration and true start time; a single producer's network flake leaves the other five running and is still reported as a failure; the six retired plists sit tracked and restorable in `ops/launchd/retired/`; and no new missing date appears in any of the three stores for the rest of the season, **including on mornings the chain started late**.

> **Do SR-02 first.** Until the plists are committed and backed up, a mistake here has no rollback at all.

---

# WEEK 2 — Mon 08-31 → Fri 09-04 (5 build days)

## DAY 7 (Mon 08-31) — make it openable, register the store that bleeds · 1.0d

### SR-12 · Make the app openable at all · S · 0.5d · **Tier 2 · David loads the agent** *(draft: MR-1)*

**Why.** Goal 3 says David opens it each morning. **Nothing in the repo starts the server.** `ls ops/launchd/` shows 12 plists, none for the API. `frontend/package.json` has no `dev` script (its scripts are exactly `banned-language`, `build`, `gate`, `lint`, `openapi-gen`, `test`, `test:governance`, `typecheck`, `visual:smoke`, `preview`). The only documented path is `README.md` → `uvicorn app.main:app --reload`, and the Setup block above it says `python3 -m venv venv` + `source venv/bin/activate` — `venv/` does not exist (it is `.venv/`) and `python3 -m venv` would build a 3.9 env, the repo-wide trap the brief names at line 28.

Worse: `app/main.py:63` is `Path("app/data/assets/headshots")` and `app/main.py:76` is `Path("frontend/dist")` — both **CWD-relative**. A LaunchAgent without `WorkingDirectory` serves the API fine but 404s on `/`; the product looks dead while the backend is healthy. On a Tuesday in October the habit dies on that friction, and SR-16, SR-20 and SR-18 are all void without it.

**Files.** NEW `ops/launchd/com.davidleess.dynasty-api.plist`; template `ops/launchd/com.davidleess.dynasty-league-opportunity-map.plist`; `app/main.py` (read only — lines 63 and 76 are why `WorkingDirectory` is mandatory); `README.md`; `frontend/dist/index.html` (exists, built 2026-08-18).

**Steps.**
1. Copy the opportunity-map plist as the template — same header-comment convention, same `StandardOutPath`/`StandardErrorPath` under `app/data/logs/`.
2. `ProgramArguments`: `.venv/bin/python3.14 -m uvicorn app.main:app --host 127.0.0.1 --port 8000` (absolute paths). **No `--reload`** — reload watches 15 GB of `app/data` and will thrash.
3. `WorkingDirectory` = `the product repo root`. **Required**, per main.py:63 and :76. All six daily plists already set it; match them.
4. `RunAtLoad=true`, `KeepAlive=true` so the 06:00 wake brings it back and a crash self-heals.
5. Rewrite README Setup/Run: replace `python3 -m venv venv` / `source venv/bin/activate` with the existing `.venv` and the explicit `.venv/bin/python3.14`; replace the `uvicorn --reload` line with the LaunchAgent plus `http://127.0.0.1:8000`. Note the SPA is served from `frontend/dist` (built by `npm run build`), not a dev server.
6. Install it as a **symlink**, matching SR-09's chain plist. Commit it **unloaded**; David runs `launchctl load`, per the standing convention stated in the opportunity-map plist's own comment.

**Verification** (after David loads it):
```
launchctl list | grep dynasty-api
   → a numeric PID in column 1, not "-"
curl -s -o /dev/null -w "%{http_code} %{size_download}\n" http://127.0.0.1:8000/
   → 200 with a non-zero byte count.  A 404 here means WorkingDirectory is wrong.
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/league/what-changed
   → 200
```

**Done looks like.** David opens a bookmark to `http://127.0.0.1:8000` on a cold morning after the 06:00 wake and the Daily What-Changed surface renders, with no terminal step.

---

### SR-10a · Register `market_divergence_history` — the store with four measured holes · S · 0.5d · Tier 0 *(draft: CAP-5 · SPLIT from SR-10 — PT-3)*

> **Blocker to clear before starting — raised on D1, confirm it is resolved now.** This ticket's primary files are dirty with another lane's uncommitted `BUILD-3: the 26-hour backup law` work: `app/api/routes/system_capture_health_models.py` **+124 lines**, `app/api/routes/system_capture_health.py` **+11**, `tests/contract/test_system_capture_health_t1.py` **+20**, `_t4.py` **+16** (measured: `git diff --stat` on those four paths). **Do not start until that lane has landed or explicitly handed the files over.** Two lanes editing a Pydantic config model in the same week is how an `extra=forbid` validator starts rejecting a config that looks correct.

**Why.** `app/config/capture_cadence.json` declares exactly two stores: `fc_forward_capture` and `model_forward_capture` (`config_version: 1`). `fc_forward_capture` is the one store with a **perfect** record — 58/58 days, zero missing. **The store with four measured holes is not in the config at all**: `market_divergence_history` is missing `2026-07-10, 07-12, 07-17, 08-12` and nothing watches it. The endpoint that answers "is the timeline complete enough to trust trends" (`app/api/routes/system_capture_health.py:72`) is structurally correct and asking about the wrong stores. **SR-11 alerts off exactly this config, so an unregistered store is an unalertable store.**

**Why 0.5d and not 1.5d.** `market_divergence_history` is a plain daily `capture_date` store — table `market_divergence_history`, columns exactly `[player_id, capture_date, decision_supported, payload_json]`, `PRIMARY KEY (player_id, capture_date)`. **The existing analyzer handles it unmodified.** It needs a config block and nothing else, and that delivers the alertable coverage the four holes have been waiting for.

**Why `league_transactions` and `nflverse_usage` are NOT in this ticket.** They cannot be without a new store kind:
- `CadenceStoreConfig` (`system_capture_health_models.py:74-89`) extends `_Strict`, whose docstring is *"reject unknown fields AND type coercion"* — `extra="forbid"`.
- `expected_cadence` is `Literal["daily"]`. A weekly or event-stream cadence is not expressible.
- `date_column`, `capture_start_date`, `density_floor_pct`, `density_baseline_window`, `scheduled_time_local`, `grace_hours`, `warn_consecutive_missing` and `window_risk_contiguous_days` are all **mandatory**, and every one is a daily-timeline concept.
- The data shapes disagree. `league_transaction` rows carry `created_at` — sparse event time; a quiet day with no transactions is **healthy**, and a missing-dates check would call it a gap. `nflverse_capture` is keyed `stream:season` with an `ingested_at` and is not date-partitioned at all.

Forcing them in means inventing `expected_cadence: "event_stream"`, making six required fields conditional, and writing a second analyzer path — a genuine 1.0-1.5d of model surgery on a file another lane is mid-edit. **That work is SR-10b, deferred to the off-season and named in the deferred list.** Cost of deferring: those two stores stay unmonitored this season. Mitigation: SR-08 recovers one, SR-06 points the other at 2026, and neither has ever been the store that silently lost a date — `market_divergence_history`, which this ticket does register, is.

**Files.** `app/config/capture_cadence.json`; `app/api/routes/system_capture_health_models.py` (read `CadenceStoreConfig` :74, `load_capture_cadence` :241, `analyze_store_health` :348, `inspect_capture_store` :644 — **edit only if step 3 requires it**); `app/api/routes/system_capture_health.py`.

**Steps.**
1. Add one store entry, copying the `fc_forward_capture` field set verbatim and changing only what differs:
   ```json
   {"store_id": "market_divergence_history",
    "db_path": "app/data/market_divergence_history.db",
    "table": "market_divergence_history",
    "date_column": "capture_date",
    "source_filter": null,
    "expected_settings_hash": null,
    "capture_start_date": "2026-07-09",
    "expected_cadence": "daily",
    "scheduled_time_local": "09:40",
    "grace_hours": 3,
    "density_floor_pct": 50,
    "density_baseline_window": 14,
    "warn_consecutive_missing": {"in_season": 1, "off_season": 3},
    "window_risk_contiguous_days": 7,
    "companion_tables": []}
   ```
   `capture_start_date` `2026-07-09` is the store's own first date (measured range `2026-07-09` → `2026-08-20`, 39 dates present). `scheduled_time_local` `09:40` is the plist's original slot; **do not change it to 09:00 just because SR-09 now starts the chain then** — the drift field in step 3 makes the difference visible, and pretending the target moved would hide it.
2. **Correct the in-season reconciliation revision 1 got wrong.** Revision 1 claimed the config carries "no top-level `in_season_months`." It does: `season_windows.in_season_months = [9, 10, 11, 12, 1]` (measured). The real problem is that this **disagrees with both market producers**, which define in-season as Aug 16 – Jan 15:
   - `src/dynasty_genius/adapters/fantasycalc_adapter.py:39-47` — *"Seasonal TTL: 6h in-season (Aug 16–Jan 15), 24h offseason."*
   - `scripts/run_market_divergence_refresh.py:106-110` — `in_season = (m == 8 and d >= 16) or m in (9,10,11,12) or (m == 1 and d <= 15)`

   **Today, 2026-08-20, the market adapters consider it in-season and the cadence config considers it off-season**, so `warn_consecutive_missing` is using the lenient `off_season: 3` on a store already moving daily. Either align `in_season_months` to the Aug-16 boundary or **state in the config file, in a comment field, why the cadence window is deliberately narrower.** Do not leave two silent definitions.
3. Add a **schedule-drift field** per store: the delta between the capture's recorded time and `scheduled_time_local`. A capture that landed at 11:42 for a 09:40 slot is present-but-degraded, and today the surface reports it as simply present. SR-09 step 5 records the number; this surfaces it. **If this requires touching `system_capture_health_models.py`, coordinate with the other lane first**; if the coordination is not clean, ship step 1 alone and move the drift field to the off-season with SR-10b. Step 1 is what closes the alerting hole.
4. **Key freshness off store contents, never off the status markers.** `app/data/nflverse_usage/nflverse_usage_status_latest.json` and `app/data/league_transactions/transaction_capture_status_latest.json` are both frozen at 2026-08-08 and written only by a Layer-1 controller that no launchd job runs. A marker-keyed check would be permanently and confidently wrong. This deliberately deletes a failure mode instead of repairing it — the old CAP-10 ticket.
5. Bump `config_version` and confirm the endpoint's fail-closed config validation still passes.

**Verification.**
```
./.venv/bin/python3.14 -c "import json;d=json.load(open('app/config/capture_cadence.json'));print(d['config_version'], [s['store_id'] for s in d['stores']], d['season_windows'])"
   → today: 1 ['fc_forward_capture','model_forward_capture'] {'in_season_months':[9,10,11,12,1]}
   → after: 2 [... 'market_divergence_history'] and a reconciled/annotated season window

./.venv/bin/python3.14 -m pytest tests/contract/test_system_capture_health_t1.py \
  tests/contract/test_system_capture_health_t2.py tests/contract/test_system_capture_health_t3.py \
  tests/contract/test_system_capture_health_t4.py -q
   → zero collection errors, zero failures

curl -s localhost:8000/api/system/capture-health | ./.venv/bin/python3.14 -c "import json,sys;d=json.load(sys.stdin);print([(s['store_id'], s['timeline']['missing_dates_count']) for s in d['stores']])"
   → includes ('market_divergence_history', 4)

./.venv/bin/python3.14 scripts/run_capture_gap_alert.py --dry-run
   → names market_divergence_history and 2026-08-12
```

**Done looks like.** The store with the four holes is in the config, the endpoint reports `missing_dates_count = 4` for it, and SR-11's dry run names it. `league_transactions` and `nflverse_usage` are **explicitly** on the off-season list, not silently absent.

---

## DAY 8 (Tue 09-01) — the xVAR archive, and the rehearsal the soak cannot do · 1.0d

> **Second Tuesday inside the build window, and the FIRST post-chain exercise of the three weekly jobs.** Do the Tuesday check before the tickets. This is what PT-2b's resequencing was for — a finding here is still a fix; the same finding on Sep 8 is a note.

**The Tuesday check — 15 minutes, before the tickets.**
```
# 1. Did the three weekly jobs run at all under the new arrangement?
launchctl list | grep -E 'league-opportunity-map|roster-capacity-audit|realized-outcome-scoring'
   → exit-status column 0 for all three

# 2. Did league-opportunity-map (09:35, fixed) read inputs the 09:00 chain had already refreshed?
./.venv/bin/python3.14 -c "
import json
a=json.load(open('app/data/valuation/league_opportunity_latest.json'))
c=json.load(open('app/data/ops/daily_chain_latest_report.json'))
print('opportunity captured_at:', a.get('captured_at'))
print('chain steps:', [(s['name'], s['status'], s['started_at'], s['duration_s']) for s in c['steps']])"
   → the opportunity artifact's captured_at must be LATER than step 4 (run_pvo_refresh)
     finishing.  Today's measured durations make a 09:00 chain finish around 09:05
     (fc ~1s, feature_refresh ~4m11s, league_capture ~3s, pvo ~21s, divergence ~8s,
     what_changed ~1s), so 09:35 should be comfortable — but MEASURE IT.  If the chain
     ran long and 09:35 fired mid-chain, that is a real finding and there are three build
     days plus Sep 8 to act on it.

# 3. The known-unfixed one.  The last realized-outcome run on 2026-08-18 wrote
#    {"status":"failed","failure_reason":"predictions_load_failed:FrozenPredictionSetUndeclared"}
#    while launchctl reported exit status 0.
grep -c FrozenPredictionSetUndeclared app/data/logs/realized_outcome_scoring.out.log
   → if it fails again today, that is a KNOWN-UNFIXED item (CAP-9, post-kickoff),
     not a new regression.  Do not spend a build day on it.
```

---

### SR-14 · The forward-capture archive has recorded NULL xVAR for all 57 days — and the fix must not fabricate 468 moves · S · 0.75d · Tier 0 *(draft: FIX-1 [Goal 2] · AMENDED — PT-1)*

**Why (the archive half).** `src/dynasty_genius/capture/model_forward_capture_driver.py:507-508` reads `row.get("dvs_pct")` and `row.get("xvar")` from the PVO **root**, but the producer emits both inside `row["valuation"]` — line 506 immediately above correctly uses `valuation.get("dynasty_value_score")`. Measured:

```
select count(xvar), count(dvs_pct), count(dynasty_value_score), count(*)
from model_forward_capture_raw
   → (0, 0, 27021, 707941)   across 57 capture dates, 2026-06-24 … 2026-08-20
```

The archive that exists to answer *"what did the model say then"* has **never stored an xVAR**. The suite is green because the fixture at `tests/contract/test_model_forward_capture_driver.py:76-77` puts `dvs_pct`/`xvar` at the root, mirroring the driver's bug instead of the real producer. Every further day loses another day permanently.

**Why (the guard half — non-negotiable).** The morning after this lands, the Morning Room will report **~468 model moves that did not happen**, unless a guard ships in the same change.

- `src/dynasty_genius/what_changed/daily_diff.py:354` is `xvar_delta = _float(latest[key].get("xvar")) - _float(prior[key].get("xvar"))`.
- `_float` at `daily_diff.py:494-495` is `return float(value) if value is not None else 0.0` — it **coerces `None` to `0.0`**.
- `count(xvar)` is **0 on every capture date that exists**, so `prior` is always `None → 0.0`.
- The moment SR-14 populates xVAR, today's real value minus yesterday's fabricated `0.0` yields a **non-zero `xvar_delta` for every scored player** — 468 today (measured: 468 of 12,222 runtime players carry a non-null `xvar`).
- Line 355 is `if dvs_delta == 0 and dvs_pct_delta == 0 and xvar_delta == 0: continue`. A non-zero `xvar_delta` defeats that skip, so all 468 rows are emitted.
- Downstream: `daily.model.status` flips from `vintage_changed_no_score_delta` (its measured value today) to `ok`; `ModelRegion` (`DailyWhatChanged.tsx:629`) flips from *"Projections held steady — no player movement on this tape"* (line 646) to a wall of rows; and SR-16's hero counts them.

**The soak cannot catch this.** SR-09's invariant is "no new date may join any missing list." 468 fabricated deltas add no missing date. Nothing in this spec's monitoring would notice, and the first person to notice would be David.

**⚠ GUARD BOTH FIELDS — David's ruling, 2026-08-20.** Line 354 (`xvar_delta`) is not the only
exposure: **line 353 computes `dvs_pct_delta` through the identical `None -> 0.0` path.** Guarding one
and not the other leaves the same ~468-row fabrication armed through the neighbouring field. Apply the
both-sides-non-None pattern at **both 353 and 354**. `_float` itself still must NOT change — it has
other callers at 350-352 and 365.

**Files.** `src/dynasty_genius/capture/model_forward_capture_driver.py` (507-508); `src/dynasty_genius/what_changed/daily_diff.py` (**lines 353 AND 354**, both call sites; `_float` at 494-495 is the coercion but must NOT be changed — it has other callers at 350-352 and 365); `tests/contract/test_model_forward_capture_driver.py` (76-77); `app/data/valuation_runtime/universe_pvo_runtime.json` (read to confirm shape); `tests/contract/test_daily_what_changed_report.py` (the guard test).

**Steps.**
1. Confirm the real shape first. Verified: `valuation` keys are exactly `['decision_supported','dvs_clamped','dvs_p90_ref','dynasty_value_score','engine_path','feature_completeness','model_grade','model_version','valuation_status','xvar','xvar_percentile_overall','xvar_percentile_position']`. **There is no key named `dvs_pct` under `valuation`** — the percentile field is `xvar_percentile_position`, populated from `pvo.get("dvs_pct")` at `universe_pvo_batch.py:99`.
2. Line 508 → `"xvar": valuation.get("xvar")`.
3. Line 507 → the `dvs_pct` decision. **Measured: of the 468 players with a non-null `xvar`, `xvar_percentile_position` is non-null for ZERO and `xvar_percentile_overall` is non-null for all 468.** So mapping to `xvar_percentile_position` fixes the nesting and still records NULL. Decide deliberately and **say which you chose**: either map `dvs_pct` to `xvar_percentile_overall` (populated) and rename the column's meaning honestly, or leave it NULL and record in the code that the cause is an upstream defect at `universe_pvo_batch.py:99`, out of scope here. Do not silently ship a mapping that still writes nulls without saying so.
4. **THE GUARD — `daily_diff.py:354`.** Compute `xvar_delta` only when **both** sides are non-`None`; when either is `None`, treat it as *no xVAR signal* — set `xvar_delta = 0.0` and let line 355's existing test do the skipping:
   ```python
   _lx, _px = latest[key].get("xvar"), prior[key].get("xvar")
   xvar_delta = (_float(_lx) - _float(_px)) if (_lx is not None and _px is not None) else 0.0
   ```
   **Do not change `_float` itself** — four other call sites in this function rely on `None → 0.0`.
   **Do not change the emitted field's type.** `xvar_delta: float` is non-Optional in `app/api/routes/league_what_changed_models.py:164`, `frontend/src/lib/api/types.gen.ts:3681` and `zod.gen.ts:1615`. Emitting `None` would be a schema change, an OpenAPI regen and a frontend regen for zero gain, because `0.0` is exactly what "no signal" means here.
   **What this buys, precisely:** on the transition morning, a row whose *only* difference is the `None → real` xVAR transition is skipped — that is the 468. A row whose DVS genuinely moved still appears, because `dvs_delta` is untouched. The Morning Room behaves on 09-02 exactly as it does today, and honestly from 09-03 onward.
5. Fix the fixture at `test_model_forward_capture_driver.py:76-77`: move `dvs_pct` and `xvar` inside the `valuation` dict.
6. Add **one** contract test that loads the real `universe_pvo_runtime.json` (skip if absent), maps a row through the driver's entry builder, and asserts the mapped `xvar` equals `row['valuation']['xvar']`. A fixture-only test is what let this run 57 days.
7. Add **one** guard test in `tests/contract/test_daily_what_changed_report.py`: prior `{"xvar": None, "dynasty_value_score": 50.0}` / latest `{"xvar": 12.3, "dynasty_value_score": 50.0}` → **zero deltas emitted**; then prior `{"xvar": None, "dynasty_value_score": 50.0}` / latest `{"xvar": 12.3, "dynasty_value_score": 55.0}` → **one delta, `xvar_delta == 0.0`, `dynasty_value_score_delta == 5.0`**. **The first case must FAIL against today's code.**
8. **Do not backfill the archive.** The 57 lost days are lost.

**Verification.**
```
./.venv/bin/python3.14 scripts/run_pvo_refresh.py \
  --runtime-dir app/data/valuation_runtime \
  --capture-db-path app/data/model_forward_capture.db \
  --report-path app/data/model_capture/pvo_refresh_latest_report.json \
  --capture-report-path app/data/model_capture/model_forward_capture_latest_report.json

./.venv/bin/python3.14 -c "import sqlite3;c=sqlite3.connect('file:app/data/model_forward_capture.db?mode=ro',uri=True);print(list(c.execute('select capture_date,count(*),count(xvar),count(dvs_pct) from model_forward_capture_raw group by 1 order by 1 desc limit 2')))"
   → today's row must show count(xvar) >= 400 (the runtime carries 468 non-null xVAR)
     where every prior date shows 0

./.venv/bin/python3.14 -m pytest tests/contract/test_model_forward_capture_driver.py \
  tests/contract/test_daily_what_changed_report.py -q   → passes, including both new tests

# THE FABRICATION CHECK — run on the morning of Wed 09-02, before anything else.
./.venv/bin/python3.14 -c "import json;d=json.load(open('app/data/what_changed/what_changed_latest_report.json'))['daily_diff']['model'];print(d['status'], len(d.get('deltas') or []))"
   → today (pre-change):         vintage_changed_no_score_delta 0
   → 09-02 morning (post-SR-14): a plausible number of REAL model moves — single or low
     double digits — and MUST NOT be ~468.  468 means the guard is not working; revert the
     driver change the same morning.  One more null day costs less than a fabricated tape.
```

**Done looks like.** `count(xvar)` for today's `capture_date` is non-zero and matches the runtime's non-null xVAR count. The real-artifact test fails if the nesting regresses. The guard test fails if the `None` coercion returns. And on the morning of 09-02, `daily.model.deltas` is a real number, not 468.

---

### SR-19 · Rehearse the season rollover the soak structurally cannot exercise · S · 0.25d · Tier 0 *(NEW — PT-4b)*

**Why.** All six soak cycles (Sat 09-05 … Thu 09-10) run **before a single 2026 game has been played**. The rollover from a 2025-anchored feature window to a 2026 one therefore cannot happen inside the soak — it happens on or about Fri 09-11, after kickoff, with the freeze on, on a chain that has never seen one.

The mechanism is dynamic and it is in the code. With `--season-end` unset — and the LaunchAgent passes no arguments at all (verified: `ProgramArguments` is exactly `[.venv/bin/python3.14, scripts/run_feature_refresh.py]`) — `run_feature_refresh.py:336-350` anchors the discovery ceiling on the current calendar year, steps down **once** on a source 404, then sets `season_end = int(ps["season"].max())` from the loaded `player_stats`. Its own comment names the case:

> *"So the daily arg-less scheduler resolves to the latest PLAYED season (e.g. 2025 in the offseason), never an unplayed calendar year, never crashes on the missing-parquet 404, and auto-advances the moment real new-season data lands. … this fixes the offseason block (and the **post-kickoff September edge**) without masking a broken feed."*

Today it resolves to 2025. In mid-September it will resolve to 2026 on its own, and every downstream artifact's feature window moves with it. **That transition has never been run.** It is also the step with the only two recorded failures in the chain, both network, both on this exact bounded probe.

**And the escape hatch makes the rehearsal cheap:** `--season-end` is an explicit override (`run_feature_refresh.py:293-300`) and `--runtime-dir` (line 285) redirects the publish, so the rollover can be forced against a scratch runtime today without touching the live one.

**Files.** None edited. Reads `scripts/run_feature_refresh.py`; writes only into `$SCRATCH/rollover_rehearsal/`.

**Steps.**
1. Force the rollover against a scratch runtime dir:
   `./.venv/bin/python3.14 scripts/run_feature_refresh.py --season-end 2026 --runtime-dir "$SCRATCH/rollover_rehearsal"`
2. Record which of three outcomes happened, in one sentence each:
   - **(a) It published.** The 2026 window loads and the T4 inference-scoped publish gate passed. Rollover proven; note the row counts.
   - **(b) It refused to publish** with `source stream(s) unavailable` or `dynamic source probe found no loadable season`. **This is the EXPECTED and CORRECT answer today** — there is no 2026 parquet yet. Confirm the refusal is clean: exit code 1, no partial artifact, and **no lock left behind** (`run_feature_refresh.py:315-320` writes a lock and releases it in a `finally`; a stranded lock would refuse every subsequent run and that failure would be silent).
   - **(c) Anything else** — traceback, partial publish, stale lock, hang. That is a finding, it is Tier 0 to fix, and there are three build days left.
3. Run the chain end to end once against the same scratch runtime so the rollover is exercised **through SR-09's runner**, not just the script: the point is that a fail-soft chain handles a `feature_refresh` refusal by carrying on, and this is the one chance to see that against a real refusal rather than a stubbed one.
4. **Write down what the first real rollover morning will look like** and leave it where the soak-week checklist can see it: on the first morning after 2026 data lands, `feature_refresh` may exit 1 once while nflverse publishes, the chain will carry on (steps 3-6 all soft), and `run_pvo_refresh` will fall back to the committed feature seed. **That is a degraded-but-captured morning, not an outage** — and SR-11 will say so.
5. Do **not** change `run_feature_refresh.py`. If the rehearsal finds a defect, fix it as its own Tier 0 change with its own verification.

**Verification.**
```
./.venv/bin/python3.14 scripts/run_feature_refresh.py --season-end 2026 \
  --runtime-dir "$SCRATCH/rollover_rehearsal"; echo "exit=$?"
   → exit=1 with "refusing to publish: ..." is the EXPECTED result today (outcome b)
   → exit=0 with a published runtime is outcome (a) — also fine, record the counts

ls -la "$SCRATCH/rollover_rehearsal"   → NO lock file remains, whatever the exit code
git status --porcelain                  → unchanged.  Must not touch the live runtime or tree.

./.venv/bin/python3.14 scripts/run_daily_chain.py --dry-run=false --runtime-override "$SCRATCH/rollover_rehearsal"
   → step 2 "failed" (outcome b) and steps 3,4,5,6 all "ok" — the fail-soft proof,
     against a REAL refusal
```

**Done looks like.** One of the three outcomes is written down with the command that produced it, no lock is stranded, the live runtime is untouched, and the chain has been observed carrying on through a genuine `feature_refresh` refusal. **SR-09 is not closed until this is done.**

---

## DAY 9 (Wed 09-02) — the two correctness items that reach an act David takes · 1.0d

> **First: run the SR-14 fabrication check** before touching anything else. This is the transition morning.
>
> **End of day: the SR-18 go/no-go checkpoint.**
> - SR-00 through SR-15 complete, SR-19 and SR-20 complete, **and at least a half-day banked** → SR-18 is in across D10-D11, severable, backend half first.
> - Anything else → SR-18 moves to the off-season. D10 runs SR-16 and SR-20, D11 stays the buffer, and the sprint ends early and safely. **This is the better outcome for goal 1, and it is the expected one.**

### SR-13 · Block the TE lambda edit an earlier brief instructed, and guard against it · S · 0.5d · Tier 0 *(draft: RISK-5)*

**Why.** An earlier version of SEASON-BRIEF.md said `XVAR_LAMBDA_ENGINE_B['TE']` should be **0.703** rather than the shipped **0.648**, and that "every TE is undervalued ~8% in every cross-positional comparison." **The algebra says otherwise, and following it would introduce the error it thinks it removes.** The brief has since been corrected — its item 1 now reads `RETRACTED 2026-08-20 — DO NOT EDIT THE LAMBDA` — but the retraction lives in one document and the constants live in the code, and nothing in the code stops the next agent who reads a stale copy.

Verified by importing the contract:
```
P90    = {QB 20.1,  RB 15.7,  WR 14.5, TE 9.4}
lambda = {QB 1.386, RB 1.083, WR 1.0,  TE 0.648}
P90[pos] / P90['WR'] →  QB 1.386   RB 1.083   WR 1.0   TE 0.648    ← exact, all four
```
`ENGINE_B_REPLACEMENT_DVS` derives from the same P90s (its own comments: QB 64.2 = 12.91/20.1, RB 46.4 = 7.29/15.7, WR 60.6 = 8.79/14.5, TE 95.6 = 8.99/9.4). Because `dvs_raw = projection_2y / _b_p90 * 100.0` at `pvo_assembler.py:407`, **the position P90 cancels exactly**: unclamped xVAR = (ppg − replacement_ppg) × 100 / P90_WR. Editing the lambda alone breaks that cancellation and creates a genuine 8.4% TE distortion where none exists today.

The real TE defect is an **ordering** defect at the clamp (`pvo_assembler.py:408-409`: `dvs_clamped_flag = dvs_raw > 100.0`; `dynasty_value_score = round(min(100.0, max(0.0, dvs_raw)), 1)`), not a scaling one. It was SR-17's subject; SR-17 is dropped and the measurement is preserved here.

**Files.** `src/dynasty_genius/models/engine_b_contract.py`; `src/dynasty_genius/pvo_assembler.py` (407-409, read only); `tests/contract/test_phase15_xvar.py`.

**Steps.**
1. **Strike the lambda-only edit from the correctness backlog, in the code's own comments.** Put the cancellation identity in the `engine_b_contract.py` docstring so it is where the next agent will actually be standing. This costs nothing and prevents an actively harmful change. If you do nothing else in this ticket, do this.
2. Add a contract test asserting the coupled identity so no future agent can move one constant alone:
   - for each position, `XVAR_LAMBDA_ENGINE_B[pos] == round(ENGINE_B_P90_PPG[pos] / ENGINE_B_P90_PPG['WR'], 3)` within 0.001;
   - `ENGINE_B_REPLACEMENT_DVS[pos] == round(REPLACEMENT_PPG[pos] / ENGINE_B_P90_PPG[pos] * 100, 1)` within 0.05, using the replacement PPG values already documented in the `engine_b_contract.py` comments (QB 12.91, RB 7.29, WR 8.79, TE 8.99).

   **This guard is green against the constants shipping today — verify that before committing it.**
3. Record the clamp measurement in the test module's docstring so the real defect is not lost with SR-17: 11 of 89 TEs sit at the DVS ceiling, versus QB 0/37, RB 5/99, WR 6/163.

**Verification.**
```
./.venv/bin/python3.14 -c "import sys;sys.path.insert(0,'.');from src.dynasty_genius.models.engine_b_contract import ENGINE_B_P90_PPG as P, XVAR_LAMBDA_ENGINE_B as L;print([(p, round(P[p]/P['WR'],3), L[p]) for p in P])"
   → [('QB',1.386,1.386), ('RB',1.083,1.083), ('WR',1.0,1.0), ('TE',0.648,0.648)]
     the pairs match — that IS the proof the lambda is not independently wrong

./.venv/bin/python3.14 -m pytest tests/contract/test_phase15_xvar.py -q
   → passes, including the new coupled-identity test, against UNMODIFIED constants

./.venv/bin/python3.14 -c "import sqlite3;c=sqlite3.connect('file:app/data/model_forward_capture.db?mode=ro',uri=True);[print(r) for r in c.execute(\"select position,count(*),sum(case when dynasty_value_score>=100 then 1 else 0 end) from model_forward_capture_raw where capture_date='2026-08-20' and engine_path='ENGINE_B' and dynasty_value_score is not null group by 1\")]"
   → ('QB',37,0)  ('RB',99,5)  ('TE',89,11)  ('WR',163,6)
```

**Done looks like.** The lambda-only edit is struck in the code, not just in a document. A contract test fails if any one of the three coupled constants moves alone. The TE defect is restated, in the repo, as 11 of 89 TEs tied at the DVS ceiling.

> **If a day is lost:** keep step 1 and drop steps 2-3.

---

### SR-15 · Trade Lab asset search renders results for the WRONG query · S · 0.5d · Tier 0 *(draft: PERF-4, absorbs MR-8)*

**This is a correctness bug, not a latency one.**

**Why.** `frontend/src/trade/AssetSearch.tsx:37` is `onChange={(event) => void run(event.target.value)}` — one fetch per keystroke, no debounce, no `AbortController`, no sequence guard. Line 26 does `setResults(parsed.success ? (parsed.data.results as CatalogEntry[]) : [])` on whichever response resolves **last**. Because each request independently parses ~30 MB server-side, completion order is scrambled. Reproduced 3/3: typing **"brown"** left the dropdown showing the results for **"bro"** — `['Amon-Ra St. Brown','Chase Brown','A.J. Brown','Brock Purdy','Brock Bowers','Jonathon Brooks']`. **Brock Purdy is offered as a match for "brown."** One mis-click puts the wrong asset into a trade evaluation. That is goal 2, reached through a perf defect.

The repo already has the fix pattern: `frontend/src/lib/useEndpointResource.ts:24-56` does exactly this with an `AbortController`. Its own header comment says *"Trade Lab POSTs and typeahead search stay on their own paths"* — which is how this got left out.

**Files.** `frontend/src/trade/AssetSearch.tsx`; `frontend/src/trade/AssetSearch.test.jsx`.

**Steps.**
1. Move the query into React state and drive the fetch from a `useEffect` keyed on the **debounced** query, instead of firing inside `onChange`.
2. 200 ms debounce: `onChange` sets the raw query; a `useEffect` + `setTimeout` sets the debounced query; the fetch effect keys on the debounced value. Clear the timer in cleanup.
3. `AbortController` per request, `{ signal: controller.signal }` on the fetch, `controller.abort()` in cleanup. Copy the shape from `useEndpointResource.ts:24-56`, **including** its `if (!controller.signal.aborted)` guard in the catch — an abort must not render as an error and must not clear results.
4. Keep the existing min-length-3 guard (`AssetSearch.tsx:15`, `if (query.trim().length < 3)`) and the `safeParse`-or-clear behaviour (line 26) exactly as they are.
5. No caching, no retry. One in-flight request at a time is the whole fix.

**Verification.**
```
cd frontend && npx vitest run src/trade/AssetSearch.test.jsx
```
with two new tests:
- **(a) stale-result** — stub fetch so `q=bro` resolves after 100 ms and `q=brown` after 10 ms; type `b,r,o,w,n` with fake timers; advance all timers; assert the rendered list contains no `"Brock Purdy"`. **This test must FAIL against today's code and pass after.**
- **(b) debounce** — type `brown` one char at a time within 200 ms, advance timers, assert `fetch` was called exactly once and with `q=brown`. Today it is called 3 times.

Then `npm run gate` → green (requires SR-04).

**Done looks like.** Both new tests pass; test (a) demonstrably fails when reverted. Typing a full player name issues one request, and the dropdown always shows results for the text currently in the box.

---

## DAY 10 (Thu 09-03) — aim the one number at him, and stop crying wolf · 1.0d

### SR-16 · The Morning Room headline counts a number David does not act on · S · 0.5d · Tier 0 *(draft: MR-3 · RE-AIMED — PT-6)*

**Why.** `frontend/src/what-changed/DailyWhatChanged.tsx:304-307` computes the hero as `top_movers.length + roster_deltas.length + model.deltas.length`. Measured against the live report: **25 + 26 + 0 = 51**, rendered by `ValueHero` at line 334 as *"Moves on the tape — 51 — market and model changes since the prior snapshot."*

Revision 1's fix was to swap 51 for `daily_diff.market.total_movers_count = 456`. **That is a bigger number, not a better one.** 456 is league-wide churn across the entire FantasyCalc universe — every player in a 12,222-row valuation set whose market value moved by any amount. David does not act on it, cannot act on it, and it will read 400-something every morning of the season, which makes it wallpaper by week three.

**The same payload already carries the number he does act on.** `daily_diff.market.roster_deltas` is his own roster, built at `src/dynasty_genius/what_changed/daily_diff.py:145-149` — *"Roster focus: every roster player present in both snapshots, even if flat."* Measured on the live report: **26 rows, all 26 with a non-zero `value_delta`** — Tank Dell +139, Chris Bell +113, Kaelon Black +93, Fernando Mendoza −84, Rome Odunze +83, Braelon Allen +78. Twenty-six names he owns, on a surface he opens to find out what happened to his team. Same half-day, same file, same fixture work.

**One precision point the code comment makes and the ticket must respect.** `roster_deltas.length` is **not** a mover count — it is the count of his roster players present in both snapshots, flat ones included. It happens to equal the mover count today because all 26 moved. **Count rows with `value_delta !== 0`.** Using `.length` would print a near-constant 26 every morning and reinvent the same wallpaper defect.

**Files.** `frontend/src/what-changed/DailyWhatChanged.tsx` (`ReadyView` moveCount 304-307; `ValueHero` 334; `quietDay` 324; `MarketRegion` 446); `frontend/src/what-changed/DailyWhatChanged.test.tsx`; `frontend/src/ui/ValueHero.tsx` — **read only.** Its props are exactly `{label, value, basis}`, all strings (lines 5-13). No component change, therefore no new CSS and no new tokens for `rawCssAudit` to census.

**Steps.**
1. Derive the hero from **his roster**: `rosterMovers = (daily.market.roster_deltas ?? []).filter(r => r.value_delta !== 0)`. Hero `value` = `String(rosterMovers.length)`.
2. `label` = `"Your roster moved"`. `basis` names the largest mover by absolute delta from the same array: e.g. *"26 of your players; largest Tank Dell +139"*. If `rosterMovers` is empty, `basis` = *"no movement on your roster since the prior snapshot"*.
3. **Keep 456 as an honest secondary line, and keep the truncation honest.** In `MarketRegion` (line 446), under the 25-row list, render *"Showing 25 of 456 market movers league-wide"*, sourced from `total_movers_count` and the rendered row count. When `total_movers_count` is null/absent (it is nullish in the schema), render *"Showing 25 market movers"* and **never** a total it does not have.
4. Repoint `quietDay` (line 324) at the new derived value so a genuinely quiet roster day still renders the baseline roster rows, and check the copy still reads true — the existing string is *"No valuation deltas observed since the last capture."*
5. Do not add a section, a chart, or a component. This ticket is three strings and a filter.

**Verification.**
```
cd frontend && npx vitest run src/what-changed/DailyWhatChanged.test.tsx
```
with three new cases:
- **(a)** 26 `roster_deltas` all non-zero, `total_movers_count` 456, `top_movers` 25 → hero renders **26**, basis contains the largest name, market region contains *"Showing 25 of 456"*.
- **(b)** 26 `roster_deltas` of which 20 have `value_delta: 0` → hero renders **6**, not 26. *(The case `.length` would get wrong.)*
- **(c)** `total_movers_count: null` → market region renders *"Showing 25 market movers"* with no total; hero unaffected.

```
./.venv/bin/python3.14 -c "import json;m=json.load(open('app/data/what_changed/what_changed_latest_report.json'))['daily_diff']['market'];rd=[r for r in m['roster_deltas'] if r['value_delta']];print(len(rd), m['total_movers_count'], len(m['top_movers']), max(rd,key=lambda r:abs(r['value_delta']))['player_name'])"
   → 26 456 25 Tank Dell
     the rendered hero must equal the first number, with that name in the basis line
```
Then `npm run gate` → green (requires SR-04).

**Done looks like.** The largest number on the surface David reads every morning is the number of **his own** players that moved, with the biggest name beside it. 456 is still there, still true, and no longer pretending to be about him.

---

### SR-20 · The Morning Room cries wolf six mornings out of seven · S · 0.5d · Tier 0 *(NEW — PT-8)*

**Why. This is the specific mechanism by which a daily habit dies.**

`league_opportunity` is a **Tuesday-only** producer — `com.davidleess.dynasty-league-opportunity-map.plist` at `{'Weekday': 2, 'Hour': 9, 'Minute': 35}`. Its section gets its staleness from `_section_envelope` (`src/dynasty_genius/what_changed/report.py:439-469`), which computes `is_stale = age_hours >= _STALE_THRESHOLD_HOURS` where `_STALE_THRESHOLD_HOURS = 24.0` (line 54) — **a flat threshold applied to every section regardless of how often its producer runs.**

Measured on the live report today (Thursday, two days after the last Tuesday):
```
/structural_context/sections/league_opportunity  age_hours 48.2   is_stale TRUE
/structural_context/sections/drop_pressure       age_hours  0.4   is_stale false
/structural_context/sections/sleeper_snapshot    age_hours  0.4   is_stale false
/structural_context/sections/team_posture        age_hours  0.4   is_stale false
/structural_context/sections/team_value          age_hours  0.4   is_stale false
```

The frontend renders it verbatim at `DailyWhatChanged.tsx:835-838` as `` `${basis} — ${is_stale ? "stale" : "fresh"} (age ${age_hours}h)` ``. So on **Wednesday through Monday** — six mornings out of seven — a caveat block appears saying a section is stale when it is **exactly as fresh as its producer is capable of making it.** By Monday it reads 144 hours old.

A surface that flags a false problem every morning teaches its reader to skip caveats. Then the caveat that matters — the one SR-11 and SR-10a exist to raise — arrives on a reader trained for four months not to look.

**Why 0.5d and genuinely low-risk.** Verified: the two contract tests that pin the exact caveat payload — `tests/contract/test_daily_what_changed_api.py:150-164` and `tests/contract/test_daily_what_changed_report.py:542-558` — both assert against **daily** sections (`team_posture` and a generic `_structural_section` helper). **Leave the default unchanged and neither test breaks.** And `basis` is typed `str` in `app/api/routes/league_what_changed_models.py:334` — free-form, so a new value is not a schema change: no OpenAPI regen, no frontend regen, no `rawCssAudit` involvement.

**Files.** `src/dynasty_genius/what_changed/report.py` (`_STALE_THRESHOLD_HOURS` :54; `_section_envelope` :439-469; `_build_league_opportunity_section` :334, which calls the envelope at :349); `tests/contract/test_daily_what_changed_report.py`; read only `frontend/src/what-changed/DailyWhatChanged.tsx` (835-838).

**Steps.**
1. Give `_section_envelope` an optional keyword `stale_after_hours: float = _STALE_THRESHOLD_HOURS` and an optional `basis: str = "captured_at_vs_report_generated_at"`. **Both defaults preserve today's behaviour byte-for-byte for the four daily sections** — that is what keeps the two existing contract tests green without editing them.
2. Add a module constant next to line 54 naming the weekly window and why:
   ```python
   # league_opportunity is a Tuesday-only producer (Weekday 2, 09:35). Judging a weekly
   # artifact against a 24h threshold marks it stale on six mornings out of seven, which
   # is not a staleness signal — it is the cadence. 7 days + a 3h grace matches the
   # grace_hours convention in capture_cadence.json.
   _WEEKLY_STALE_THRESHOLD_HOURS = 24.0 * 7 + 3.0   # 171.0
   ```
3. At `_build_league_opportunity_section`'s envelope call (line 349), pass `stale_after_hours=_WEEKLY_STALE_THRESHOLD_HOURS` and `basis="captured_at_vs_weekly_producer_cadence"`. **Key the threshold off the producer's declared cadence, not off a bigger arbitrary number** — the constant's name and comment must say which producer and which schedule, so the next reader can check it against the plist.
4. **Do not silence the section.** A weekly artifact genuinely 9 days old — because the Tuesday job failed, which is exactly what the Sep 1 / Sep 8 exercises watch for — must still read `is_stale: true`. The point is to make the flag mean something, not to remove it.
5. Confirm the rendered string still reads true with the new basis: *"captured_at_vs_weekly_producer_cadence — fresh (age 48.2h)"*. Honest and self-explaining. No frontend change.
6. Add two contract tests: a `league_opportunity` artifact 48.2h old → `is_stale False` with the weekly basis; the same artifact 200h old → `is_stale True`. **The first must FAIL against today's code.**

**Verification.**
```
./.venv/bin/python3.14 -m pytest tests/contract/test_daily_what_changed_report.py \
  tests/contract/test_daily_what_changed_api.py -q
   → passes, including both new tests, and WITHOUT editing the two existing assertions
     at test_daily_what_changed_api.py:150-164 and test_daily_what_changed_report.py:542-558

./.venv/bin/python3.14 scripts/run_what_changed_report.py
./.venv/bin/python3.14 -c "
import json
d=json.load(open('app/data/what_changed/what_changed_latest_report.json'))
for k,v in d['structural_context']['sections'].items():
    c=v.get('staleness_caveat')
    print(f\"{k:22} {c and (c['age_hours'], c['is_stale'], c['basis'])}\")"
   → today: league_opportunity  (48.2, True,  'captured_at_vs_report_generated_at')
   → after: league_opportunity  (48.2, False, 'captured_at_vs_weekly_producer_cadence')
            and all four daily sections UNCHANGED at (0.4, False, 'captured_at_vs_report_generated_at')
```

**Done looks like.** On a Thursday the Morning Room shows no caveat block for a Tuesday artifact doing exactly what it is scheduled to do — and if that Tuesday job actually fails, the caveat comes back.

---

## DAY 11 (Fri 09-04) — BUFFER · FREEZE at end of day

**Nothing is scheduled here. That is the point.**

Seven of these tickets touch a producer that writes to a store whose gaps cannot be backfilled, four are Tier 2, and the freeze is hard. This day is the answer to the first thing that goes wrong. If nothing has gone wrong by Friday morning, spend it on the pre-freeze checklist and stop early — stopping early is a valid outcome and it is better for goal 1 than filling the day.

**Pre-freeze checklist, whatever else happens:**
```
1.  ./.venv/bin/python3.14 scripts/run_daily_chain.py --dry-run      → six steps, right order
2.  the three-store gap invariant (SR-00)                             → no new date, any store
3.  ./.venv/bin/python3.14 scripts/run_capture_gap_alert.py --dry-run → silent, or names a real thing
4.  launchctl list | grep -c dynasty                                  → 9  (12 original − 6 retired
                                                                        + daily-chain + capture-gap-alert
                                                                        + dynasty-api)
5.  ./.venv/bin/python3.14 -c "import plistlib,glob;[plistlib.load(open(p,'rb')) for p in glob.glob('ops/launchd/*.plist')];print(len(glob.glob('ops/launchd/*.plist')),'parse')"
                                                                      → 9 parse (12 − 6 moved to retired/
                                                                        + the three new plists)
6.  ls ops/launchd/retired/          → six plists + the two snapshots + README
7.  git status --porcelain ops/ app/config/                           → clean
8.  git push origin feature/outcome-loop-week1                        → level with origin
9.  cd frontend && npm run gate                                       → green
10. ./.venv/bin/python3.14 -m pytest tests -q  → ZERO COLLECTION ERRORS (never a pinned count)
```

---

## CONDITIONAL — only if the D9 checkpoint says yes · 1.5d

### SR-18 · A read-only League Activity strip on the Morning Room · L · 1.5d · Tier 0 · **CONDITIONAL** *(NEW — PT-7 replaces SR-17)*

> **CONDITION: ships only if SR-00 through SR-15, SR-19 and SR-20 are all complete by end of day Wed 2026-09-02, AND at least a half-day is banked.** It needs 1.5 days against a 1.0-day buffer, so on plan the answer is no. Unlike the SR-17 it replaces, **this one is severable**: the backend half (steps 1-5) is a section in a generated report that nothing renders, and it is safe to land alone.

**Why it replaces SR-17.** SR-17 would have unclamped xVAR to break the ties at the top of each position — 11 TEs, 6 WRs, 5 RBs and 1 QB sharing a maximum. Its three named consumers are trade `side_value` for `POST /api/trade/analyze` (David trades ~2x a season); `roster_cut_engine.py:171` (`_tier_sort_key`) and `:359` (`active_pool.sort(key=lambda c: _tier_sort_key(...))`); and `league_opportunity_map.py:518` (`sort_value=raw_xvar`, `sort_key="taxi_long_term_value_desc"`).

**The latter two are the exact sites Product Law Ruling 10 names.** The ruling, as approved 2026-08-20: *"composites of ONE lane's own outputs with disclosed construction + stated interval, DESCRIBING A PLAYER, are legitimate. **Ranking ACTIONS by any scalar is not.** Today `league_opportunity_map.py:518` and `roster_cut_engine.py:171,359` sort actions by raw xVAR."* Spending the last 1.5 days of a capture-reliability sprint on a Tier 1 rescale of every xVAR David sees, to improve an ordering the product's own law forbids, is the wrong trade.

**Why this instead.** `league_transactions.db` is the store SR-08 is already recovering, holding a genuinely descriptive record no surface reads today. Measured: `league_transaction_movement` carries 2023:505, 2024:560, 2025:500, 2026:133 rows, with columns `created_at, transaction_type, action, manager_display_name, player_name, position, team` plus pick fields. That is *"rzalika added Isaiah Williams, dropped Ja'Tavion Sanders"* — league news, in his own league, seen every morning, Tier 0, read-only. **It describes events; it ranks nothing.** Ruling 10 is not engaged at all.

**Why it rides the existing report instead of getting its own route.** Verified: no route module under `app/api/routes/` reads `league_transactions.db`. A new route means a new module, new models, a new fetch on the morning open, and new surface to keep honest. The what-changed report already has the right shape — `assemble_structural_context` (`report.py:207-221`) builds five sections from injected paths, each wrapped by `_section_envelope`, each degrading alone. A sixth section costs one builder function and one model field, rides the existing `/api/league/what-changed` fetch, and **inherits SR-20's cadence-aware staleness for free** — as a daily producer (the 06:30 transaction job), a 24h threshold is already right for it.

**Files.** `src/dynasty_genius/what_changed/report.py` (new `_build_league_activity_section`; register in `assemble_structural_context` at 224-240); `scripts/run_what_changed_report.py` (add the db path to `_INPUT_RELATIVES`, 46-59); `app/api/routes/league_what_changed_models.py` (new section model; add the field to `WhatChangedStructuralSections`, feeding `WhatChangedStructuralContext` at :438 — `_Strict` is `extra="forbid"`, so the field is mandatory, not optional-by-omission); `frontend/src/what-changed/DailyWhatChanged.tsx`; tests in `tests/contract/test_daily_what_changed_report.py`, `test_daily_what_changed_api.py`, `frontend/src/what-changed/DailyWhatChanged.test.tsx`.

**Steps.**
1. `_build_league_activity_section(db_path, generated_at)`: open `league_transactions.db` **read-only** (`file:...?mode=ro`, `uri=True` — the pattern every other reader in this repo uses), select the most recent N movements for the current season ordered by `created_at desc`, and return them through `_section_envelope`. Use `max(ingested_at)` from `league_season_capture` as the section's `captured_at` so the staleness caveat is real. **N = 12.** Cap in the producer, not the renderer, and carry an honest total alongside — the discipline `top_movers` / `total_movers_count` already uses.
2. Group by `transaction_id` so a waiver add+drop renders as one line with two names, not two lines. `transaction_type` and `action` are already the right vocabulary; do not invent a friendlier one.
3. **No scores, no ranking, no ordering by anything but time.** No xVAR, no DVS, no "biggest move." Ruling 10 stays disengaged by construction, and that is the point of choosing this ticket.
4. Degrade like every other section: a missing DB → `_unavailable_section`, never a raised exception and never a whole-context failure.
5. Regenerate the contract: `npm run openapi-gen` in `frontend/`, so `types.gen.ts` and `zod.gen.ts` carry the new section.
6. Render a compact strip below the market region. Twelve rows: date + manager + action + player. Reuse existing row primitives; **add no new CSS tokens** — `rawCssAudit` counts them and SR-04 is the only thing between this and a red gate.

**The cut line, if the day runs out.** Steps 1-5 (backend, ~1.0d) land alone and safely: a new section appears in the generated report and in the API response, and nothing renders it. Step 6 (frontend, ~0.5d) is what David sees. **If step 6 cannot finish by Friday afternoon, land 1-5 and stop.** Do not ship a half-rendered strip into a freeze.

**Verification.**
```
./.venv/bin/python3.14 scripts/run_what_changed_report.py
./.venv/bin/python3.14 -c "
import json
s=json.load(open('app/data/what_changed/what_changed_latest_report.json'))['structural_context']['sections']['league_activity']
print(s['status'], s['captured_at'], s['staleness_caveat']['is_stale'], len(s['recent_movements']), s['total_movements_season'])"
   → ok  <within 24h of the last transaction capture>  False  12  <133 or higher after SR-08>

./.venv/bin/python3.14 -m pytest tests/contract/test_daily_what_changed_report.py \
  tests/contract/test_daily_what_changed_api.py -q     → passes

# the section must degrade, not explode
./.venv/bin/python3.14 -c "
import datetime, sys; sys.path.insert(0,'.')
from src.dynasty_genius.what_changed.report import _build_league_activity_section as f
print(f('/nonexistent.db', datetime.datetime.now(datetime.timezone.utc))['status'])"
   → unavailable

cd frontend && npx vitest run src/what-changed/DailyWhatChanged.test.tsx && npm run gate   → green
```

**Done looks like.** The Morning Room shows the last twelve things that happened in his league, in plain language, off a store that was dead until SR-08 revived it — with no score attached to any of them.

---

# WEEK 3 — Sat 09-05 → Thu 09-10 · FROZEN

**No build. Six unmodified capture cycles.** This week exists to find out whether the changes hold, in the only way possible: by letting the schedule run.

**Daily, each morning:**
1. Read the SR-11 notification. **If it is silent, the morning was clean.**
2. Run the SR-00 gap invariant. **No new date may join any list.**
3. Read `app/data/ops/daily_chain_latest_report.json`. Every step `ok`, or a `failed`/`skipped_upstream_failed` that SR-11 already told you about. **A step that failed while the chain carried on is the design working, not a regression** — check that the store it feeds still got its date, because the whole fail-soft argument is that most of them will.
4. `launchctl list | grep dynasty` → 8 dynasty agents plus the API, with the expected exit statuses.

**Tuesday 09-08 is the confirmation, not the only shot.** It is the second post-change Tuesday (Sep 1 was the first, inside the build window). Re-run the Day 8 Tuesday check verbatim and compare. Note the last realized-outcome run on 2026-08-18 wrote `{"status": "failed", "failure_reason": "predictions_load_failed:FrozenPredictionSetUndeclared"}` while `launchctl` reported exit status 0. **If it fails again on 09-08, that is a known-unfixed item (CAP-9, post-kickoff), not a new regression.**

**Watch for the rollover, and know what it looks like.** SR-19 wrote down the expected shape. The 2026 feature window will not have arrived by Sep 10, so the soak will not show it. The first morning it does — on or about Sep 11-14 — expect `feature_refresh` to possibly exit 1 once while nflverse publishes, the chain to carry on, and `run_pvo_refresh` to fall back to the committed feature seed. **Degraded-but-captured, not an outage.**

**Kickoff morning, Thu 09-10:** run the SR-11 alert by hand and the gap invariant. If both are clean, the sprint delivered goal 1.

**Only Tier 0 changes land this week.**

---

# WHAT TO DROP FIRST IF A DAY IS LOST

In order. Do not improvise a different order under pressure.

1. **SR-18** — already conditional and already does not fit. Drop it whole. If half-built, land the backend and stop.
2. **SR-20** — the false staleness alarm. A real honesty harm, but a caveat block on a surface, not a lost day or a wrong number.
3. **SR-16** — the Morning Room hero. A number aimed at the wrong thing is worse than one aimed right and better than a lost capture.
4. **The test half of SR-13** — keep only the strike of the lambda-only edit, in the code's comments.
5. **SR-10a step 3** (the schedule-drift field) — keep step 1, the config block, which closes the alerting hole on the store with four holes.

**Never drop, in any circumstance:** SR-00, SR-02, SR-06, SR-07, SR-09, SR-11, SR-19, and the guard half of SR-14. Each either stops permanent loss on a clock, or is the only reason a loss would be noticed, or prevents a wrong number reaching David on the surface he trusts most.

**If SR-09 cannot land by Fri 08-28:** do not compress it into Mon 08-31. **Drop SR-09 entirely and keep SR-00.** SR-00 already recovers the dominant observed failure at a fraction of the risk; a chain rewrite landing after Sep 1 gets one Tuesday exercise instead of two and half the soak, which inverts its own risk case. Reschedule it as the first item after the freeze lifts, when it can have four uninterrupted soak weeks.

---

# DECISIONS THAT NEED DAVID'S WORD

| # | Decision | Ticket | Why it is his |
|---|---|---|---|
| 1 | **The freeze date 2026-09-04** and the refusal of Tier 3 changes for the rest of the sprint | SR-03 | It is the ruling that makes every estimate here mean anything. Without it, every lane assumes it has until Sep 10 and goal 1 gets no soak. |
| 2 | **Battery sleep: Option A, B, or C** | SR-05 | `sudo`, his laptop, changes power behaviour for every use of the machine. |
| 3 | **`launchctl load` the API agent** | SR-12 | Standing repo convention: agents commit plists, David loads them. |
| 4 | **SR-18 go/no-go at the Wed 09-02 checkpoint** | SR-18 | It is the only thing that would fill the buffer day before a hard freeze. The default is no. |

**Not a decision, but he should be told:** SR-00 edits two live LaunchAgent schedules on Day 1. Tier 2 by classification, reversible in seconds by construction (both plists tracked and symlinked). It is the one Tier 2 change that does not wait for SR-02, and the reason is in its ticket.

**Deferred — named so he can see them coming, not asked now:** the Engine B P90 refresh (Tier 1, rescales 27,021 archived DVS rows); the `market_divergence_rebase` cutover (rewrites ~37% of divergence classifications); cloning the 10.89 GB DynastyProcess repo; a GCS lifecycle/retention policy (destroys older backup runs — irreversible, his bill); indexes on the capture DBs (a schema write to the irreplaceable stores); retiring the `/api/league/morning-tape` route (a visible surface removal); changing `roster-capacity-audit` from weekly to daily.

---

# DEFERRED TO THE OFF-SEASON ARCHITECTURE PROGRAM

### Dropped or deferred THIS revision
- **SR-17 · unclamp xVAR — DROPPED, not merely deferred.** Two of its three named consumers (`roster_cut_engine.py:171,359` and `league_opportunity_map.py:518`) are the exact sites Ruling 10 says must not be ranked by a scalar; the third is trade side-value, reached ~2x a season. **If it is ever revived, revive it with the Ruling 10 question answered first.** Its measurement survives in SR-13: TE n=111 distinct=94 max=2.85 ties_at_max=11; WR 6; RB 5; QB 1 — 22 of the most tradeable assets in the league carrying no distinguishing value.
- **SR-10b · event-stream freshness for `league_transactions` and `nflverse_usage`.** Needs a new store kind: `CadenceStoreConfig` is `extra=forbid` with `expected_cadence: Literal["daily"]` and eight mandatory daily-timeline fields. `league_transaction.created_at` is sparse event time — a quiet day is healthy; `nflverse_capture` is keyed `stream:season` and not date-partitioned. ~1.0-1.5d of model surgery plus a second analyzer path. Cost of deferring: those two stores stay unmonitored this season.

### The replay program — the hardest cut, ~6+ honest days
- **RPL-1** trade replay engine (all 39 trades, honest per-trade status — only 21 are fully groundable today). **RPL-2** read-only `GET /api/replay/trade-replay`. **RPL-3** Trade Replay panel inside Model Trust. **RPL-4** 2024 feature-season bridge (21 → 30 trades; pulls seven seasons of nflverse over the network on the machine that must capture reliably for 17 weeks).
- **Goal-3 FIX-1** trade parity absolute floor (the evaluator names a winner on 0.11 vs 0.00 xVAR). Needs David to pick the constant.
- **Goal-3 FIX-2** ceiling-clamp surfacing in trade math. **With SR-17 dropped this is now the live version of the TE-ceiling question** — annotating the tie honestly is Tier 0 disclosure, where removing it was a Tier 1 rescale. Prefer this one when the program restarts.
- **Goal-3 FIX-3** TE headroom measurement — its finding already lives in SR-13.
- **MKT-1 / MKT-2** DynastyProcess probe and consensus lane. Zero of 39 trades have a local point-in-time market snapshot; the PICK question may collapse the deliverable to ~5 usable trades.

**Cut because it contributes nothing to goals 1 or 2 and is not calendar-gated by kickoff.** Build it in weeks 1-4 of the season. Start with RPL-1.

### Capture and ops
- **CAP-8** backup retry + staging-leak fix. SR-11 already alerts on `status != completed`, 90% of the value. *Delete the two orphaned staging dirs by hand — `app/data/ops/backup_staging/20260801T141848Z` and `20260812T141500Z`, 4.2 GB, two minutes, not a ticket.*
- **CAP-9** outcome-loop cadence (weekly → idempotent daily). First real in-season run is **Tue Sep 15, after kickoff**, and it is a Tier 2 launchd change that must not land inside the soak window. **First item post-kickoff.** Includes the 2026-08-18 `FrozenPredictionSetUndeclared` failure, which the Sep 1 and Sep 8 checks watch but do not fix.
- **CAP-10** status markers frozen at 2026-08-08 — **deleted as a failure mode, not deferred** (SR-10a step 4).
- **CAP-11** GCS retention (~404 GB over a season). Needs David's irreversible word. **CAP-12** `preflight_season.py` — SR-11 runs the same inspectors daily; a second entry point is duplicate surface.
- **RISK-1** back up `league_transactions.db`. **Premise falsified by SR-08** — the exclusion is correct. Do not do this.
- **RISK-3** cadence-model correction. The true split (nine daily, three Tuesday-weekly) is recorded in SR-03 for free.
- **NEW · retire `ops/launchd/retired/`.** SR-09 step 7 parks six plists there and forbids deleting them before the freeze lifts. **On this list so it actually happens** rather than sitting in the repo for a year.

### Correctness
- **FIX-3** valuation-constants provenance stamp — only needed if a constant changes, and SR-13 blocks the only proposed change.
- **FIX-4** Engine B P90 refresh — under 1% effect on every unclamped player; rescales 27,021 archived DVS rows mid-season.
- **FIX-5** leakage regex — a real defect with **zero season exposure**; no training run happens before February.
- **FIX-6** divergence-rebase shadow artifact — it edits the same 09:40 producer SR-09 is rewiring.
- **FIX-7** NDCG bootstrap defect — no decision turns on it, and a 3x narrower interval still straddles zero by 5x.
- **FIX-8** cross-version pickle golden vectors. *Pin the sklearn version in `requirements.txt` — two minutes, not a ticket.*
- **NEW · `universe_pvo_batch.py:99` — `dvs_pct` is populated for zero of 468 players.** Surfaced by SR-14 step 3 and explicitly out of scope there. It is why `xvar_percentile_position` is null on every row that carries an xVAR. Fix upstream, then revisit SR-14's column mapping.
- **NEW · the `posture_label` contradiction.** `team_posture.david_posture = REBUILDING` against `team_value.david_value_summary.posture_label = UNCLASSIFIED`, both on the same morning surface. **First post-kickoff correctness item on a surface.**

### Surfaces
- **MR-4 / CAP-7** the `stores[0]` pick at `DailyWhatChanged.tsx:601` (exactly one site; the two draft tickets were literal duplicates). Cut because SR-11 reaches David without him opening anything.
- **MR-5** staleness cadence — **NO LONGER DEFERRED. Promoted to SR-20** and shipping on D10. Revision 1 cut it and then, three sections later, listed the resulting harm under what David does not get.
- **MR-6** market_divergence store registration — **absorbed into SR-10a**. **MR-8** — **absorbed into SR-15**.
- **MR-7** League Activity section — **promoted to SR-18** as the conditional item, replacing SR-17.
- **MR-9** drop the ranked-action payload (`partner_score`, `cut_priority`). **First S-sized item to add back if a day frees up** — and note it is the *same* Ruling 10 surface SR-17 was dropped over, approached from the honest direction.
- **MR-10** transaction capture status artifact — its three halves are SR-07, SR-10a, and the deleted CAP-10. **MR-11** movement-history chart — a chart, not a loss or a wrong number. **MR-12** retire the Morning Tape route (returns 503 permanently, no producer) — needs David's word for a visible surface removal.

### Performance
- **PERF-1** capture-store memo (10 full-index scans per app open → 2). Real, S, pure Tier 0. **The first thing to land after kickoff.** Cut only because SR-12 makes the app openable at all, which outranks making it fast.
- **PERF-2** single `/api/health` fetch — value depends on PERF-1. **PERF-3** artifact-read memo — M, and its 0.72s cost lands on Trade Lab. **PERF-5** Sleeper player-map cache — M, touches the network layer. **PERF-6** atomic artifact writes — 43 ms/day of exposure; *three lines, do it when someone is already in that file.* **PERF-7** indexes on the capture DBs — a schema write to the irreplaceable stores mid-season.

---

# TWO THINGS THIS SPEC DOES NOT COVER — stated plainly

1. **RISK-7 through RISK-10 were never visible.** The draft ticket list handed to sizing was truncated mid-RISK-6, so roughly four risk tickets appear in neither the keep nor the cut list. One (RISK-9, the failing realized-outcome scorer) is covered by moving CAP-9 to the post-kickoff window. **The other three need the same sizing pass before anyone assumes this list is complete.** Unchanged from revision 1 and still true.

2. **The draft ticket IDs collided.** `FIX-1` appeared three times and `FIX-2`/`FIX-3` twice each, under different areas. Every ticket above is renumbered `SR-nn`, unique, with its draft id in parentheses. **Revision 2 note:** `SR-10` no longer exists as an id — it is `SR-10a` (shipping) and `SR-10b` (deferred). `SR-17` no longer exists as a shipping ticket. Do not re-use either number.

---

# CHANGELOG — revision 2, 2026-08-20

Four independent pressure tests were run against revision 1 (usefulness, risk-inversion, estimate realism, strategic frame). They returned 6 CRITICAL findings and graded estimate realism FLAWED. All eight amendments are applied above, in the ticket bodies and the schedule. This section records what changed and why; it does not restate the tickets.

| # | Change | Where | Why |
|---|---|---|---|
| **PT-5** | **NEW SR-00 · same-day retry insurance.** `StartCalendarInterval` arrays adding 11:30 and 14:00 to the market-divergence and model-pvo plists. Day 1, first. | New ticket, D1 | The dominant observed loss is a **prior-date abort** — recorded twice in `market_divergence_refresh.out.log`, both on the most-delayed capture mornings. `run_market_divergence_refresh.py:166-217` reads the market side from the **DB-resident** FC snapshot with no network call, so a same-day rerun recovers it completely. Provably a no-op: `market_divergence_history` is an idempotent upsert on `(player_id, capture_date)` (:393-415) and `model_forward_capture` is `INSERT OR IGNORE` with `artifact_vintage` already excluded from the immutability signature *specifically* so re-runs are no-ops (`model_forward_capture_store.py:53-55`). `man launchd.plist` confirms an array of dictionaries is valid; no plist in this repo uses that form yet, so SR-00 validates it in both `plutil` and `plistlib` before loading. Both targets are already tracked and symlinked, which is why it can go first without waiting on SR-02. |
| **PT-2** | **SR-11 moved from D7-D8 to D4**, ahead of SR-09. | Schedule; SR-11 and SR-09 | Revision 1 scheduled the only detection channel this product will ever have *after* the change that retires six LaunchAgents, leaving 4-5 live capture mornings with a brand-new single point of failure and no notification. Detection precedes risk. SR-11 also gained failure class (c): a chain step recorded `failed` or `skipped_upstream_failed`. |
| **PT-2b** | **SR-09 must land by end of D6 (Fri 08-28)**, before Tue 09-01. | Schedule; SR-09 deadline box; new Day 8 Tuesday check; freeze rationale rewritten | Revision 1 claimed "Sep 8 is the ONLY post-change Tuesday" — true only because of its own sequence. **Aug 25 and Sep 1 are inside the build window.** Landing SR-09 before Sep 1 gives the three Tuesday-only jobs **two** post-change exercises, the first inside the window where a finding is still a fix. The Day 8 check is concrete: compare `league_opportunity_latest.json`'s `captured_at` against the chain report's step-4 finish, because `league-opportunity-map` fires at a fixed 09:35 into a chain whose internal timing is no longer pinned. |
| **PT-4a** | **SR-09 rewritten to FAIL SOFT**, with a named dependency table. Only one hard edge: `fc_forward_capture → market_divergence_refresh`. | SR-09 "why it must fail soft", the edge table, steps 2-4, two new proof commands | Not a preference — a measurement. `feature_refresh.out.log` records **two** `refusing to publish` exits (lines 36 and 47; `run_feature_refresh.py:179` and `:344`), both GitHub asset timeouts. **On both mornings nothing downstream was lost**, because `resolve_feature_source` (`feature_source.py:66-76`) already falls back to the committed seed and `resolve_pvo_source` does the same one layer up. A wholesale-halt chain would **override a designed fallback** and turn a handled degradation into a permanent hole in `model_forward_capture` and `market_divergence_history`. A rewrite that is worse than what it replaces on the failure mode that has actually occurred is not a fix. |
| **PT-4a′** | **SR-09 step 7 no longer destroys its own rollback.** The six retired plists are `git mv`'d to `ops/launchd/retired/` with a pre-change `launchctl` and `plutil` snapshot, and must survive the freeze. | SR-09 step 7 + verification; a post-freeze chore added to the deferred list | Revision 1 said "remove their plists in the same change," contradicting its own Tier 2 definition four tickets earlier. Six of the twelve installed agents are **copies, not symlinks**, so deleting the repo files leaves no recoverable original anywhere — rollback would mean git archaeology during a freeze. |
| **PT-4b** | **NEW SR-19 · season-rollover rehearsal**, 0.25d, on D8. | New ticket; SR-09 step 8 makes it a closing condition | All six soak cycles run **before a 2026 game exists**, so the rollover structurally cannot be exercised. `run_feature_refresh.py:336-350` derives `season_end` dynamically and its own comment names *"the post-kickoff September edge."* The rehearsal is cheap because `--season-end` and `--runtime-dir` are both real flags (:285, :293-300): force 2026 against a scratch runtime, record which of three outcomes happened, and run the chain through a **real** refusal rather than a stubbed one. |
| **PT-3** | **SR-10 split. SR-10a** (register `market_divergence_history` only, 0.5d) ships; **SR-10b** deferred. **Cross-lane blocker flagged for D1.** | SR-10a ticket + blocker box; SR-10b in the deferred list with its cost | 1.5d was ~2x understated: `CadenceStoreConfig` is `extra=forbid` with `expected_cadence: Literal["daily"]` and eight mandatory daily-timeline fields, and neither event store fits without a new store kind. Meanwhile `market_divergence_history` — **the store with four measured holes** — is a plain daily `capture_date` table the analyzer handles unmodified. Separately, the ticket's four primary files are dirty with another lane's `BUILD-3` work (+124/+11/+20/+16 lines), so the conversation opens on D1, not D7. **Also corrected: revision 1 claimed the config has "no top-level `in_season_months`." It does — `[9,10,11,12,1]` — and it disagrees with both market producers, which use Aug 16 – Jan 15.** |
| **PT-1** | **SR-14 amended (non-negotiable) and resized 0.5 → 0.75d.** Guard at `daily_diff.py:354`: skip when either side's `xvar` is `None`. | SR-14 steps 4 and 7, plus a dated fabrication check in its verification | Without it, the morning after SR-14 lands the Morning Room reports **~468 model moves that did not happen**. `_float` at `daily_diff.py:494-495` coerces `None → 0.0`, `count(xvar)` is 0 on every existing capture date, and the runtime carries exactly 468 non-null xVARs. `daily.model.status` would flip `vintage_changed_no_score_delta → ok` and `ModelRegion` (`DailyWhatChanged.tsx:629,646`) from "Projections held steady" to a wall of rows. **The soak instruction cannot catch this** — 468 fabricated deltas add no missing date. The guard goes at the call site, not in `_float` (four other callers), and keeps `xvar_delta: float` non-Optional to avoid a schema/OpenAPI/frontend regen for zero gain. |
| **PT-6** | **SR-16 re-aimed** from `total_movers_count = 456` to his own `roster_deltas`. | SR-16 rewritten; same 0.5d | 456 is league-wide churn across 12,222 players — a bigger number, not a better one, and wallpaper by week three. The same payload carries **26 roster rows, all non-zero** (Tank Dell +139, Chris Bell +113, Fernando Mendoza −84) at `daily_diff.py:145-149`. **Added precision the amendment did not state:** `roster_deltas` includes flat players by design (its own comment: *"even if flat"*), so the hero must count `value_delta !== 0`, not `.length` — otherwise it prints a near-constant 26 and reinvents the same defect. 456 survives as the honest secondary line. `ValueHero`'s props are three strings, so no component change and no new CSS tokens. |
| **PT-7** | **SR-17 DROPPED. NEW SR-18 · read-only League Activity strip** takes its conditional 1.5d. | SR-17 removed from the schedule and moved to the deferred list with its reason; SR-18 written as a new conditional ticket | SR-17's three named consumers are trade side-value (~2 trades/season) and two sites Ruling 10 explicitly names — `roster_cut_engine.py:171,359` and `league_opportunity_map.py:518`. Improving an ordering the product's own law forbids, via a Tier 1 rescale of every xVAR David sees, is the wrong last 1.5 days. SR-18 is Tier 0, read-only, seen every morning, and **ranks nothing**. It rides the existing what-changed report (no route module reads `league_transactions.db` today) so it costs one builder function and one model field instead of a new API surface, and inherits SR-20's staleness handling. **Unlike SR-17 it is severable**, with a stated cut line. |
| **PT-8** | **NEW SR-20 · cadence-aware staleness**, 0.5d, on D10. | New ticket; MR-5 promoted out of the deferred list | `league_opportunity` is a Tuesday-only producer judged against a flat `_STALE_THRESHOLD_HOURS = 24.0` (`report.py:54`), so it reads `is_stale: true` on **six mornings out of seven** — measured at 48.2h against four sibling sections at 0.4h — and renders as a caveat block at `DailyWhatChanged.tsx:835-838`. **This is the mechanism by which a daily habit dies.** Revision 1 cut it and then listed the resulting harm under "what he does not get." Verified low-risk: the two contract tests that pin the caveat payload both assert against *daily* sections, so keeping the default unchanged leaves them green untouched, and `basis` is a free-form `str` — no schema change. |

### Budget effect

```
  9.75  revision 1 committed (against 11 available, 1.25 buffer)
+ 0.25  SR-00  NEW
- 1.00  SR-10 → SR-10a  (1.5 → 0.5); SR-10b deferred
+ 0.25  SR-14  amended (the None-guard and its regression test)
+ 0.25  SR-19  NEW
+ 0.50  SR-20  NEW
─────
 10.00  revision 2 committed (against 11 available, 1.00 buffer, D11 unallocated)
```

The conditional line is unchanged in size: SR-17's 1.5d left it and SR-18's 1.5d took it. Neither was ever in the committed total. **SR-18 does not fit inside the 1.0-day buffer and the D9 checkpoint's default answer is therefore no** — stated plainly rather than left as an implication, which is the failure mode revision 1's SR-17 checkpoint had.

### Two of revision 1's own verified facts were wrong, and are corrected above
- SR-10's step 4 asserted `capture_cadence.json` has **no** top-level `in_season_months`. It has one: `season_windows.in_season_months = [9,10,11,12,1]`. The real problem is that it disagrees with `fantasycalc_adapter.py:39-47` and `run_market_divergence_refresh.py:106-110`, both of which use Aug 16 – Jan 15 — so **today the market producers consider it in-season and the cadence config does not**, and the store is watched with the lenient off-season threshold while it moves daily.
- SR-02's step 3 gave the backup-manifest directory shape as two fields. The live shape has three: `{'path': ..., 'required': True, 'kind': 'directory'}`.

### What was deliberately NOT changed
- **The freeze date.** 2026-09-04 EOD stands. Every amendment tightens the sequence inside the window rather than asking for more of it.
- **The verification-command discipline.** Every ticket carries an exact command and an expected result, and every number was re-measured against the live repo on 2026-08-20 rather than carried forward from revision 1.
- **The honest "what he does NOT get" section**, which now also names the `posture_label` contradiction and SR-10b's unmonitored stores rather than letting them vanish into a deferred list.
- **The retracted TE lambda edit stays retracted.** SR-13 is unchanged in substance and now strikes it in the code's own comments rather than only in a document, because the retraction lives in `SEASON-BRIEF.md` and the constants live in `engine_b_contract.py`, and only one of those is where the next agent will be standing.