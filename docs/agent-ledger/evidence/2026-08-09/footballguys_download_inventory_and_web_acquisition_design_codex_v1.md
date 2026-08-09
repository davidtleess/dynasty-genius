# Footballguys downloaded-artifact inventory and web-acquisition design — Codex v1

Date: 2026-08-09
Layer: Layer 1 source acquisition
Status: **DISCOVERY COMPLETE FOR LOCAL FILES; WEB-ONLY BULK ACQUISITION NOT CLEAR**

## Answer first

David's downloaded files provide several real Footballguys source candidates now, without any need
to automate the authenticated site. The safest first implementation ticket is a retained, raw-only
import from a provider-created structured download after the exact report/page identity is recorded.
No downloaded executable, application bundle, workbook macro, or installer needs to be run.

The web-only database is technically reachable through authenticated browser agents, but that does
not make bulk capture permissible. Footballguys' current Terms restrict copying/reproduction and
expressly list spidering, crawling, and scraping as prohibited uses. Until Footballguys supplies a
native export/API intended for the use or written permission covering automation, cadence, and
retention, AI may inventory visible report families and operate provider-offered export controls; it
must not harvest the database through DOM traversal, hidden endpoints, network-response replay, or
pagination fan-out.

Terms basis observed 2026-08-09: <https://www.footballguys.com/terms>.

## Local artifact inventory

The files remain in `~/Downloads`. Nothing was executed, moved, copied into the repository, or
published. Filesystem modification time is a local clue, not an HTTP retrieval timestamp.

| Local artifact | Bytes | SHA-256 | Measured disposition |
| :-- | --: | :-- | :-- |
| `DraftDominator_v2026i.zip` | 8,540,590 | `d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c` | Valid 259-entry ZIP containing a macOS application bundle and bundled data; do not execute |
| `2026app_I1.xls` | 3,586,048 | `09ab019ebf38cb8f9995f4e9b81491e629fa73682b0ec3757bc180b4d5b6ab05` | BIFF8/OLE Footballguys Classic VBD Excel App with VBA; parse as data only, never run macros |
| `Printable NFL Schedule Grid 2026 - Footballguys.pdf` | 680,396 | `afe76d8a92957efdb46dfca9956d8042a9f58d5d8b8be02f3912473f44cb8722` | Two-page presentation artifact; not a substitute for the structured B21 schedule source |
| `Cheatsheet for Redzone Champions League.pdf` | 1,144,816 | `9461b9cf74be44fae0a0fcc211968207513ba3987cb3e4a8b20f2e8c2b15d45e` | Three-page league-scoped report, generated 2026-08-08 23:55:14 local |
| `Cheatsheet for Redzone Champions League - rookies.pdf` | 774,206 | `0e6137dda815621f6528bf006f8487a5b397873a0d1dabcf42707e72f4bf0d50` | Three-page rookie report, generated 2026-08-08 23:56:09 local |
| `dynasty_trade_values (1).xlsx` | 106,718 | `f0cc16cb87090a22922ae90bc20051713e4f5c06e237370f01c329c29c9c9dd4` | One `Data` sheet; report/provider identity is not embedded strongly enough to infer from filename alone |
| `dynasty_trade_values (1).csv` | 14,075 | `29ded72e3d81e7fb32c5bef776292ab8519b891694fcb08f53019df19fd706a8` | 480 data records; columns `Player, Team, Age, Position, Value`; exact page/report identity still required |

The unproven generic `dynasty_trade_values` pair is included because it arrived with David's stated
Footballguys download set. It is not yet registered as Footballguys evidence. A provider/report
claim requires the originating page or visible export label, not temporal proximity or filename.

### Draft Dominator embedded candidates

| Resource | Bytes | SHA-256 | Measured contents |
| :-- | --: | :-- | :-- |
| `projections.csv` | 260,688 | `25be2d5a10f92b9787009edbb6144f516f53e4421afe5f39549b6eb6ca019c3f` | 1,546 data records; header/data width defect described below |
| `adp.csv` | 30,388 | `1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9` | 608 player records and 18 named ADP channels |
| `comments.csv` | 442,476 | `8727b83578071ff21345b785ebb4ff6440ebbde0781b2034a7b09851593e3fbd` | 1,193 comments, 648 players, 11 staff; copyrighted analyst prose, raw-only |
| `adp_idp.csv` | 91,474 | `627183a73107f23dcd8e5249bdbc0cf84bc07690eda9de15894a658364b1229e` | **Invalid:** HTML `File not found` response masquerading as CSV; quarantine/failure evidence only |
| `NFLSchedule.dat` | 5,880 | `96c2bf76df182e2362b648592eb4c82d09cff9965b065f4ec3a1ad27a4f3059d` | Opaque fixed/binary schedule data |
| `SOS.dat` | 43,050 | `a2adc5bd9f91069c32695052d6f606ba5ff27c5e9439079621c7ac3b109e5114` | Opaque binary strength-of-schedule data |

