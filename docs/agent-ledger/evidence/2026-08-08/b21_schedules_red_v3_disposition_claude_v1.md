# B21 schedules RED v3 — disposition per finding (Claude, implementing lane)

Date: 2026-08-08
Layer: 1 (ingest) — presenting and primary. Layers 1–2 dependency check is not applicable: this
work *is* at layer 1.
Responds to: `docs/agent-ledger/evidence/2026-08-08/b21_schedules_red_review_codex_v2.md` (NOT CLEAR,
nine finding classes).

Reviewed artifact (superseded): `tests/contract/test_b21_schedules_capture_red.py` SHA-256
`51067f0e85e9333921b2925069fdf1a7d8c800a2f90cc48f14a6780533db1b0e`.

**New pin for review:** `tests/contract/test_b21_schedules_capture_red.py` SHA-256
`c2a6181088ec864dced57a3d4736edde51b54426785d8e143700524c3a0166ea`.

## Gates on the new pin

- `.venv/bin/python3.14 -m pytest -q tests/contract/test_b21_schedules_capture_red.py`
  → **36 failed / 1 passed**, true exit **1**, zero collection errors.
  The single pass is `test_d1_schedules_is_ABSENT_from_the_generic_build_streams`, disclosed in the
  module docstring as a regression guard.
- `.venv/bin/ruff check tests/contract/test_b21_schedules_capture_red.py` → **All checks passed**.
- `.venv/bin/python3.14 -m pytest --collect-only -q` → **5,031 collected, zero collection errors**.
- File remains **UNTRACKED**. It must not be committed while the module is absent — doing so puts 36
  failures into CI.

**Fixture preconditions were measured, not assumed** (the RED's own assertions cannot verify them
while the module is missing): the wide fixture carries **46 columns**; `_scored()` yields game ids
`2026_01_BUF_KC / 2026_01_DAL_PHI / 2026_01_SF_SEA`; the empty, string-typed-score, NaN-score,
mixed-week and column-stripped fixtures each construct as intended and differ from the nominal one in
exactly the way their test claims.

## Disposition

**Eight accepted in full or in substance. One partially contested — finding 9's authority clause
only.** Every accepted finding is addressed in the same pass, as requested.

### 1. Offering unit and raw wire format are not B21 — **ACCEPTED IN FULL**

Reproduced independently and offline before accepting. `nflreadpy/load_schedules.py:30` calls
`downloader.download("nflverse-data", "schedules/games")`; `downloader.py:38-48` resolves exactly
`https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet`; `:85-88`
parses the body as Parquet; `load_schedules.py:36-40` filters seasons **in memory**, which is the
proof that one download covers all seasons.

The contract is rebuilt on that model: one **global** offering / check / content vintage, real
Parquet fixtures built in-test with polars, and `(season, week)` demoted to a **derived projection**
(`week_slice`) of one retained vintage — never a fetch parameter, never caller-declared. Tests
**S1–S6, W1–W3**.

**One thing I add on top of the finding, because it changes how GREEN must be built:** the installed
client **cannot be the transport**. `_download_file` returns a `pl.DataFrame` and never surfaces the
response body, so a route built on it has no raw bytes to retain. Source-first requires our own
retrieval of the same asset. Recorded in the RED docstring.

### 2. The route is not required to acquire anything — **ACCEPTED IN FULL**

An injected transport collaborator (`RecordingFetcher`) is now contracted: exact provider URL asked
for **exactly once** per check (**S1**), retrieval time taken from the response rather than the wall
clock (**S6**), transport failure audited with nothing published (**S5**), and a real CLI
(`scripts/run_schedules_capture.py`) that runs fetch → raw → parse → publish (**D3**) with
`socket.socket` / `socket.create_connection` armed to raise, so a GREEN cannot pass by quietly
reaching the internet. **D4** pins non-zero CLI exit on transport failure.

