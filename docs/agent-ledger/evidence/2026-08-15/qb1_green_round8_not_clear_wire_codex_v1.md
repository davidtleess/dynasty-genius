From Codex (independent review lane) - QB-1 GREEN round 8 NOT CLEAR; three reproducible BLOCKERs

Reviewed exact pins: execution 913225f529a0c63a30b4ee6b025c3d1ac408a5d6107be15b8a65dc80d83e9f37; runner ef7a8244d5b141eaa7280f37b269531089f5eeeb6649b230b09fcbe50bde86eb; contracts 513ed1bd255c9c62368bcb68f8cacfbfdc3284aa5c9df3a0c8a36affd46b9b58. Full review: docs/agent-ledger/evidence/2026-08-15/qb1_green_round8_review_codex_v1.md SHA-256 4f155f1e04fbefeb492675d76a4d9dffa49f69a38f1831cfef008bed7668d47d. Public-runner probe: qb1_green_round8_adversarial_probe_codex_v1.py SHA-256 750f8213945cccf71c969ce7417ed4f7577ee5e7a709c988418a4b57a1bb254b, 4/4 passed (passing is the defect).

BLOCKER R8-G1-H5-SPECIAL-CASE: execution.py:1291-1335 checks only status/flags when any H5 numeric is missing below floor. Public runner accepts 2 folds, partial p/delta evidence, missing adjusted_p_ni and one-sided bound, and ni_met=True as unsupported_power. The honestly-unavailable exception must be exact: all inference numerics null, ni_met=False, registered status and exact flag; partial evidence refuses.

BLOCKER R8-G2-EVALUABLE-RECONCILIATION: execution.py:1388-1468 counts H5 metric-key presence. Public runner accepts c11 evaluable_folds=4 when one keyed fold has paired_delta=None, both Spearmans null, common_pool_n=0. Derive and compare the actual evaluable-season set; reconcile exclusions as the registered complement.

BLOCKER R8-G3-F13-TOTALITY: execution.py:1714-1727 checks only claimed True flips and never sums case booleans into aggregate counts. Public runner accepts a 401-yard/5-game case reporting the mechanically required plus flip as False, and separately accepts a True case flip with aggregate count zero. Require exact booleans both directions and aggregate equality.

Checks: submitted/frozen bundle 646/646; prior R7 probe now rejects 9/9; Ruff + strict compile clean. R7-G4 and closed margin leaves checked without findings.

Structured state: findings 8-1..3 recorded; round 8 closed, churn 3 files/657 lines; failed-review receipt terminalized revision 50 BLOCKED. No further round is authorized; prior Judge STOP is spent. No study execution, publication, or push. H2 QB rushing remains UNDER TEST with no result.

PLEASE REPLY with: (a) ACK of the three recorded blockers and David-gate parking, OR (b) dispute with reproducible evidence.
