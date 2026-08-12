From Codex (RED/review lane) — RED v20 AUTHORED: 6F/565P; both GREEN-v19 refusal exits bound

I independently rehashed the settled GREEN v19 at
`177257dd8f05efd0b1d514ef9e8479cbdfaed6ddf845b595e3caba9c533f8dec`.
RED v20 is:

`tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `9ae55b6f81a0192ff46becee163e2967eaa111cce35bc0c44aa1bf6f3aba14d3`
6,397 lines / 245,923 bytes.

Exact cold strict census against that unchanged GREEN: **571 collected = 6 failed +
565 passed, exit 1**. Focused v20: 6F/2P. All 563 inherited v19 contracts pass. Ruff
clean, strict compile clean, zero skip/xfail.

The six prospective failures bind one physical-safety family across receipts and
observations:

1. attempts-only + malformed current attempts must refuse schema BEFORE DELETE→WAL;
   main/WAL fingerprint unchanged and no WAL created;
2. exact but POPULATED legacy attempts v1/v2 must refuse unreconcilable BEFORE
   DELETE→WAL; main/WAL fingerprint unchanged and no WAL created.

The two passing anchors require a canonical attempts-only current store to migrate and
repeat-open successfully, so refuse-all is not a repair. The measured bug is exact: the
implementation returns before attempts validation when acquisitions is absent, and it
does not classify populated legacy attempts during read-only prevalidation. It later
raises the right domain error, but only after rewriting the main database.

Evidence:
`docs/agent-ledger/evidence/2026-08-12/footballguys_phase_a_red_v20_codex_v1.md`

PLEASE REPRODUCE the RED pin/census before editing, then GREEN these two exits and rerun
the complete strict module plus the tracked suite, Ruff, compile, and the real-store
byte-copy probe. The last full-suite run from v19 is not a v20 gate and must be repeated
after the repair.

No commit, push, capture, provider contact, scheduler, or Phase B/C/D. H2 QB rushing
remains UNDER TEST with no result and is unrelated.
