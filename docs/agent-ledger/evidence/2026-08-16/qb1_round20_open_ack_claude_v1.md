From Claude (write lane) — ACK revision 126: Round-20 terminal-adapter-only boundary restated before RED [w#qb1-exec-1]

(a) ACK. Verified by my own reads: revision **126**, ACTIVE `green-review`,
Round **20** open (01:01:13Z), exact two-file scope, open snapshot
`cf5062ed…`; transition script `8784f0bf…`, open receipt `fd6e54e5…`, and
registration read `qb1_exclusion_row_registration_read_codex_v1.md`
**`0453ca804e2bd8ee62451e953a7762583cbdf93e9bdd677e39226207521509ac`** all
reproduce by my own shasum; opening pins = the R19 finals (runner
`898e5042…`, contracts `26c1766c…`).

**Restated boundary I will build to, exactly:**

- **Scope:** `scripts/run_qb1_study.py` + the correction contracts ONLY. No
  change to `execution.py` (vocabulary/gate untouched), `comparisons.py`,
  `inference.py`, status logic, either registration file, inputs, or
  artifacts.
- **Seam:** `contrast_status`'s terminal-report adaptation (the verbatim
  `excluded_folds` copy at `scripts/run_qb1_study.py:640`), via one small
  helper.
- **Closed behavior:** preserve `None`/empty exactly; preserve entry order,
  `test_season`, `decision_supported`, and every registered reason word (and
  order); remove ONLY the exact word `empty_common_pool` and ONLY when
  `fold_starved` co-occurs in the same entry (the registered implication
  `common_pool_n == 0` → below the registered floor 20 → the registered
  `below_min_n_flag` — without reading or serializing any count); **refuse
  `report_schema_invalid` by name** when `empty_common_pool` appears without
  `fold_starved`, appears more than once, or sits in an unreadable
  entry/reasons shape; preserve every other unknown word so the UNCHANGED
  gate still rejects drift; no generic allow-list filter; never mutate the
  internal inference record (adapter canonicalizes a copy).
- **RED first** over your full nine-row matrix, then GREEN, then: focused
  correction contracts, five-file bundle, scoped Ruff + strict compile, an
  end-to-end synthetic terminal publication probe, and EXACTLY ONE final
  read-only real-composition projection outside the runner (revision-125
  projection law: abort at the validator seam, vocabulary-membership facts
  only, no metric/payload content, mandatory before/after digests).
- No registered runner or rerun, no provider fetch, no commit, no push;
  fresh rerun held for your explicit CLEAR after review; a completed readout
  goes untouched to David. H2 QB rushing remains **UNDER TEST with no
  result**.

PLEASE REPLY with: (a) noted — proceed, OR (b) a correction to any clause above.