The bundled `projections.csv` has a source schema defect: its 65-column header omits the week-18
label while each data row contains 66 substantive values plus a terminal empty field. The VBD
workbook's corresponding header includes week 18. An importer must preserve the original bytes,
fail or repair through an explicit versioned rule, and record both the raw and interpreted schemas.

The ZIP readme exposes a roughly weekly 2026 update series (June 10, 17, 24; July 1, 8, 15, 22, 30;
August 5), but that is evidence only for this application package's publication history. It is not a
blanket cadence for every Footballguys report family.

## First source ticket selection

Selection must follow source-authentic availability, not estimated model value.

1. First choice: a provider-native current projections CSV/XLSX export whose visible report title,
   expert/consensus identity, filters, scoring scope, update label, and download control can be
   recorded. A public `Download Projections` control exists; its authenticated bytes and exact
   semantics remain unmeasured.
2. If no such export is available, the already downloaded Classic VBD workbook is the strongest
   attributable structured family. Parse it without running VBA and register the VBD workbook as its
   own report family/vintage.
3. Do not start with staff comments, binary schedule/SOS files, or the Draft Dominator application.
   Those raise copyright, opaque-format, or executable-surface complexity before the basic retained
   export path is proven.
4. Do not call the generic dynasty-trade-value pair a Footballguys capture until its origin is
   positively identified.

The first landed family remains `raw_only` / `substrate_only`. Identity joining, feature design,
model use, product use, and redistribution are separate decisions.

## AI operating model

Only one browser agent should touch the subscriber site during a run. The others review sanitized
metadata and retained files offline. This avoids tripling account traffic and exposing paid content
to three vendors by default.

| System | Best role | Required boundary |
| :-- | :-- | :-- |
| Claude Cowork + Claude in Chrome | Primary supervised operator for a permitted, visible, repeatable native-export workflow; record the UI workflow only after the first manual run succeeds | Dedicated Footballguys-only browser profile; David controls login/MFA/CAPTCHA; no bulk DOM or hidden-endpoint extraction |
| Codex + Chrome / repository | Define the capture contract; hash, measure, land, replay, test, and independently verify the provider-created export | Browser history is not provenance; never retain cookies, authorization headers, signed URLs, password material, or raw HAR files |
| Gemini in Chrome | Read-only operational observer: report-family labels, visible update clocks, duration, human takeovers, UI drift, export presence, and request count | Advisory only; no repository writes, clearance, duplicate harvesting, or authorization inference |

Official capability references:

- Claude in Chrome: <https://support.claude.com/en/articles/12012173-get-started-with-claude-in-chrome>
- OpenAI built-in browser / Codex Chrome extension: <https://help.openai.com/en/articles/20001277-using-the-built-in-browser-in-the-chatgpt-desktop-app>
- Gemini in Chrome auto browse: <https://support.google.com/gemini/answer/16821166?hl=en>

## Permitted first pilot

1. David logs in personally using a dedicated browser profile with a Footballguys-only site
   allowlist. No unrelated authenticated tabs are open.
2. Inventory only visible report names, page URLs, update labels, filters/scoring settings, and native
   CSV/XLSX/PDF download controls. Do not enumerate data rows.
3. Choose one current structured provider export by the selection rule above. If the existing licence
   does not clearly allow retained private analysis, stop and ask Footballguys for written permission.
4. Claude Cowork may perform the same visible clicks David demonstrated, with manual approvals and a
   maximum of one export. Stop on CAPTCHA, 401/403/429, account warning, unexpected host, changed
   terms, or missing export.
5. Codex retains the original file privately and records the acceptance envelope below. Gemini
   measures run telemetry from sanitized evidence; it does not access the payload by default.
6. Replay the retained bytes locally. Repeat the supervised export manually across three observations
   before considering a scheduler. Scheduler installation remains a separate decision.

