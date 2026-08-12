From Claude Code (implementing lane) — GREEN v20 GATED AGAINST THE FROZEN PIN · ready for review

ACK on the amendment: I am citing ONLY the frozen pin `88bcc54e…` and I am not citing my earlier
6F/565P reproduction or the 575-pass run that crossed your moving RED. Both void as whole-run
claims, as you said.

FROZEN RED PIN, verified by me BEFORE and AFTER every run below:
  tests/contract/test_footballguys_phase_a_red.py
  SHA-256 88bcc54efbb069a77f2621808db11f1e57e609e3897ccd635c94bc4b609dc0f7
  6,424 lines / 247,107 bytes — matches your final pin exactly.

GREEN under review:
  src/dynasty_genius/sources/footballguys_intake.py
  SHA-256 6fbac8af65c5f0c2eba92688a4ee7c600e0949b644262fc304a166076e2d14ca

GATE CARD — every number below was taken with the pin hash re-verified on both sides of the run,
so none of them can have crossed a moving tree:
- strict `-W error` module: **575 passed, exit 0** (exit code captured, not inferred)
- full tracked suite: **15 failed / 5,808 passed / 12 skipped / 9 xfailed, ZERO collection
  errors**, 498.14s. All 15 failures are tests/contract/test_governed_cadence_inputs_red.py — the
  standing UNTRACKED cadence RED, unrelated to this pair and failing identically before my change.
  Suite exit is 1 for that reason alone.
- ruff clean · strict `py_compile -W error` clean · `git diff --check` clean
- real-store byte-copy probe: **0 failures**; live receipts/semantics hashes `ceac8dee…`
  unchanged before and after.
- PINS AFTER the full suite: RED `88bcc54e…`, GREEN `6fbac8af…` — both identical to the start.

THE REPAIR, against your six negatives and two positive anchors:
In `_classify_acquisition_store`, attempts is now classified BEFORE the acquisitions-presence
early return. Two exits are bound read-only:
1. attempts present but matching neither the current grammar nor an exact legacy grammar →
   `store_schema_unmigratable:{store}` — reached through pure reads, so an attempts-only
   malformed store refuses with main/WAL byte-frozen and no WAL materialised.
2. attempts matching an exact legacy grammar but POPULATED → `store_migration_unreconcilable:
   {store}`, also read-only. Row state is treated as a refusal-class property rather than
   something discovered mid-migration after the journal-mode write.
The acquisitions-absent early return still stands AFTER those checks, which is what keeps your two
positive anchors alive: a canonical attempts-only current store, and an empty exact legacy
attempts-only v1/v2 store, both still migrate and repeat-open, with the sqlite_sequence high-water
preserved by the v19 restore path.

YOUR AMENDMENT WAS LOAD-BEARING AND I WANT THAT ON THE RECORD. Before it, "refuse every legacy
partial store" satisfied all six physical-mutation negatives. My first repair instinct was exactly
that shape, and only the positive family forced the narrower fix. That is the second time tonight
an adequacy audit of yours caught a repair that would have passed a contract while breaking the
product.

REVIEW TARGETS — my remaining doubts, unchanged and still unproven by me:
a) `_index_signatures_governed(conn, "acquisitions")` is applied to legacy stores; I inferred
   autoindex coincidence across legacy v1-v3 from green tests rather than proving it.
b) The populated-attempts count now runs on a read-only connection before any write — confirm
   there is no legacy shape where `SELECT count(*) FROM attempts` itself raises rather than
   refusing by name.
c) Ordering: inventory → attempts grammar → attempts population → acquisitions-absent return →
   acquisitions grammar → index signatures → marker identity. If any pair of those is
   order-sensitive in a way I have not seen, it is here.

No commit, push, capture, provider contact, scheduler, or Phase B/C/D. Landing is David's word.
H2 QB rushing remains UNDER TEST with no result.
