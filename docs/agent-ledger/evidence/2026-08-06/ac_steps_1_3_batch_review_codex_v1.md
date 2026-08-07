# A-C steps 1-3 batch review — Codex v1

**Artifact reviewed:** `docs/layer-1-data-inventory-catalog.md`  
**Pinned SHA-256:** `363c2609a9e7561416cd20e48bec2105c10b569d343a8e55bca5a387484a8b45`  
**Verdict:** **NOT CLEAR**  
**Layer:** Layer 1 inventory. No build, scheduler, capture, consumer migration, checkbox move, or Layer 2 authority is implied.

## Checks run

- Recomputed the catalog SHA-256: matched the routed pin.
- Compared `4bee0be..3019d44`: catalog change is 225 insertions / 0 deletions; `git diff --check` clean.
- Opened `app/data/fc_forward_capture.db`: `fc_forward_capture_raw` has 20,518 rows, 44 snapshot dates, 2026-06-24 through 2026-08-06; the row carries the claimed provenance columns.
- Read `fantasycalc_adapter.fetch_with_cache`, `market_overlay_service.enrich_pvo_list_with_market_overlay`, `roster_auditor.py`, and `app.data.sleeper` directly.
- Read the seven-class definitions and provisional classifications in the refresh plan and compared them with canonical catalog §4.4 and new §§6C/6E.
- Read `app/config/report_freshness.json`, enumerated `ops/launchd`, and inspected live `launchctl list`.
- Opened N18 status/ready markers and logs: current run `league-20260806T132000Z`, status `ok`; 22 successful output-log rows/runs; empty error log; six ready artifacts.
- Compared the exact §4.4 member set with §§6D/6E.

## Findings

### F1 — HIGH: the automation classifications contradict the governing plan and canonical §4.4

The new sections do not reconcile the existing canonical classification table; they create a second, conflicting answer.

- N18 is `automatic_active_verified` in the refresh plan and §4.4. The new §§6C/6E downgrade it to `automatic_active_health_unverified` because exact raw replay is absent. That is a capture-quality/provenance defect, not an operational-health defect. Operational health is independently evidenced by registered freshness, a current `ok` marker, a current ready pointer, 22 successful runs, an empty error log, and loaded-job exit 0.
- B15-B19 are already-running direct-read routes. The plan and §4.4 classify the current routes as `automatic_active_health_unverified`, with their desired canonical-capture routes separately `automatic_candidate`. §6E calls the running routes `blocked`, conflating current state with target state.
- Additional unresolved contradictions include B5 (`automatic_candidate` vs `blocked`), B12 (`blocked` vs `automatic_candidate`), B13 (`blocked` vs landing-gated `automatic_candidate`), and N1-N8 (`blocked` vs `manual_only`).

One canonical classification must survive. Quality/remediation gates belong in their own columns; they must not rewrite operational state.

### F2 — HIGH: the Roster Auditor route is an acquisition defect, not merely a consumer edge

`roster_auditor.py` calls `get_user`, `get_leagues`, `get_rosters`, and `get_all_players`; `app.data.sleeper._get` performs live `httpx.AsyncClient.get` calls to Sleeper. The request-time route therefore acquires external data outside the canonical captures and preserves no exact bytes.

`consumer edge` accurately describes topology but omits the load-bearing governance defect. Record it as **consumer edge + acquisition defect**, or make `acquisition defect` the disposition and retain consumer-edge wording as relationship metadata. The FantasyCalc route is correctly classified as an acquisition defect for the same reason.

### F3 — MEDIUM: N19's uniqueness claim overstates the measured relationship

§6B says N19's non-transaction endpoint families are a separate corpus “not held anywhere else.” They are not held elsewhere as exact endpoint history, but several datasets overlap N18's normalized league/users/rosters/draft bundle. The proven statement is narrower: N19 is the only exact historical endpoint representation of those families; it is not the only place their information appears.

### F4 — HIGH: §6D is not complete, and one asserted consumer state contradicts the canonical record

- N14 `league_season_capture` is in the enumerated R7 set but omitted from §6D's non-nflverse states.
- B20-B24 should remain open rather than be inferred, but “all five R7 states UNVERIFIED” is too broad: `decision_supported = false` is already declared as a global invariant, and the canonical B20-B24 rows already carry measured candidate states. Re-probe each cell and preserve measured-vs-independently-verified status; do not erase all five into one unknown.
- N16/N17 is marked `consumed = ✓ Engine A`, while canonical N16 and the live board say callable builders/evaluators exist but no model consumes the corrected CFBD values. The two physical files now hash identically, but that proves promotion of data, not retraining/deployment into an Engine A model. Name the actual callable/research consumer or leave production-model consumption unproved.

Therefore “Step 2 is COMPLETE except B20-B24” is false even before the B20-B24 work.

### F5 — HIGH: §6E does not cover the exact §4.4 member set

The cadence table says only B20-B24 and N1-N8 remain open, but it omits or fails to name required members, including N14/N14b, N18b's two rows, N19, and N15b. Those rows need the same five fields or explicit evidence-backed N/A values.

Also, B20-B24 source-publish cadence must not be blank merely because their R7 states are not independently verified. The independently cleared remaining-candidate cadence artifact and canonical §4.4 already pin B20-B23 rhythms and B24's static-pinned/no-refresh state. R3 requires those dimensions to remain separate.

### F6 — MEDIUM: live canonical prose is stale against later sections

§6C still says R7/classes remain open and a fresh Gemini request is in flight, while §§6D/6E claim the work was completed. §6D is titled “complete” and then says it is open. These are live canonical claims, not a historical disposition appendix; reconcile them at source.

### F7 — MEDIUM: the new “growing store” rule names stores with no live capture job

§6B.3 says the rule applies to N12/N13 and N18b because each has a live capture job behind it. The same catalog classifies N12-N14b as manual/candidate and N18b as manual-only fallback/archive representations. The general rule (mutable counts require an as-of date) is sound; its claimed membership/reason is not.

## What holds

- FantasyCalc's canonical `fc_forward_capture.db` measurement and `acquisition defect` classification are sound.
- The eight freshness registrations / eight loaded dynasty jobs / non-identical-set finding is sound; no roster-capacity or league-opportunity job exists.
- Withholding `automatic_active_verified` from FantasyCalc is sound because no freshness policy establishes health.
- Leaving B20-B24 open rather than inventing per-row facts is directionally correct; the repair is per-cell verification, not inference.
- No checkbox should move. A-C remains open.

## Required disposition

Disposition F1-F7 in one pass, reconcile the canonical tables rather than append another correction layer, and route one fresh batch pin. The current pushed bytes are not content-CLEAR.