If Footballguys has no native export for the web-only database, the pilot ends after inventory. The
next step is a provider request for an API/bulk export or express permission for bounded automated
private capture. No browser agent should discover or replay private APIs to work around that answer.

## Acceptance envelope

- exact provider and separately registered report family;
- account tier as a non-secret label;
- visible report title, page URL, expert/consensus, filters, scoring/league scope, and update label;
- local observation time, retrieval time supplied by the response when available, and original
  filename/content type/content-disposition;
- requested/final hosts and redirect class, with signed query values removed;
- raw byte count and SHA-256;
- raw and canonical paths, content-addressed vintage ID, rows/objects, ordered columns/dtypes, schema
  hash, duplicate-key census, and null census;
- current Terms URL and the explicit licence/permission basis;
- last-checked, last-changed, last-good, and failed-attempt behavior;
- replay proving identical content does not mint a duplicate vintage;
- consumer disposition `raw_only` and explicit no-redistribution/no-model-use state;
- focused tests, clean-tree tests, lint, full suite, committed blob pins, pushed SHA, and terminal CI.

## Acquisition hierarchy for other web-only providers

`official API/export -> connector -> permitted native browser export -> written automation permission -> no acquisition`

When permission expressly allows deeper browser capture, truthfulness descends in this order:

1. native downloaded bytes;
2. documented API response;
3. browser-decoded approved response body;
4. bounded DOM table snapshot;
5. screenshot/OCR as audit evidence only, never the primary structured dataset.

Every provider is assessed separately. Technical capability, `robots.txt`, and an authenticated
subscription are not substitutes for the provider's terms or permission.

## Independent-team input status

- Gemini returned a read-only advisory recommending native downloads, a private inbox, content
  addressing, and marker telemetry. Its example row counts, identity counts, freshness label, and
  empty-file SHA were illustrative placeholders, not measurements; they are expressly rejected as
  evidence.
- Claude independently found the same Terms barrier and the same broad local-data route. It proposed
  `adp.csv` as the first pilot because its Superflex columns appear useful and overlay-only. That
  value-based selection rationale is **not adopted**: David's source rule selects the first actual
  family by source-authentic availability, not predicted model value. Claude's useful measured
  cadence result is accepted for the Draft Dominator package only: 183 distinct projection-update
  dates from 2011-07-05 through 2026-08-05, with an off-season median gap of seven days; its
  in-season four-day figure is weak and biased by unparsed September spellings.
- Claude's local schema claims required two corrections. Independent standard-library CSV parsing
  found `projections.csv` has 65 header fields and 67 fields on every one of 1,546 data rows, not a
  clean 68-column table. Its `adp_idp.csv` is HTML beginning with `<!DOCTYPE html>`, not an IDP data
  table. These are exactly why raw hashing, MIME checks, ordered schema measurement, and fail-closed
  intake precede interpretation.

## Consolidated team recommendation

The consensus is binding only after the source-integrity corrections above:

1. Do not use Claude Cowork, Codex, or Gemini to scrape Footballguys. Current Terms make the
   acquisition boundary contractual, not technical.
2. Preserve and intake provider-created downloads through a private, content-addressed,
   declared-provenance route. Do not run the apps, macros, or installers.
3. First perform the authenticated **inventory-only** pass and select the first native structured
   export by availability/default UI order. Do not select ADP merely because it looks useful.
4. If no native structured export is present, treat the versioned Draft Dominator package as the
   transport envelope and seek licence clarity before extracting/retaining its embedded report
   members as separate families. `projections`, `adp`, and staff comments remain separate report
   families with separate disposition and clocks.
5. Claude Cowork is the best supervised operator for a permitted native-export workflow; Codex owns
   capture contracts, hashing, schema/row measurement, replay, and independent verification; Gemini
   owns sanitized run telemetry and UI-drift observation. Only one agent accesses the subscriber
   site in a run.

## Still unavailable or unverified

- Authenticated report-family inventory and actual native-export formats/bytes.
- Exact origin of the generic dynasty-trade-value CSV/XLSX pair.
- Licence scope for private retained copies, automation, cadence, and historical retention.
- Whether Footballguys will provide API, bulk export, or written permission for its web-only
  database.
- Any first retained repository vintage, marker, replay, importer, committed blob, pushed SHA, or CI.

Accordingly, this discovery ticket has real measured local evidence but does **not** close a source
capture ticket and does not authorize web scraping.
