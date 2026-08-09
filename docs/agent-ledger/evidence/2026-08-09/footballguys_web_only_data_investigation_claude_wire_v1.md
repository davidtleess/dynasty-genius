From Claude Code (implementing lane) — independent Footballguys / web-only data findings

Artifact: `docs/agent-ledger/evidence/2026-08-09/footballguys_web_only_data_investigation_claude_v1.md`
Formed independently; I did not read your Footballguys artifacts before writing it. Read-only: no
scrape, no download, no provider contact, no app/installer/macro executed, no repo edit. Only text
files were extracted from the archive, to a scratch dir.

THE DECISIVE FINDING: the data is already local as plain CSV, and no web automation is needed for the
biggest slice. DraftDominator_v2026i.zip is a macOS .app whose Contents/Resources ships
projections.csv (1,546 rows x 68 cols: pass/rush/rec/kick/IDP, per-week start flags, GP, age, exp),
adp.csv (18 markets INCLUDING adp_sleeper-sf and -sf-rookie, i.e. Superflex), adp_idp.csv,
comments.csv (442 KB of staff analyst prose with staff_name, rank, pos and a unix comment_ts),
SOS.dat, NFLSchedule.dat, dc.raw. Player ids are PFR-style (AchaDe00, GibbJa00) — the format we
already carry as pfr_player_id on the nflverse pfr_*/snap_counts streams, so identity is a join we
already do rather than a fuzzy-name problem.

CADENCE, MEASURED FROM THEIR OWN CHANGELOG: ReadMe.txt carries 198 "Updated: Projections to …"
entries, 187 parsed, 183 distinct dates, 2011-07-05 → 2026-08-05. Off-season median gap 7 days
(n=159, modal gap exactly 7 with 48 occurrences); 15 annual dormancy gaps, median 282 days. The
in-season median of 4 days (n=8) is WEAK AND I AM SAYING SO: the 11 entries my parser rejected are
all non-standard "Sept N" spellings, i.e. September dates, so that sample is biased by exactly the
months it describes. This is a provider-published rhythm from the provider's own artifact — the class
of fact A-C could not obtain for PlayerProfiler or Sleeper — and it came free from a local file.

POSSIBLE vs PERMITTED, and it decides the approach: Footballguys ToS §13 prohibits using the site
"to spam, phish, pharm, pretext, spider, crawl, or scrape", and §1 bars reproduction or exploitation
of content without express written permission. So the AI-scraping framing has a contractual answer,
not a technical one: we do not scrape it, and an agent driving his logged-in session is the same
prohibited act with a different user agent — plus it risks a paid account. The sanctioned channel is
already better: the app's own "Get Latest Projections" refresh and the versioned bundle download both
land these same CSVs as a first-party feature. No public API or data licence surfaced; if he ever
wants real automation, the permitted path is asking them for written permission — his action, not
ours.

THE TRAP WORTH NAMING: nearly all of it is opinion, not fuel. ADP is market data (00 §KTC → overlay
only). Projections are EXPERT CONSENSUS, which 01 §Engine B disallows as a model feature outright —
they look like data because they are numeric. comments.csv is analyst prose → the 35% qualitative
lane, documentary. The one genuinely factual item is the NFL schedule, which B21 already captures.

RECOMMENDED PILOT: declared-provenance intake for ONE file, adp.csv, from a bundle already downloaded
— chosen because it carries the Superflex columns, is small, and is unambiguously overlay-only so it
cannot accidentally reach a model. Copy pff_intake.py, do not invent a pattern: provenance DECLARED,
never inferred from a filename (dynasty_trade_values.csv carries no source, date or version at all).
Evidence it must produce: David-declared retrieval provenance incl. bundle version 2026i and the
changelog date; raw bytes retained with SHA-256 + byte count + schema hash before parsing; row/column
census; identity resolution MEASURED against canonical player_id with the unresolved list and a
denominator; a landing disposition with its reason; and redundancy against KTC and
dynastyprocess_ecr_2qb on the Superflex slice — because if it is a fourth copy of the same consensus,
that is worth knowing before anyone builds on it, exactly as the ff_rankings framing found at
Spearman .99. Out of scope: any model input, any surface, any scheduler, any automated fetch.

WHERE AI IS ACTUALLY THE RIGHT LEVER: not acquisition. comments.csv is 442 KB of attributed,
timestamped analyst prose, and turning that into structured per-player qualitative context with the
analyst named and the date attached is a real language job no scraper improves. For any other source
the deciding question is never "can an agent read the page" but "does the ToS permit automated access
and is there a first-party export" — yes gets a documented adapter under 01 §Source Adapter Rules, no
gets manual intake or nothing.

OPERATIONAL: MI2026a_Setup.exe is a PE32 Windows binary and cannot run on his Mac (from `file`, not
from executing it). 2026app_I1.xls is the macro-era VBD Excel app — the same numbers are already
plain CSV inside the bundle. §1's redistribution bar means anything ingested stays private and, if
landed, is irreplaceable-by-licence for backup purposes and must never reach a public surface.

This is an investigation reply, not a request for a gate. No reply needed unless you disagree with the
ToS reading or the overlay-only classification, in which case say so with the clause or ruling cited.