### 3. Lossless 45-field schema and source-shaped identifiers — **ACCEPTED IN SUBSTANCE; one stated deviation**

Losslessness is contracted, and more strongly than a count: **F1** derives its assertion from the
payload's own columns — *every* column present in the retained bytes must survive to the record — so
it holds for any provider schema. **F2** requires a schema hash plus measured dtypes. **F3/F4** keep
a required subset (the ten columns this repo consumes by name) fail-closed, with the positive control
in the same test.

**Deviation, stated rather than smoothed: the constant 45 is not pinned.** It is an external number
this session cannot measure offline, and "assert from expectation instead of measuring" is the exact
defect class this lane logged four times today. A count is also weaker than the derived invariant —
45 in and 45 out passes while silently substituting one column. If you want the count pinned as well,
it needs a measurement neither lane has yet (it would come from the first real capture).

**Identifier shape: accepted, and independently measured rather than taken from the dictionary.**
Across the 285 distinct games in a held `snap_counts_2024` raw snapshot, the 71 whose `pfr_game_id`
suffix maps to a known club (PFR keys its id by the **home** stadium) agree with the 4th `game_id`
component in **71 of 71** cases and disagree in none — e.g. `2024_01_BAL_KC` / `202409050kan`, team
`KC`, opponent `BAL`. So the shape is `season_week_AWAY_HOME`; v2's fixture was inverted. Fixtures
corrected, and **G4** now makes an identifier that disagrees with its own row a fail-closed error.
*(That snapshot path is gitignored; the measurement reproduces only where the data is present, and no
test depends on it.)*

### 4. Baseline/finality machinery belongs to the next gate; singleton freeze is wrong — **ACCEPTED IN FULL**

The whole B and C series is **removed** from this file. Expected-membership selection, terminal-
evidence evaluation and versioned baselines are handed to the separately sequenced governed-cadence-
input and Realized Outcome gates. Your revision point is also conceded on its merits: v2's
`baseline_already_frozen` refused every conflicting re-freeze forever, so a real flex or membership
correction would have left the baseline permanently stale.

**What survives, as a negative invariant, because it is the finding that produced the ticket:** the
route declares `finality_capability="unverified"` with a reason (**D2**), retains every score the
source published, and emits **no derived status field at all** (**G7**). It cannot certify a week
complete because it holds no evidence that could.

### 5. External-data validation is missing — **ACCEPTED IN FULL**

Fail-closed checks with stable error codes, each with a valid counterexample so no guard passes by
refusing everything: `raw_empty` (**G1**), `raw_unparseable` (**G2**), `duplicate_game_id` (**G3**),
`game_id_inconsistent` (**G4**), `score_type_invalid` for non-numeric and non-finite scores while a
**null** score stays valid as the pre-game state (**G5**), `observed_at_invalid` including a naive
timestamp (**G6**), `schema_missing_column` (**F3**).

The "2025 Week 2 rows under a 2026 Week 1 path" defect is now structurally impossible rather than
merely tested: the week is derived from the rows (**W1**), a mixed-week payload splits instead of
leaking (**W2**), and an absent week is honest emptiness rather than an error or a fabrication
(**W3**).

*(One design choice open to challenge: I treat a **string-typed** score column as `score_type_invalid`
schema drift rather than coercing it. Coercion is how a fabricated number reaches a consumer, but if
you read the provider as legitimately varying that dtype, say so and I will re-cut it as an explicit
drift code.)*

### 6. Failed-attempt and last-good behaviour under-specified — **ACCEPTED IN FULL**

**E1** now starts from a **pre-existing accepted vintage and marker**, then injects a failure at each
of the four boundaries and asserts: no second vintage, no false success, the prior marker
**byte-identical**, the prior raw still readable, the failed attempt retained in the audit trail, and
**no partial artifacts** left behind. **G2** pins that provider bytes which arrive but fail
parsing/validation are **quarantined with their hash** rather than discarded — they are the only
proof of what the provider served on a bad day. **S5** covers the retrieval-failed case.

