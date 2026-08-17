# QB-1 F34 college cross-check — Codex registration read

Date: 2026-08-16  
Run: `f8f7551c…`, revision 110 diagnostic continuation  
Disposition: **IMPLEMENTATION, not amendment**  
H2 status: **UNDER TEST with no result**

## Evidence audited

- Claude diagnostic v2 script SHA-256:
  `af612c030c211b79825314a4b51264c939dc098d5bd2a3cdda5c3451475ace3d`
- Recorded output SHA-256:
  `404fefce1d3e74c02857291f29935d1e0c7621d646373a6b4a4a58efd2c31a64`
- One admission/load pass, 17 paths loaded once; all seven admitted frame
  digests unchanged; matrix/F34 ceiling only; no folds, ridge fit, inference,
  comparison, report, composition, or registered rerun.
- Complete H4 refusal set: 143 unique `(player_id, target_season)` keys across
  49 players. Every key is `target_evaluable`, `cohort_admitted`, label-present,
  below the >50% row-drop threshold, null in all three draft-capital members,
  and linked to shipped `TRIAGE/cross_check_conflict/gsis`.
- All 49 affected players have exactly one GSIS draft candidate, matching GSIS
  and normalized name, an age check passing with delta zero, and valid draft
  round/pick. The only refusing clause is current college whole-string
  inequality.
- Morphology reconciliation: 23 multi-school histories whose current
  normalized token set contains the draft school exactly; 4 multi-school
  histories whose draft school is the same institution under a provider alias;
  22 single-school provider alias/abbreviation/qualifier variants. Total 49.
- Independent frozen-row audit reproduced those 49 pairs and audited all 69
  matrix-player TRIAGE identities. A closed canonicalization consisting of
  semicolon tokenization, terminal `St.`→`State`, terminal `Col.`→`College`,
  and the exact provider aliases below reconciles 67/69. The two residuals are
  genuine fallback-name conflicts and must remain TRIAGE:
  `Ryan Griffin` (study Tulane vs matched drafted Ryan Griffin, Connecticut)
  and `Anthony Brown` (study Oregon/Boston College vs matched drafted Anthony
  Brown, Purdue).
- Product/report pins remained byte-identical throughout the diagnostic,
  including `identity.py` `aacb56fc…`, `study_matrix.py` `6c607bad…`,
  `ridge_lane.py` `02e7a980…`, runner `7de911cc…`, correction contracts
  `200c6dee…`, and failed terminal report `bb70130d…`.

## Registered clauses

Registration §10 makes `draft_picks` authoritative, uses `gsis_id` as the
primary key, and requires a college cross-check in which **both strings are
normalized** and a both-present **mismatch** becomes `TRIAGE`. It also requires
fallback age to pass, forbids silent UDFA conversion, and makes true
draft-capital gaps non-imputable. Registration §5 pins the H4 draft-capital
group and likewise says true source gaps fail closed rather than enter the
median imputer.

The registration therefore pins semantic college agreement after
normalization; it does not pin raw whole-field equality over a provider field
that encodes a semicolon-delimited school history. The shipped `_college_check`
normalizes the unsplit container string and compares it to one draft school.
That treats representation differences as source conflicts even when the
registered primary identity, normalized name, age, and institution all agree.
Normalizing the provider's list structure and closed aliases implements the
registered comparison. Removing the college check, accepting fuzzy similarity,
or turning a genuine mismatch into DRAFTED would be an amendment and is not
authorized.

## Exact bounded implementation

Round 18 is confined to:

1. `src/dynasty_genius/eval/qb_validation/identity.py`
2. `tests/contract/test_qb1_green_correction_contracts.py`

Implement one private college canonicalization path used only by the existing
F34 `_college_check`:

1. On the **players/study side only**, split a present `college_name` on the
   literal semicolon. Normalize each nonempty institution token independently
   with the existing `normalize_name` law.
2. Normalize the draft row's single `college` value with the same law.
3. At institution-token boundaries only, canonicalize a terminal `st` token to
   `state` and a terminal `col` token to `college`.
4. Apply only this closed exact alias table after step 3:
   - `n c state` → `north carolina state`
   - `ucf` → `central florida`
   - `miami oh` → `miami ohio`
   - `uab` → `ala birmingham`
5. A both-present college check passes iff the canonical draft institution is
   an exact member of the canonical study-institution set. Disjoint sets remain
   `conflict`. Either side missing remains `missing`, preserving the registered
   degraded-check/age law.

No substring, prefix, edit-distance, fuzzy, city-dropping, initials heuristic,
player allowlist, or H4-row allowlist is permitted. Do not bypass the college
check merely because GSIS/name/age agree. Resolver route precedence, ambiguity,
age checks, drafted-capital validation, UDFA constants, TRIAGE reasons, matrix,
ridge lane, registration, manifests, frozen inputs, and report schema remain
unchanged.

## Required falsification and real-surface proof

- RED-before-GREEN contracts for all three measured false-conflict
  morphologies and each closed alias rule.
- One-field near misses proving a non-member institution remains
  `cross_check_conflict`; missing values retain the degraded age law; bad age,
  fallback ambiguity, duplicate GSIS, invalid capital, and missing identity
  retain their named closures.
- Exact negative controls for the two genuine fallback-name conflicts above:
  both remain TRIAGE and never become UDFA/DRAFTED.
- Real admitted matrix/F34 replay at final pins:
  - the 49 affected players / 143 H4 rows resolve to authoritative DRAFTED
    capital with round/pick unchanged;
  - all 67 representation-only TRIAGE identities become DRAFTED;
  - the two genuine fallback conflicts remain the exact residual TRIAGE set;
  - zero H4 gate-surviving row carries null draft capital;
  - complete before/after resolution counts reconcile in both directions;
  - admitted frame digests remain unchanged.
- Correction contracts, the existing five-file QB bundle, scoped Ruff,
  `py_compile`, and exact two-file diff/hygiene checks.

No registered rerun occurs during Round 18. A fresh rerun may fire exactly once
only after Codex independently reviews the stable final pins and explicitly
CLEARs the round. Any successful registered readout goes untouched to David for
his ruling; any failure remains fail closed by name.
