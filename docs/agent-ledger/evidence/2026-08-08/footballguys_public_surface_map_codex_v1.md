# Footballguys source-discovery map — Codex v1

Date: 2026-08-08
Layer: Layer 1 ingestion
Status: **PUBLIC-SURFACE MAP ONLY — AUTHENTICATED INVENTORY BLOCKED, NO EXPORT RETAINED**

## Answer first

Footballguys is a real omitted paid-source family, but this pass does **not** close its source ticket.
The current runtime exposes no callable Chrome-extension browser control, so David's authenticated
account surfaces could not be inspected without substituting an unsanctioned browser/session hack.
Public official pages are used only to bound the later authenticated inventory. No login, download,
provider contact, form submission, or subscriber-data access occurred.

The strongest first-export candidate, **conditional on authenticated confirmation**, is the native
**Download Projections** control on the current projections page. It is source-authentic, current,
structured by expert and stat family, and explicitly downloadable. The format, URL, auth behavior,
bytes, headers, row count, schema, timestamp and licence/retention behavior remain unmeasured and
must not be inferred from the public label.

## Official public surface map

| Report family | Publicly observable variants / fields | Export signal | Authenticated pass must verify |
| :-- | :-- | :-- | :-- |
| Preseason player projections | multiple named experts; offense, IDP, kickers, team defense; season passing/rushing/receiving/fantasy columns | explicit `Download Projections` control | exact file format/content-disposition; selected experts/positions encoded in export; league scoring effect; retrieval timestamp; whether one download contains one expert or a combined view |
| Draft rankings | overall and position filters; multiple experts/FBG consensus; league settings; ADP and rank-vs-ADP | print/custom-cheatsheet controls visible; no public native download established | whether authenticated page exposes CSV/XLSX/print-only export; exact expert/consensus identity; scoring and league-setting provenance |
| Dynasty rankings | overall and position filters; experts/consensus; age/experience; upside/downside context | custom/print surface; no public native download established | whether a structured download exists; Superflex/league-setting controls; update timestamp per expert; raw label/value schema |
| Rookie rankings | named as its own ranking family in official tools/plans | not established publicly | exact report route, Superflex/1QB split, expert identity, timestamps and export capability |
| Salary-cap and best-ball rankings | named as separate ranking families | not established publicly | separate routes/files vs views over one ranking dataset; export capability and clocks |
| IDP rankings and projections | separate offensive/defensive expert families and position filters | projections page exposes download control; scope unknown | whether IDP is one export family or shares the offensive transport; schema and expert identity |
| ADP / Top 300 / Footballguys Draft List | official tools page names Average Draft Position, Top 300 and Draft List separately | no public native download established | provider inputs, scoring variants, timestamp, structured export and whether Draft List is derived rather than an independent source family |
| Data Dominator | player/team custom statistics since 2002 | interactive tool | whether any native CSV/XLSX export exists; query dimensions; source timestamp; report-vs-query family boundary |
| Historical Data Dominator | season-long statistics back to 1960 | interactive tool | same; do not classify query results as a standing feed without a native export contract |
| Game Log Dominator | game logs for the last 15 years | interactive tool | native export, exact retained columns, query parameters and change clock |
| IDP Matchup Analyzer | IDP game-log analysis since 2003 | interactive tool | native export and source/report boundary |
| Classic drafting/projection apps | Draft Dominator, Projections Dominator, VBD spreadsheet; “Get Latest Projections” transport described | downloadable software/workbook, not yet a report export | **do not install or execute as acquisition discovery**; first inspect whether the web-native projections download already provides the underlying source bytes |
| Rookie Guide | downloadable editorial PDF with historical stats/scouting | document download | article/guide, not first structured ingestion; register separately only if David later wants document evidence, never as a substitute for a data report |

Articles, trade-value prose, podcasts and strategy pages are **not ingestion report families**.

## Authenticated inventory procedure

When Chrome control is available, read only and record for every account-visible report family:

1. exact visible report name, page URL and account tier/access state;
2. native export/download control and exact user-selected parameters;
3. file extension and browser-provided filename **before** opening the payload;
4. report/expert identity, scoring/league settings, position/scope and visible updated-at value;
5. whether the export is raw provider output or a customized/derived view;
6. whether repeated export of the identical view is byte-stable, content-stable but metadata-variant,
   or changed;
7. observed family-specific clock evidence—never one blanket Footballguys cadence;
8. any terms/retention notice shown on the authenticated surface.

Do not click executable-app installers. Do not contact Footballguys. Do not submit league credentials,
messages or forms. A normal inbound report download is the only contemplated state change.

## Conditional first-export specification

If the authenticated pass confirms the native projections download, retain **one current named
expert projection export exactly as delivered**, without selecting an expert for predicted model
value. Selection rule: first report family with a native structured download whose provider/report
identity and visible update time can be recorded; if several qualify simultaneously, use the first
expert already selected by the site default and record that fact rather than choosing analytically.

Required sidecar before intake:

- provider: `footballguys`
- report family and visible report title
- exact page URL and download URL/redirect chain if observable without exposing credentials
- authenticated access tier, recorded as a non-secret label only
- expert/consensus identity
- scoring, league, position and other selected parameters
- provider-visible updated-at, if present
- retrieval time in UTC and local timezone
- original filename, MIME/content-disposition, byte count and SHA-256
- declared handling: `raw_only`, no model/consumer use

First ticket acceptance then requires: content-addressed raw path, metadata ledger, measured rows or
objects, exact schema and schema hash, success/last-good marker, failed-attempt behavior, replay with
no duplicate vintage, backup-manifest coverage, focused/clean-tree/full gates and catalog update from
the retained evidence.

## Sources

- Current projections page, including named expert families and `Download Projections`:
  <https://www.footballguys.com/projections>
- Current rankings surface and its separate ranking families:
  <https://www.footballguys.com/rankings>
- Official tool inventory, including ADP, Top 300, Draft List and four statistics tools:
  <https://www.footballguys.com/article/fantasy-football-tools>
- Current plan matrix naming projection/ranking report families:
  <https://www.footballguys.com/plans>
- Current classic-app page, used only to bound—not authorize—its projection transport:
  <https://www.footballguys.com/article/footballguys-classic-drafting-apps>
