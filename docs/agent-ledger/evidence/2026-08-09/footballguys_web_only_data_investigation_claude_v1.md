# Footballguys / web-only data — independent investigation (Claude)

Date: 2026-08-09
Scope: **read-only investigation, no write scope.** No scraping, no download, no account or site
state changed, no provider contacted, no downloaded app/macro/installer executed, no repository file
edited. Local inspection + official-page research only.
Layer: 1 (ingest) for the acquisition question; the constitutional finding lands on `00`/`01`.
Formed independently: I did not read the other lane's Footballguys artifacts before writing this.

## 1. What is actually in the Downloads folder (measured, 2026-08-09 00:02–00:03)

| File | What it is |
| :-- | :-- |
| `DraftDominator_v2026i.zip` (8.5 MB) | A **macOS `.app`** bundle — and the important one |
| `2026app_I1.xls` (3.5 MB) | The **VBD Excel App**; `file` reports Title "VBD Excel App", Author David Dodds, Excel/Windows compound document |
| `MI2026a_Setup.exe` (2.6 MB) | **PE32 Windows executable — cannot run on this Mac at all** |
| `Printable NFL Schedule Grid 2026 - Footballguys.pdf` | Print artifact |
| `Cheatsheet for Redzone Champions League.pdf` + `- rookies.pdf` | **League-customized** cheatsheets |
| `dynasty_trade_values (1).csv` / `.xlsx` | 479 rows: `Player, Team, Age, Position, Value` — no provenance, no timestamp, no source stamp |

## 2. The decisive finding: the data is already local, as plain CSVs

The `.app` bundle ships its data as ordinary text files in `Contents/Resources/` (listed from the
archive; **only text files were extracted, to a scratch directory; no binary was extracted and
nothing was executed**):

| File | Size | Content (measured from the header row) |
| :-- | --: | :-- |
| `projections.csv` | 260 KB | **1,546 rows × 68 columns** — full stat projections: pass/rush/rec/kick/IDP, per-week start flags 1–17, `GP`, `age`, `exp`, return yardage |
| `adp.csv` | 30 KB | ADP across **18 distinct markets**, including `adp_sleeper-sf` and `adp_sleeper-sf-rookie` — **Superflex**, which is David's format |
| `adp_idp.csv` | 91 KB | IDP variant |
| `comments.csv` | 442 KB | Staff analyst commentary with `staff_id`, `staff_name`, `rank`, `pos`, **`comment_ts` (unix)** and body text |
| `SOS.dat`, `NFLSchedule.dat`, `dc.raw` | 43/6/84 KB | Strength of schedule, schedule, cheatsheet raw |
| `ReadMe.txt` | 58 KB | A **15-year changelog** (below) |

**The player id is PFR-style** — `AchaDe00`, `GibbJa00`, `AlleJo01`. That is the Pro-Football-Reference
identifier format, and this repo already carries `pfr_player_id` on the nflverse `pfr_*` and
`snap_counts` streams. Identity resolution against our canonical `player_id` is therefore a join we
already know how to do, not a fuzzy-name problem.

**Nothing about this slice requires the web, an agent, or a browser.**

## 3. The changelog answers a cadence question we have failed to close elsewhere

Parsed from `ReadMe.txt`: **198 "Updated: Projections to …" entries, 187 parsed, 183 distinct dates,
spanning 2011-07-05 → 2026-08-05.**

- **Off-season: median gap 7 days** (n=159; modal gap exactly 7, with 48 occurrences).
- **In-season (Sep–Dec): median 4 days (n=8) — WEAK, and stated as weak.** The 11 entries my parser
  rejected are *all* non-standard `Sept N` spellings, i.e. **September dates**, so the in-season
  sample is both small and biased by exactly the months it is meant to describe. Treat the weekly
  off-season figure as evidenced and the in-season figure as indicative only.
- 15 annual dormancy gaps, median 282 days — the between-seasons quiet period.

This is a **provider-published rhythm**, evidenced from the provider's own artifact — the class of
fact the A-C inventory has been unable to obtain for PlayerProfiler or Sleeper. It came free, from a
file already on the laptop.

## 4. Possible vs permitted — and this is the part that decides the approach

