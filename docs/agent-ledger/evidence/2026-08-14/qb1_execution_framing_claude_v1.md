# QB-1 Study Execution — Framing v1 (Claude, 2026-08-14)

**Cycle:** TW14-QB1-1 (opens on the scorer cycle's close; one run per worktree).
**Authority:** David's word today via Tower (TW14-QB1-HANDOFF): *"i want the QB1 study done.
QBs are the most important position in Superflex Dynasty - we need to have a strong model."*
— on top of his 2026-08-03 grants (execution · H5 loader bridge · `eval/` allowlist).
Grounding-layer full build DEFERRED on his word; nothing here touches it.
**Spec of record:** the RATIFIED pre-registration
`docs/validation/2026-07-21-qb-1-study-registration.md` + canonical JSON, binding pin
`37065566a9b372e329454cc51edbcf3de724fd1e5cc57a2f15cc547b1ae54c9d`. The registration fixes
every analytical choice; this framing covers EXECUTION MECHANICS ONLY and may not restate or
reinterpret a registered value.

## 1. The manager situation

Superflex makes QB the scarcest, highest-leverage asset class, and the latest trust-surface
backtest (Jun 13) shows the QB lane failing `g3_market_superiority_pass`. David has a
pre-registered, five-times-reviewed study designed to tell him — without forking paths —
whether the research pair's QB hypotheses (efficiency/rushing/volume/composite lanes vs
naive and vs expert consensus) hold on his own scoring rule. Executing it is the shortest
governed path to "a strong model" or to the honest knowledge that the current one is not.

## 2. Measured readiness (all probes this session, rerunnable)

| Item | State |
| :-- | :-- |
| Registration pin | **HOLDS** over the canonical 11,008-byte body (`37065566…` reproduced). The FILE carries one trailing newline (11,009 bytes; raw-file hash `eb56943a…`) — a post-emission byte appended by tooling. DISCLOSURE + RED row: the runner must hash the canonical object (as `build_registration` does), never raw file bytes, and must refuse on mismatch (`preregistration_missing`). |
| Analytical modules | 14 on disk in `src/dynasty_genius/eval/qb_validation/` incl. `folds.py`, `ridge_lane.py`, `comparisons.py`, `inference.py`, `study_matrix.py` — richer than the board's last record; the exact runner gap is a RED-time measurement, not an assumption. |
| Missing | The D3/D4 end-to-end orchestrator (no script under `scripts/` runs the study) and the H5 standalone-file bridge (`load_dynastyprocess_archive.py` reads via `git show` only — the registration itself names this gap at §9.1). |
| H5 substrate | **All four market snapshots SURVIVE** at `/var/tmp/dp-values/`, byte-identical to the §9.1 pins (4/4 SHA-256 verified this session). |
| H2 guard | **UNDER TEST** (Addendum A, commit `ae536f7`) — binding until execution + David's ruling on the registered result. No interim output is a result. |

## 3. Risks / mislead surface

- **Forking-paths discipline is the whole point:** the runner implements registered values
  ONLY; any "fix" that moves a registered value voids the pre-registration (protocol
  violation, never a patch). The RED pins refusal on pin mismatch and on drift (F7/F23).
- **H5 scratch fragility:** `/var/tmp` is scratch — a cleanup loses the only local copies,
  and re-retrieval is provider contact (David-gated). See Q2.
- **Result language:** every artifact `decision_supported=False` recursively; H5 outcomes
  read "keeps up with expert rankings," never "beats the market"; the 8 mandatory
  disclosures (§12) appear on every report; `support_status`, never `verdict`.

## 4. Execution design questions (cockpit; nothing reopens a registered value)

- **Q1 — H5 bridge shape:** a standalone-file loader honoring the §9.1 SHA pins
  (fail-closed on mismatch), the F32 name-reconciliation gate, and the §9.3 join gates.
  Authorized 2026-08-03; smallest honest form is a read-only adapter consuming exactly the
  four pinned files by path+hash.
- **Q2 — H5 durability:** copy the four files (hash-verified) into a gitignored store under
  `app/data/` with a `backup_manifest.json` entry landing TOGETHER with the populated store
  (the landing-order law), under David's standing 2026-05-30 approval for saving
  DynastyProcess data — vs leaving them in scratch. Repo commit stays prohibited
  (registration: no redistribution).
- **Q3 — output destination** (this answers grounding open question #1 for this program's
  slice): registered readout (prose + tables, disclosure-complete) under
  `docs/validation/`; machine artifacts under gitignored `app/data/validation_runs/qb1/`
  with the registration hash stamped in every artifact. Cockpit refines; David sees the
  readout only after execution completes.
- **Q4 — sequencing:** QB-1 opens as its own run after the scorer cycle's gate-path commit
  (one `run.json` per worktree). Framing → Codex challenge → RED (owner per 02: Codex, as
  in the scorer cycle) → GREEN (runner) → EXECUTE (deterministic, seeded 20260716) →
  registered readout → David's ruling. The ruling remains a separate David word (the
  registration says so); execution itself is granted.

## 5. Falsification seed families (for the RED, from the registration's own seams)

1. Pin refusal: absent/mismatched registration hash → `preregistration_missing`; post-pin
   drift → `registration_drift`; raw-file-bytes hashing rejected (the trailing-newline
   probe is the reproducer).
2. Scoring: `settings_hash_mismatch` refusal; 12-key rule applied to ALL seasons; excluded
   keys never reach the settings gate.
3. Leakage: features ≤ t−1 only; imputer/scaler fitted on test rows fails the fold by name
   (F2/F22); train/test season overlap refuses.
4. Manifests: absent column → `manifest_column_missing` (F15); H1∪H2∪H3 pairwise disjoint +
   H4 exactly-union (F27); age-cliff guard (F12).
5. Cohort/labels: qualifying-game rule exact; rookie exclusion honest; duplicate
   player-seasons/non-finite PPG/missing games refuse by name; ≥4-game slice reported
   never substituted (F29).
6. Inference: seeds deterministic (20260716; two runs byte-identical); BCa + cluster
   permutation per §7; fold floors → `unsupported_power`; `fold_starved` at n<20;
   `contradicted` never folded into `supported`; BH-FDR at q=0.10 across exactly 14.
7. H5: after-date ban (F19); §9.1 SHA fail-closed; F32 reconciliation >2% breach →
   `join_reconciliation_failed`; coverage <70% → `join_coverage_low`; status precedence
   total-ordered incl. `ci_p_disagreement`; `supported` impossible on H5.
8. Provenance gates: seven-dataset presence checks refuse whole-pool by name
   (`source_unavailable`); the §11 presence-not-authenticity limit restated, not
   engineered around.
9. Disclosure completeness: all 8 §12 disclosures present in every report;
   `decision_supported=False` recursive; banned-language scan.

## 6. Not doing

No registered-value changes · no rookie predictor · no KTC/trade-market contact · no
grounding-layer build (David deferred it) · no provider contact (the four files are already
local) · no commit/push outside gate paths · ruling on the result remains David's separate
word. H2 QB rushing remains **UNDER TEST** until that ruling.