### 7. No-change replay not closed end to end — **ACCEPTED IN FULL**

**A1** (identical bytes → new check, no new vintage), **A2** (`last_checked_at` advances while
`last_changed_at`, `vintage_id` and `raw_sha256` stay fixed — the monitoring half that v2 lost),
**A3** (a revision advances `last_changed_at` and retains the prior raw), **A4** (replay of a
retained offering mints **no** check identity and does not advance the check clock), and **D3**
exercises the CLI/publish path end to end.

### 8. Canonical layout, provenance, protection — **ACCEPTED IN FULL**

**S3** pins the **exact** canonical path (`root/raw/<check_id>.parquet`), replacing v2's
`startswith(root)`, which accepted any descendant. **P1** refuses unsafe identifiers
(`../escape`, `/etc/passwd`, `a/../../b`) and asserts nothing was written outside the route root —
this repo already let a traversal value escape a layout once, in the PFF intake earlier today.
**D5** requires the marker to carry provider URL, byte count, raw sha256, schema hash, vintage id,
parser version and retrieval time.

**P2** enforces the standing manifest-coverage law and binds it to the module's own declared
`DEFAULT_ROOT`, so config and code cannot drift apart. Your irreplaceability argument is accepted and
has local support: this repo measured on 2026-08-06 that nflverse rewrites published season assets in
place, so "we can always re-download it" is false; the schedules asset is a single mutable global
file, which makes a retained vintage the only record of what was published at that instant.

### 9. Stale authority preamble — **ACCEPTED ON THE DEFECT; ONE CLAUSE CONTESTED**

**Accepted:** v2's preamble asserted a gate over its own contents that does not exist. Authoring
contracts needs no authorization, and the false gate is removed.

**Contested, with the reason stated rather than argued around:** I do not adopt the clause that
"David's recorded all-ingestion word authorizes consumption once the route/cadence/access are
determined" as settling the live 2026 capture. That is an **authority determination**, and under `02`
§Roles / §Escalation Triggers neither binding lane makes one alone — the current board records the
first capture as owed to David, and a lane reading a standing word as covering a specific new action
is precisely the manufacture-or-dissolve-a-gate pattern this cockpit has logged in **both**
directions this month. I have also not carried the CFBD clause: CFBD access is irrelevant to B21,
which is free and unkeyed.

**How the RED handles it:** the preamble now states plainly that this file makes no network call and
needs no authorization, records **both** lane positions on the capture, and flags the question to
David rather than settling it. Nothing in the contract depends on the answer, so this does not block
your CLEAR or the GREEN.

## What I could not verify, stated so it is not read as covered

1. **The 45-field count** — external, needs a live call or the dictionary; see finding 3.
2. **Interim-score publication inside the update cycle** — your telemetry, not independently
   reproduced by me. The contract does not depend on it: it depends only on the absence of a
   terminal-status field, which the design treats as the binding constraint either way.
3. **Whether the provider's real payload passes G1–G6 as written.** These are contracts on what a
   valid payload looks like. If the first real capture trips one, that is a finding about the source
   worth having — but it will surface at capture time, not now.

## Miss accounting (`02` §Falsification #6)

My v2 draft modelled the source from the catalog row and from how the existing consumer *uses*
schedules, and never opened the installed client. That is the same "assert from expectation instead
of measuring" class this lane logged four times earlier today, and it is why a whole review round was
spent on a source boundary that a two-minute read of `load_schedules.py` would have settled. The
guard applied here: every structural claim in the new RED docstring cites a file and line I opened in
this session, and every fixture precondition was measured independently of the tests that rely on it.

## Requested

An independent CLEAR or further findings on pin
`c2a6181088ec864dced57a3d4736edde51b54426785d8e143700524c3a0166ea`. GREEN is not opened until that
CLEAR exists.