**Footballguys' Terms of Service prohibit automated collection outright.** §13 (Prohibited Uses)
bars using the site "to spam, phish, pharm, pretext, **spider, crawl, or scrape**". §1 bars
reproduction, duplication, copying, sale or exploitation of site content without express written
permission. (<https://www.footballguys.com/terms>)

So the question "how do we use AI to get web-only data from Footballguys" has a **contractual**
answer, not a technical one: **we don't scrape it.** No amount of Cowork/Codex/Gemini capability
changes that, and an AI browser agent driving his logged-in session is the same prohibited act with a
different user agent. It would also put a paid account he wants to keep at risk.

**The sanctioned channel already exists and is better than scraping anyway:** the subscriber app's
own "Get Latest Projections" refresh, and the versioned bundle download, both of which land the same
CSVs locally as a first-party product feature.
(<https://www.footballguys.com/article/fantasy-football-tools>)

**No public API or data-licence offering surfaced** in official material. If David ever wants true
automation beyond the app's own refresh, the permitted path is to **ask them for written permission
or a data licence** — a David action, not an agent action.

## 5. What this data is, under our own constitution — the trap worth naming

Almost all of it is **opinion and market data, not ground truth**:

- **ADP** is market data → `00` §KTC ruling: overlay only, never an Engine A/B feature.
- **Projections are expert consensus** → `01` §Engine B explicitly disallows "expert consensus as a
  model feature". They *look* like data because they are numeric; they are opinions with decimal
  points.
- **`comments.csv` is analyst prose** → the 35% qualitative lane, and the standing locked ruling
  keeps analyst material documentary rather than a model input.

This does not make it worthless — it makes it a **market/consensus overlay and a qualitative-context
source**, which is exactly the lane the value-margin thesis needs on the market side. It must simply
never be confused for fuel. The one genuinely *factual* item in the bundle is the NFL schedule, and
we are already capturing that from nflverse under B21.

## 6. Recommended first pilot — small, sanctioned, and it proves one thing

**Pilot: a declared-provenance intake for ONE file — `adp.csv` — from a bundle David has already
downloaded.**

Why `adp.csv` and not the projections: it carries the **Superflex** market columns, which is the only
slice with a plausible near-term use (a second independent market lane beside KTC/DynastyProcess), it
is small, and it is unambiguously overlay-only so the pilot cannot accidentally reach a model.

**Copy the pattern we already shipped — do not invent one.** `src/dynasty_genius/sources/pff_intake.py`
is exactly this shape: a human puts a file somewhere, a sidecar *declares* its provenance, and the
intake hashes and versions it. Provenance is **declared, never inferred from a filename** — which
matters doubly here, because `dynasty_trade_values (1).csv` carries no source, no date and no
version, and in six months nobody will be able to say what it was.

**Evidence the pilot must produce, or it has not run:**

1. The exact retrieval provenance **declared by David** (bundle version `2026i`, the changelog's
   own `Updated:` date, when he downloaded it) — never guessed from mtime.
2. Raw bytes retained with SHA-256, byte count, and the file's schema hash, before parsing.
3. Row/column census, and **identity resolution measured**: how many of the ~1,546 PFR ids resolve
   to our canonical `player_id`, and the unresolved list — not a percentage without a denominator.
4. A `blocked_for_use` or `substrate_only` disposition recorded at landing, with the reason.
5. **Redundancy measured against the overlays we already hold** (KTC, `dynastyprocess_ecr_2qb`):
   rank correlation and top-24 overlap on the Superflex slice. If it is a fourth copy of the same
   consensus, that is a finding worth having *before* anyone builds on it — which is precisely what
   the `ff_rankings` framing found when Spearman came back at .99.
6. A second bundle, later, to confirm the changelog's weekly cadence against observation.

**Explicitly out of scope for the pilot:** any model input, any David-facing surface, any scheduler,
any automated fetch, and the `comments.csv` / projections files.

## 7. Where AI actually helps here — and where it is the wrong lever

- **Wrong lever:** agentic browsing to acquire Footballguys data. Prohibited by §13, and it risks the
  account.
- **Right lever, and undervalued:** `comments.csv` is 442 KB of attributed, timestamped analyst prose.
  Turning that into structured, cited qualitative context — per player, with the analyst named and
  the date attached — is a genuine language-model job that no scraper would improve. It stays
  documentary under our rulings, but "what did a named analyst say about this player, and when" is
  real 35%-lane material.
- **Right lever:** normalizing and reconciling already-licensed local files, and identity resolution.
- **For other sources:** the deciding question is never "can an agent read the page" — it is "does
  this provider's ToS permit automated access, and is there a first-party export or API". Sources
  answering yes get a documented adapter under `01` §Source Adapter Rules. Sources answering no are
  manual-intake or nothing.

## 8. Two operational cautions

1. **`MI2026a_Setup.exe` is a Windows binary and cannot run on this Mac.** The macOS path is the
   `.app` in the zip. Nothing was executed to determine this — `file` reports the header.
2. **Do not open `2026app_I1.xls` expecting a data source.** It is a macro-era Excel application; the
   same underlying numbers are already available as plain CSV inside the app bundle, without opening
   a workbook that may carry VBA.
3. **Redistribution is barred by §1.** Anything ingested stays private to this repo's gitignored
   stores — which also means, if it is ever landed, it belongs in the backup manifest as
   irreplaceable-by-licence, and must never reach a public surface.

## 9. What I did not do

No web scraping or download. No account, site or provider interaction. No execution of any downloaded
app, installer, or macro. No repository edit. Only text files were extracted from the archive, to a
scratch directory, for inspection.

## Sources

- [Footballguys Terms of Service](https://www.footballguys.com/terms)
- [Footballguys Fantasy Football Tools](https://www.footballguys.com/article/fantasy-football-tools)
- [Footballguys Plans](https://www.footballguys.com/plans)
- Local, measured: `DraftDominator_v2026i.zip` (`Contents/Resources/`), `ReadMe.txt` changelog.
