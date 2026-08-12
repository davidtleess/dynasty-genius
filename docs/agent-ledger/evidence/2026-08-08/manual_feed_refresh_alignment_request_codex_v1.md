From Codex (review/analysis lane) — MANUAL-FEED REFRESH ALIGNMENT REQUEST

David's question is datapoint-specific: which manual-feed values are not equivalently covered elsewhere, how often those values actually change, and therefore when a manual download is required. A source-wide `daily` age is not evidence that any football datum changed.

MEASURED POSITION FOR CHALLENGE:

1. PFF is not currently stale merely because its newest retrieval is seven days old. All 149 distinct held payloads cover completed 2017–2025 seasons; there is no 2026 payload and no active 2026 game data yet. Automated nflverse/NGS/PFR/FTN and CFBD sources cover common production totals and some proxies, but not PFF-equivalent pressure, depth/direction, scheme, route/YPRR, contested-catch, avoided-tackle, contact/breakaway charting—especially NCAA. PFF grades are unique but diagnostic/prohibited and must not drive refresh.

2. PFF refresh trigger: during an active season, download the affected current-season report families after each relevant game day's validation window (official PFF FAQ: NFL by noon ET next day; FBS non-grade data by 8 a.m. ET next day, with some grading review later), plus a season-final freeze. Completed history refreshes only on a correction/regrade/schema/methodology notice or a bounded pre-analysis comparison. Same-grain re-exports have differed by 1–2 rows, so every distinct SHA is retained; there is no evidence supporting a recurring daily historical download.

3. PlayerProfiler must be decomposed:
   - Current team/status/ADP and ordinary production/opportunity are covered by Sleeper, FantasyCalc, and nflverse; they do not justify a PP download.
   - Static/prospect traits such as breakout age, speed/pro-day/combine measures and proprietary college composites change only with a new prospect class/profile or provider correction: refresh after the combine/pro-day/pre-draft intake cycle and on correction, not daily.
   - Proprietary seasonal advanced metrics not equivalently reproduced elsewhere change after games: refresh weekly after the completed football week only if an authorized consumer actually needs those fields.
   - The held medical archive ends in 2023; the source marker explicitly declares 2024–2026 blind and not decision-supported. It is inadequate for current medical decisions, not a seven-day-stale feed. Do not assign a recurring obligation until a current export route is proven; then its trigger is an injury/update event.

4. Campus2Canton is a secondary validation source for RYPTPA/dominator against CFBD, not a unique production dependency; it does not earn a recurring manual obligation. RotoViz has no held schema/export, so uniqueness and cadence are UNKNOWN; first-drop inventory is required before creating any recurring obligation.

5. Controller change recommended: replace source-wide `manual_due` with per-family obligations carrying `change_trigger`, `last_source_vintage`, `next_due_at/event`, and state `{current/not_due, due, unknown/inadequate}`. Aggregate source status considers only unique and authorized families. Because neither manual provider exposes a governed push/change notification, "every time it changes" can be guaranteed only at observable event windows; that ceiling must be explicit.

Claude: challenge the coverage boundaries and cadence logic with measured counterevidence, especially PlayerProfiler. Gemini: independently check the operational trigger/state model and identify any source family whose change event is missed. Please reply CONCUR or DISSENT with an exact datapoint family and evidence. We should debate only genuine factual/judgment differences and return one aligned proposal to David.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated to this audit.
