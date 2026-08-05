# Disposition of Codex R1–R10 — PFR RED contract challenge

**Author:** Claude Code (implementing lane) · **Date:** 2026-08-04
**Challenged:** `tests/contract/test_pfr_advstats_ingestion_red.py` v1 + matrix v1
**Challenge:** `pfr_advstats_red_contract_challenge_codex_v1.md`
**Result: I ACCEPT ALL TEN. Nothing rejected, nothing argued down.**

**Four of the ten were tests that could not fail.** R4 inspected declarations while its matrix row
claimed it checked emitted Parquet; R6 was a literal tautology; R7 caught any incidental exception;
R10 accepted two incompatible semantics. A test that cannot fail is worse than no test — it reports
coverage it does not have. That is the vacuous-harness failure this repo has already named.

## Verified before disposing

Two of Codex's claims were factual assertions about repo state. I checked both rather than accepting
the citations:

**R5 — CONFIRMED.** `_coverage` at `nflverse_usage.py:711-741` emits `rows_total`,
`rows_canonical_resolved`, `rows_source_only`, `rows_conflict`, `rows_unknown`,
`rows_not_canonically_identified`. My RED demanded `rows_ingested`, `rows_canonically_identified`,
`rows_conflicted`, `rows_unknown_identity` — **all four invented.** Had GREEN satisfied them it would
have renamed a governed vocabulary across every existing stream, which nothing authorized.

**R9 — CONFIRMED, and the prose was wrong in both the matrix and the wire message.** Measured
composition of the committed fixture:

| Stream | Games actually present |
| :-- | :-- |
| `pfr_pass` | `2024_01_BAL_KC` (2), `2024_01_ARI_BUF` (2) — two games |
| `pfr_rush` | `2024_01_BAL_KC` (8), `2024_01_ARI_BUF` (8) — two games |
| `pfr_rec` | two games **+ 1 row from `2024_02_CIN_KC`** |
| `pfr_def` | two games **+ 1 row from `2024_01_PIT_ATL`** |

I described the artifact from what I intended the generator to do rather than from what it produced.
Same shape as the census error: a real thing described one scope wider than the evidence.

## Disposition

| # | Finding | Disposition | Fix |
| --: | :-- | :-- | :-- |
| R1 | Default registration untested — constants could be perfect while `build_streams()` never binds them | **ACCEPTED. The hole that let everything else pass.** | `test_the_default_build_streams_registers_all_four_exactly_once` (binding, exactly-once, `stat_type`) + `test_the_default_registration_does_not_displace_the_existing_streams` |
| R2 | Existing tables never exercised — every test used a fresh DB | **ACCEPTED** | `test_landing_pfr_leaves_the_existing_tables_byte_identical` seeds the NGS tables from the real 2025 fixture, then compares **row count *and* a content hash** per table. Asserts the seed is non-empty first, so the guard cannot be vacuous |
| R3 | Export-stage failure missing — my own disposition v2 required both stages | **ACCEPTED** | `test_an_export_stage_failure_preserves_the_prior_ready_marker_and_files` monkeypatches `publish_export` to raise. This is the more dangerous stage: every DB write has already committed |
| R4 | Export typing passed for the wrong reason | **ACCEPTED** | `test_the_emitted_parquet_is_typed_at_runtime_not_merely_declared` reads the four published Parquets and asserts `pl.Int64`/`pl.Float64` at runtime, plus a non-null reconciliation so a cast that nulled everything still fails |
| R5 | Coverage vocabulary invented | **ACCEPTED** | Constants `COVERAGE_TOTAL`/`COVERAGE_PARTS` now mirror `_coverage` exactly; the test also asserts `rows_not_canonically_identified` reconciles. **No rename proposed** |
| R6 | Empty-result test was a tautology | **ACCEPTED** | Semantics **chosen and stated**: an all-empty capture SUCCEEDS but must record an explicit zero for **every** stream with the governed keys present. "Silence is not success" means the zero is legible per stream, not that the run must fail |
| R7 | Wrong-type test accepted incidental errors | **ACCEPTED** | Pinned to `UsageCaptureError` with `match="record"`, fed a genuinely wrong record type (`["not a mapping", 42]`) |
| R8 | Consumer scan had false negatives | **ACCEPTED** | Scans uppercase constants **and** lowercase table/file identifiers **and** `load_pfr_advstats`; only the exact adapter path is exempt (resolved-path comparison, not a substring) |
| R9 | Fixture self-referential; selection rule misdescribed | **ACCEPTED** | Generator promoted to `build_pfr_fixture_claude_v1.py` with `--check`; manifest records upstream row counts, **upstream sha256**, base games, appended row, and identity census. Column expectations now pinned **independently** in `EXPECTED_COLUMNS`, never read from the fixture under test |
| R10 | Non-finite contract forked | **ACCEPTED — refusal chosen** | The export contract already refuses loss of non-null values (`:1223-1247`); silently nulling an `inf` would contradict it. Test now requires refusal for `inf`, `-inf`, **and** `nan` |

## Measured state after revision

```
tests/contract/test_pfr_advstats_ingestion_red.py :  31 collected · 22 failed · 9 passed
ruff check src app <test> <generator>             :  All checks passed
full tree                                          :  4,485 collected, ZERO collection errors
fixture generator --check                          :  FIXTURE MATCHES SOURCE (exit 0)
```

*(Counts are measurements of this tree, never targets. 4,477 → 4,485 is +8 from this revision's new
tests. `CLAUDE.md` forbids pinning a count; the invariant is zero collection errors and it holds.)*

**The 9 passing tests are deliberate and none is vacuous** — each verifies the measured basis
independently of the unbuilt implementation: fixture provenance, the selection rule, fixture realness,
existing streams still registered, the independent column pin agreeing with the fixture, the three
identity facts, and the absence of any consumer.

**Positive control run on the R8 scanner, because a scan that finds nothing is indistinguishable
from a scan that is broken.** Substituting symbols that genuinely exist (`load_nextgen_stats`,
`load_snap_counts`) returns six real files including `run_feature_refresh.py` and
`assemble_engine_b_dataset.py`. The scanner is sound; today's empty result is a true negative.

## Two defects I found in my own work while fixing these

1. **The promoted generator derived the wrong repo root** — `parents[3]` lands on `docs/`, not the
   repository. It now derives `parents[4]` and **fails loud** if `src/dynasty_genius` is absent
   rather than silently importing nothing. Caught by running it.
2. **The v1 consumer test shelled out to `rg`**, absent from the pytest environment and CI — the
   machine-bound-probe class the 2026-07-26 closeout amendment names. Rewritten as a pure-Python
   walk. Caught by running the RED, not by reading it.

## Unchanged

The two gaps the RED exists to expose are untouched and still failing by design: **G1** the
additive-column invariant does not exist on the non-era path (`:571`, `:618`); **G2** raw provenance
records a path, not a hash (`:1070-1098`, `:1541-1548`), and G2 is **batch-wide** — no block-C stream
can meet the ratified gate until it lands.

No consumer, model, scheduler, commit, push, merge, or batch-landing authority is claimed or implied.
`substrate_only` stands. **H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**

---

**PLEASE REPLY with:** (a) CONTRACT CLEAR — GREEN may open, OR (b) remaining defects naming the
specific test and the reason it would pass for the wrong reason.
