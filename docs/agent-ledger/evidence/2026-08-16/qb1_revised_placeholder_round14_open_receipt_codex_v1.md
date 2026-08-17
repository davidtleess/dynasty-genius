# QB-1 Revised-Placeholder Round 14 Open Receipt — Codex v1

Date: 2026-08-16 10:12 ET  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`

## Authority

David authorized one bounded round in these words:

> approved - open one bounded round per your sanctioned mechanism: claude implements your revised placeholder predicate exactly (missing player_id AND missing position AND exact validated zero across all 17 D2 inputs, names as audit evidence only, label-builder records only, full pool untouched to the matrix), and on your explicit clear the already-granted rerun fires - the registered readout then comes to me for my ruling

## Pre-apply state

- Revision `80`; `phase=blocked`; `terminalState=BLOCKED`.
- Round 13 closed with unresolved criterion
  `R13-G1-LABEL-PLACEHOLDER-PREDICATE-INCOMPLETE`.
- Round-13 close snapshot:
  `0ebb1bf627a928389ab52df8e6ede6b763be62e077c6f81419df284efe1ba027`.
- Corrected registration read SHA-256:
  `729c68e074d49a6c1b6c6abf7b85236d36c390ec8f65f8b084f25f2c3114fdce`.
- Failed terminal artifact SHA-256:
  `fb222a60957e2ae4a353ed730ff5ddccdfac5cb9bbc803cdc2cefe6c62306244`.
- Opening runner pin:
  `8a559c314823ffcb572c020f85268c04e7f782861a88e5d42abf639e045907bf`.
- Opening contract pin:
  `634d7ce76521b63c26b8021c0c6926a11440b17410c4cc86229c9c635fe8afa3`.

## Applied transition

Transition artifact:
`docs/agent-ledger/evidence/2026-08-16/qb1_revised_placeholder_round14_open_codex_v1.mjs`,
SHA-256
`08ff5b0975bdda39e709d497473fac5bb422085ae468358c7f763e9cdf9e81e9`.

`node --check` passed. The default dry run loaded revision 80 and reproduced
the expected two-file snapshot hash. The `--apply` form then wrote through
the revision-guarded atomic `persistRun` path exactly once.

- Persisted revision: `81`.
- Phase: `green-review`.
- Terminal state: `null`.
- Open round: `14`.
- Open snapshot:
  `0ebb1bf627a928389ab52df8e6ede6b763be62e077c6f81419df284efe1ba027`.

Independent post-apply `jq` and file-hash reads reproduced revision 81, the
full authorization record, the open snapshot, and both opening pins.

## Bounded implementation and execution boundary

Claude may change only:

- `scripts/run_qb1_study.py`
- `tests/contract/test_qb1_green_correction_contracts.py`

The exact classifier is missing `player_id` AND missing `position` AND exact
validated zero across all 17 D2 inputs. Names are audit evidence only. It
applies only to copied records passed to `build_label_table`; the full admitted
pool remains untouched for `build_study_matrix`. Any nonmatching, unproven,
malformed, nonzero, identified, or nonmissing-position row remains fail-closed.

The already-granted registered rerun remains held until Codex issues an
independent explicit CLEAR. No input mutation, registration or publication-gate
change, provider fetch, commit, or push is authorized. H2 QB rushing remains
UNDER TEST with no result.
