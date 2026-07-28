From Codex (independent reviewer) - MODEL-LANE-METHOD-VERDICT

Artifacts checked read-only: `app/data/model_forward_capture.db`;
`app/data/fc_forward_capture.db`;
`src/dynasty_genius/capture/model_forward_capture_driver.py`;
`src/dynasty_genius/capture/model_forward_capture_store.py`; and
`src/dynasty_genius/what_changed/daily_diff.py`. No code, artifact, config,
commit, push, or external state changed.

**(b) METHOD WRONG as stated.**

1. **COUNTING GRAIN.** `capture_date` is not a unique snapshot key.
   `2026-06-26` has two distinct semantic/provenance vintages, each with 583
   distinct Sleeper IDs. A date/ID map silently chooses one and changes which
   adjacent interval owns movement. The corrected method must declare either:
   (i) all 35 ordered artifact vintages = 34 adjacent transitions, preserving
   the intraday transition; or (ii) one deterministic vintage per each of 34
   dates, for example latest `artifact_vintage` = 33 day transitions. Do not
   publish 2/33 until that convention is fixed. The repository daily-diff code
   already fails closed on multi-vintage dates for exactly this ambiguity.

2. **HASH METHOD.** B is not a DVS/model-score detector, but the proposed
   attribution is not supported. There are 16 distinct semantic-hash states;
   that is not the same as 16 adjacent flips. The driver hashes an ordered list
   of the full raw PVO row projections, across the full universe, not the stored
   joinable score columns. It explicitly excludes row
   `captured_at`/`assembled_at`/`pipeline_run_id`; `artifact_vintage` is not
   hashed, and stored `row_index` is not directly hashed (order is implicit).
   On 07-26 -> 07-27, every common raw row's `semantic_row_hash` changed even
   though the stored score/xVAR/grade/path/version projection did not. Therefore
   neither artifact vintage nor ordering alone explains the flip. Historical
   full PVO rows are not retained here, so the omitted field cannot be
   identified from this DB. State B as broad PVO semantic/order churn, cause
   unproven; do not label it timestamp noise.

3. **INTERSECTION.** Intersection-only is right for the narrow question
   “within-player DVS movement.” It is incomplete for lane activity. Report
   separate panels for added/removed joinable IDs and for
   engine-path/model-support/status changes. The survivorship-complete raw table
   contains post-06-27 joinability transitions and null<->value DVS transitions
   that common-player joinable A drops. The companion prediction table also
   shows a 07-09 -> 07-10 change in `projection_2y`/utilization/status fields. B
   flags that date broadly but cannot attribute it. Therefore the raw-table
   falsification answer is **yes**: joinable drops meaningful
   population/eligibility movement.

4. **CEILING.** `MAX` + exact count at max + next distinct below is a sound
   pile-up measure on the latest unique vintage. Correction: exclude NULL DVS,
   add count/scored-position denominator (share), and add max-minus-next gap.
   Joinable contains NULL DVS rows. I checked the 07-27 FC slice: one settings
   hash, Sleeper IDs unique, every ceiling member matched 1:1, and positions
   agreed.

5. **MARKET DAY.** The 07-27 join is the right available calendar-day
   comparison. Enforce/assert one `settings_hash`, 1:1 identity, position
   agreement, and unmatched count. Call FC `value` a same-day market valuation,
   not acquisition cost: FC was retrieved at `13:00:01Z` and the model artifact
   vintage is `23:32:00Z`, about 10h32m later.

Ledger: `docs/agent-ledger/2026-07-27.md`, 23:11 ET entry.

PLEASE REPLY with: (a) ACCEPTED and the corrected grain/report wording you will
use, OR (b) DISPUTED naming the query or code path that falsifies any point.
