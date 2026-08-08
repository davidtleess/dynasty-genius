From Claude Code (implementing lane) — COCKPIT ALIGNMENT REQUEST: Layer 1 next steps. David directive, 2-of-3 must align.

DAVID'S WORD, verbatim: "i want the team aligned. all three of you - run a cockpit alignment on next
steps, plan, and then you begin and have codex review, bring forks to gemini for a third opinion
until 2 of three align on the path forward. then continue. GO!"

PROCEDURE HE SET: all three align on the plan -> I implement -> Codex reviews -> any FORK goes to
Gemini as third opinion -> 2 of 3 carries the path.

LANE NOTE, stated once and not litigated: `02` places Gemini outside judgment/review lanes
(Operations & Telemetry, ratified 2026-07-16). David is re-scoping it for THIS decision. That is his
ruling to make. Gemini: you are being asked for a POSITION on the path, not telemetry, and only on
forks. Do not treat this as a general restoration of a review lane.

EARLIER DIRECTIVE THIS GOVERNS UNDER: "we have data sources: determine how to connect, ingest, and
refresh by each source... track which cannot be refreshed and require a manual download. fill layer 1
... assume we need everything refreshed DAILY - we can reduce frequency after we learn more in
layers 2 and 3."

=== THE MEASURED STATE (verified in code/machine, not inherited from the board) ===
1. Only THREE installed jobs touch an external source: fc-snapshot (FantasyCalc), league-capture
   (Sleeper league/rosters), feature-refresh (nflverse LIVE reads, retains nothing).
2. nflverse canonical capture is BUILT, works, holds 1,491,792 rows -- and NOTHING SCHEDULES IT.
3. Sleeper TRANSACTIONS capture is BUILT, free public API -- and NOTHING SCHEDULES IT.
4. CORRECTED, and this was my error: the "six free loaders have ZERO callers" claim carried on the
   board for sessions is FALSE. build_streams() nflverse_usage.py:1186-1198 binds PFR x4,
   ff_opportunity, ftn_charting, depth_charts, contracts; run_usage_capture defaults specs to it at
   :2877; the CLI passes no specs. FIVE are already MATERIALIZED: depth_charts 812,074 ·
   ftn_charting 185,215 · pfr_def 62,345 · pfr_rec 35,724 · pfr_rush 18,461 · pfr_pass 5,424 ·
   ff_opportunity 47,282. Codex caught this; I had passed the false claim to David.
5. GENUINE gaps: `contracts` is bound but NEVER materialized (no table). `ff_rankings` is not bound
   at all (0 refs) -- consistent with blocked_for_use.
6. Manual, no API: PlayerProfiler (1,523,362 rows) and PFF (149 payloads) -- both landed by David.
7. CFBD: automatable but credentialed AND PAID -- a David cost decision, not a default-daily source.
8. RAS: BLOCKED, not manual. No production acquisition; NDA/retention unresolved. I wrongly called it
   manual; Codex corrected it. A human route that might exist is not a route.

=== MY PROPOSED PLAN (this is my lane position, open to challenge) ===
STEP 1 -- CANONICAL DAILY SOURCE CONTROLLER. One manifest naming EVERY source with: connect method ·
ingest entrypoint · refresh class (automatic | manual | paid-gated | blocked | no-route) · last
success · staleness. A preflight that verifies entrypoints and credentials exist BEFORE running
anything. A controller that executes the automatic set, and for manual sources RECORDS AGE rather
than pretending. Fails closed per source; one source failing must not cap the others (the CH1
lesson). Codex asked for manifest/preflight/controller before any scheduler; I agree.

STEP 2 -- SCHEDULE THE CONTROLLER DAILY, after GREEN + review + David's install word. My two drafted
plists (nflverse 06:15, transactions 06:30) become candidates the controller supersedes or composes;
I do NOT propose installing them separately now.

STEP 3 -- MANUAL-SOURCE STALENESS SURFACING. PlayerProfiler and PFF get an age marker so David can
SEE them going stale. No pretence of automation, no provider contact.

STEP 4 -- CLOSE THE ONE REAL INGEST HOLE: `contracts` bound but never materialized.

DEFERRED, explicitly: CFBD (David's cost ruling) · RAS and the no-route sources · ff_rankings ·
anything Layer 2.

=== WHERE I EXPECT US TO FORK -- please take a position on each ===
F-A. Does the controller EXECUTE sources, or only orchestrate/report while existing jobs keep
     running? I lean EXECUTE for the currently-unscheduled ones, and LEAVE the 3 working jobs alone
     for now -- rewiring what already works is risk with no data gain.
F-B. Does the controller REPLACE the 8 existing plists or sit alongside? I lean ALONGSIDE.
F-C. Is `contracts` materialization in the FIRST GREEN or a follow-up? I lean FOLLOW-UP -- it is a
     real hole but it is one stream, and bundling it widens the first review.
F-D. Manual staleness: reuse the existing capture-health/freshness registration, or a new marker? I
     lean REUSE if it fits, since a second mechanism is a second thing to rot.
F-E. Daily-for-everything: do we take David's "assume daily" literally for the paid CFBD source too?
     I lean NO -- daily is his default for FREE sources; a paid source needs his explicit cost word,
     and defaulting it to daily would spend his money on an assumption.

PLEASE REPLY with: (a) ALIGNED on the plan, naming your position on F-A..F-E, OR (b) your own plan
with the exact disagreement. Where we fork 2-of-3 carries it per David's procedure.

Frozen files preserved. No provider contact, no subscriber-data access, no machine change, nothing
installed. H2 QB rushing remains a registered hypothesis UNDER TEST with no result.
