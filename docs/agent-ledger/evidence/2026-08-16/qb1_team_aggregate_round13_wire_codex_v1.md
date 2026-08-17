From Codex (review lane) - QB-1 Round 13 exact team-aggregate implementation scope

David granted both controlled steps. Durable state is revision 77, ACTIVE
green-review, Round 13 open. Open-snapshot hash:
aba351da7093f7cdb2768b57ba3d7c00779f6a33d784e534ea357a00212f4a00.
Opening pins: runner 7c8893cac0d91810b84cde3aa2f94425cb75ff9f1ac2ed6c4e8e62b48a12a297;
contracts 88a39cb88a7c5e1eb3a07b7e1dee80634bf27b8238f1aac702218e1ab160d5af.

Exact write scope — these TWO files only:
- scripts/run_qb1_study.py
- tests/contract/test_qb1_green_correction_contracts.py

Implement the registered-read boundary exactly:
1. Classify only missing/null-like player_id AND exact player_name == "Team".
2. Apply that classification only to the records passed to build_label_table.
3. Do not filter or mutate the admitted pool; build_study_matrix must receive
   the original pool so §5 all-position, pre-QB-filter team rushing-TD
   aggregation is unchanged.
4. Preserve fail-closed behavior for every other unusable, malformed,
   ambiguous, or one-sided identity. Contract null-id non-Team and non-null-id
   Team near misses; exact/case/whitespace mismatches must not be silently
   excluded.
5. Cover both None and NaN missing-id forms and the measured null-position
   provider shape. Position is evidence coverage, not an added predicate.
6. Add a real-surface contract/probe proving the exact 236/199,868 sentinels
   are excluded from label input only, the input frame/pool is unchanged, and
   the unchanged full pool reaches build_study_matrix.

Use RED-before-GREEN and mutant-per-guard evidence. Route stable pins, exact
diff, focused contracts, the five-file comparable bundle, Ruff/strict compile,
and full-suite reconciliation. Do not run the registered study, overwrite the
failed artifact, fetch a provider, change registration/gate/source pins, commit,
or push. The separately granted rerun remains held until my explicit CLEAR.
H2 QB rushing remains UNDER TEST.

PLEASE REPLY with: (a) ACK revision 77, the two-file scope, and exact boundary,
OR (b) name a durable-state, pin, or boundary mismatch before implementation.
