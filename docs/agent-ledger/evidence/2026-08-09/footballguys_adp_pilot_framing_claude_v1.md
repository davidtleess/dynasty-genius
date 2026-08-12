# Footballguys `adp.csv` pilot — framing v1 (Claude, implementing lane)

Date: 2026-08-09 (session **reopened** after the team closeout at `ca90450`; `02` §Flush vs terminal close)
Authority: David's word on the board — *"next session starts with the football guys pilot"*.
Scope of this artifact: **framing only.** No code, no RED, no intake, no landing, no scheduler.
Predecessor investigation: `footballguys_web_only_data_investigation_claude_v1.md` (same directory).

**Layer: 1 (ingest).** The `05` §3 Rule-2 layers-1–2 dependency check is scoped to work at layers
3–6; this work *is* at layer 1, so the check does not apply and is not manufactured here.

---

## 0. THE HEADLINE — the file is not what its name says, and this is measured

`adp.csv` does **not** contain average draft position. It contains **ordinal rankings**.

Measured this session from the bundle in David's Downloads (`DraftDominator_v2026i.zip`,
`DraftDominator.app/Contents/Resources/adp.csv`, zip entry stamped `08-05-2026 20:57`):

- **30,388 bytes**, SHA-256 `1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9`
- **608 data rows, 608 distinct ids** (zero duplicates), **19 columns** = `id` + 18 `adp_*` markets
- **5,166 populated cells. Zero decimals. Zero non-numeric values.**
- **Every one of the 17 populated columns is a perfect dense permutation `1..N`** — no gaps, no ties,
  min exactly 1, max exactly equal to its own populated count.

| Column | n | range | gaps | tied values |
| :-- | --: | :-- | --: | --: |
| `adp_consensus` | 519 | 1–519 | 0 | 0 |
| **`adp_sleeper-sf`** | **500** | **1–500** | **0** | **0** |
| `adp_nffc` | 467 | 1–467 | 0 | 0 |
| `adp_sleeper-1qb` | 435 | 1–435 | 0 | 0 |
| `adp_draftkings-bestball`, `adp_underdog` | 405 | 1–405 | 0 | 0 |
| `adp_mfl` | 340 | 1–340 | 0 | 0 |
| `adp_drafters` | 277 | 1–277 | 0 | 0 |
| `adp_rtsports` | 264 | 1–264 | 0 | 0 |
| `adp_bestball10s`, `adp_fbgoc`, `adp_ffpc` | 250 | 1–250 | 0 | 0 |
| `adp_cbs` | 231 | 1–231 | 0 | 0 |
| `adp_yahoo` | 218 | 1–218 | 0 | 0 |
| `adp_espn` | 212 | 1–212 | 0 | 0 |
| `adp_sleeper-sf-rookie` | 77 | 1–77 | 0 | 0 |
| `adp_sleeper-1qb-rookie` | 66 | 1–66 | 0 | 0 |
| **`adp_sleeper-redraft`** | **0** | — | — | — |

**Why this is decisive rather than pedantic.** A true ADP is a mean of observed draft slots. Across
hundreds of drafts it is dense with decimals and it *ties* — two players genuinely go at 45.3 and
45.3. A perfect gapless duplicate-free permutation over 500 players cannot arise from averaging, and
rounding an ADP to integers would produce ties, not eliminate them. The app is shipping **the rank
order derived from ADP, with the price discarded**.

**What was lost with the price: the spacing.** Rank says Player 12 is ahead of Player 13. ADP says
whether that gap is half a round or four rounds. Spacing is the part of a market signal that is not
already in every consensus ranking we hold — so the file's value proposition is materially weaker
than the predecessor investigation assumed when it recommended `adp.csv` on the strength of it being
*"a second independent market lane beside KTC/DynastyProcess"*. **That recommendation was made
without this measurement, and I am the lane that wrote it.**

**Second measured defect: `adp_sleeper-redraft` is a declared column with 0 of 608 populated.** The
schema announces a market that carries no data at all. Any intake that reports coverage from the
header rather than from counted cells will report a lane we do not have.

---

## 1. The concrete user situation this would serve

David plays one Superflex PPR dynasty league. `adp_sleeper-sf` is the only column in the bundle
matching his format, at 500 of 608 rows.

The honest statement of the moment it serves: **when he is looking at our model's value for a player
and wants a second read on where the market has him**, beyond KTC (a trade market) and
`dynastyprocess_ecr_2qb` (an expert-consensus conversion). This is the market side of the standing
value-margin thesis.

**But name the horizon problem out loud.** ADP — even as a rank — is a **redraft/best-ball drafting**
artifact from seasonal markets (ESPN, Yahoo, NFFC, Underdog, DraftKings best-ball). `00` §Separate
Dynasty And Redraft is a mandatory protocol, not a caveat. `adp_sleeper-sf` is a Sleeper Superflex
draft position; whether those drafts are dynasty startups or seasonal Superflex redraft is **not
established by anything in the file**, and the distinction decides whether this is a dynasty market
signal at all. **Unresolved, and it is a gating question rather than a footnote.**

## 2. Mislead / nudge risks — verdict by the back door

1. **Semantic laundering by field name.** Storing these under `adp_*` would propagate "average draft
   position" through every downstream reader for as long as the store exists. The column is a rank.
   It must land under a name that says rank, or with a declared semantic that a consumer cannot miss.
2. **A rank is one sort away from a recommendation.** `00` §No-Verdict Line: a default order tied to
   an undisclosed basis functions as a hidden recommended-action order. A 1..500 market rank is
   *exactly* that shape, and it is more tempting than a price because it is already ordered.
3. **Dense integers read as precision.** Rank 47 vs rank 48 looks like a measured difference. It is
   an ordering artifact of a discarded average, and the underlying ADP gap may be nil.
4. **Cross-market rank arithmetic is invalid and will look reasonable.** Averaging `adp_espn` (212
   deep) with `adp_sleeper-sf` (500 deep) mixes two different denominators; the same player's rank
   means different things in each. Any composite across these columns is a defect.
5. **Coverage asymmetry becomes a value signal.** A player ranked in 3 of 17 markets is not worse
   than one ranked in 17 — he may be an IDP/rookie-market artifact. Absence is missingness, never a
   low score.
6. **`00` §KTC/market ruling is absolute here.** Overlay only. This may never enter Engine A or B.

## 3. Candidate falsification seeds for the RED

Behaviours, then mathematical boundaries. Codex owns final RED authorship.

**Provenance and raw evidence**
- F1: provenance is **declared by David**, never inferred. Filename, zip mtime, and the bundle's own
  `08-05-2026` build stamp are all **rejected as provenance** — they date the *build*, not David's
  retrieval. Intake must refuse without a declaration.
- F2: raw bytes + SHA-256 + byte count + schema hash persisted **before** parsing; a mismatch on
  re-intake refuses rather than overwrites (the B21 `529a3e5` fail-closed lesson: verify the payload,
  do not trust the metadata about it).
- F3: re-intake of the identical file is idempotent; re-intake of a *changed* file under the same
  declared version refuses loudly.

**Schema and coverage**
- F4: the empty `adp_sleeper-redraft` column must survive intake as an **evidenced zero**, and must
  not be dropped (silently losing a declared lane) nor reported as present.
- F5: coverage is **counted per column with its denominator**, never derived from the header.
- F6: **do not encode the dense-permutation property as a contract.** It is an observed property of
  this vintage. A future bundle may tie or gap; an intake asserting permutation would refuse valid
  data. Measure it and record it — the RED must include a fixture that ties and one that gaps, and
  both must be **accepted with the property recorded as false**.
- F7: a decimal value must be accepted (it would mean the provider started shipping true ADP) and
  must flip the recorded semantic, not crash and not silently truncate.

**Identity**
- F8: `id` is PFR-style (`GibbJa00`, `RobiBi01`, `ChasJa00`); this repo carries `pfr_player_id` on
  the nflverse `pfr_*` and `snap_counts` streams. Resolution is measured as
  **resolved / 608 with the unresolved ids listed** — never a bare percentage. `01` §Identity
  Resolution: unresolved rows go to triage, they are not silently scored.
- F9: a duplicate `id` in a future vintage must refuse, not last-write-win. (This vintage: 608/608
  distinct.)

**Redundancy — the check that decides whether this is worth anything**
- F10: Spearman + top-24 overlap of `adp_sleeper-sf` against KTC and `dynastyprocess_ecr_2qb` on the
  resolved intersection, with the intersection size stated. **The `ff_rankings` precedent is the
  direct one and it is now sharper: that comparison came back at Spearman .99 and the stream was
  ruled `blocked_for_use`. Because this file is a rank rather than a price, it is comparing
  like-to-like with ECR and is therefore *more* exposed to that outcome, not less.**
- F11: pre-register the redundancy threshold **before** running it. A materiality result chosen after
  seeing the number is not a result.

**Disposition**
- F12: landing disposition is recorded at landing (`blocked_for_use` / `substrate_only`) with its
  reason, per the `ff_rankings` and `contracts` precedent.
- F13: if it ever lands, `app/config/backup_manifest.json` coverage and the **landing-order law** —
  *the manifest entry and the first capture land together, or the manifest entry does not land*
  (this fired for real on 2026-08-09 with `cfbd_fbs_schedules`).
- F14: licence — Footballguys ToS §1 bars reproduction/redistribution. Anything ingested stays in a
  gitignored private store and reaches no public surface. **Raw CSV bytes must never be committed.**

## 4. Overclaim check against the No-Verdict Line

- Everything here is **market/consensus data**: overlay only, `decision_supported=False`,
  never an Engine A/B feature (`00` §KTC, `01` §Engine B).
- No named tier, no verdict vocabulary, no buy/sell/hold, no recommended order.
- The pilot ships **no David-facing surface**. Its entire output is measured evidence and a
  disposition.
- The changelog cadence figure carried forward from the predecessor investigation
  (**off-season median 7 days, n=159**) stands as evidenced; its **in-season median of 4 days is
  WEAK (n=8, biased by 11 rejected "Sept" spellings)** and must not be cited as a cadence.
- **H2 QB rushing remains a registered hypothesis UNDER TEST with no result.** Nothing here bears
  on it.

## 5. What I am asking Codex to attack

1. **Is the rank-not-ADP conclusion wrong?** Steelman a mechanism by which averaging produces a
   gapless tie-free permutation over 500 players. If one exists, the framing's headline collapses.
2. **Does the pilot still earn its build?** Given the price is gone and F10 may well return ~.99
   against ECR, is the honest recommendation to run the redundancy check **first, standalone, off
   the scratch copy** — and only build intake if it survives? That inverts the predecessor
   investigation's order, and it is my current position.
3. **Is the dynasty-vs-redraft horizon question (§1) a gate or a caveat?**
4. Anything in §3 that would pass against broken code — the failure species that accounted for
   every one of your eight review findings on 2026-08-08.

## 6. What has NOT happened

No repository file edited beyond this artifact. No intake, no store, no RED, no code. No scraping, no
provider contact, no download, no account interaction. Nothing executed from the bundle; one text
file extracted read-only to a session scratch directory. No David-declared provenance exists yet —
and without it, F1 means intake cannot run at all.
