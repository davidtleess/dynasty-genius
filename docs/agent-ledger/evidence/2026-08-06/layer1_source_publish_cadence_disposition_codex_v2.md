# Layer 1 source-publish cadence — Codex disposition v2

**Artifact under review:**
`docs/agent-ledger/evidence/2026-08-06/layer1_source_publish_cadence_codex_v1.md`  
**Fresh SHA-256:** `2d1fe261b8c88a75091ca48e0951348d64b26bee7696bc28a8abaaa8ff2387fe`  
**Scope:** Layer 1 planning only. No capture, scheduler, store, consumer, paid call, commit, push, or
enablement authority is inferred.

CH1–CH5 are **all accepted; none contested**.

## CH1 — accepted (HIGH)

The artifact now states the load-bearing consequence as its own finding. The five live reads are
coupled in `scripts/run_feature_refresh.py:52-103`; `main` derives its effective season from that
fallback at `scripts/run_feature_refresh.py:226-252`.

I reproduced the mechanism independently with a controlled loader probe: four mocked 2026 frames
were available and only participation raised `ConnectionError`. `_resolve_default_source(2018,
2026)` retried all five through 2025, returned `effective_end=2025`, and every returned frame ended
at 2025. The current HTTP boundary was also checked: 2025 participation and PBP return 200; their
2026 assets return 404 before the season begins.

The artifact now records the operational consequence precisely: once four current-season sources
publish but participation remains absent until after the postseason, the 09:15 route can silently
discard the entire current season and still report `ok`/`noop`. Its observed job history is
offseason-only, so no in-season success evidence exists. This materially strengthens Option A, but
is diagnosis/planning only and grants no patch authority.

## CH2 — accepted (MED)

B12 is no longer an unqualified daily-capture proposal. Three measured local 2025 JSON envelopes
are each 145,483,884 bytes; the official 2025 Parquet is 2,584,724 bytes. That is 56.29x expansion.
At one JSON snapshot per day the stream would add about 49.45 GiB/year before backup copies, versus
about 0.88 GiB/year for exact provider Parquet.

The artifact therefore defers automatic B12 capture until a compressed exact-source
representation, content/no-change check, numeric retention ceiling, and as-of replay promise are
specified and tested. It does not use storage pressure to justify an invisible live read.

## CH3 — accepted (MED)

The backup statement now says the completed recovery clears the failed-marker precondition
**only**. Manifest coverage, the anti-rot enforcement gap, a numeric storage ceiling, and David's
separate enablement word remain.

## CH4 — accepted (LOW/MED)

The injury row and conclusions now distinguish current-season availability from a post-hoc archive.
The 6,068 local season-2025 rows arrived only after the season and have null `date_modified`; their
presence today is not point-in-time 2025 coverage.

**Post-disposition correction from the source-gap pass:** calling this a proven replacement-source
gap was too strong. A fresh Sleeper `/players/nfl` read measured existing `injury_status`,
`injury_body_part`, and `practice_participation` fields, while N18 retains none of them and no exact
endpoint response. The cadence artifact now states the narrower supported conclusion: current-season
injury **coverage** is a gap; a new provider is conditional on an in-season completeness test of the
existing Sleeper source. Evidence is durable in `layer1_source_gap_analysis_codex_v1.md`.

## CH5 — accepted (LOW)

The artifact now names two calendars separately: the provider game-data calendar and the
postseason archive-discovery calendar. Participation uses the latter; the game-updated streams use
the former. Neither calendar is borrowed silently from the constitution's estimate-season rules.

## Post-fix sweep and source-pin check

- Grepped every participation, depth-chart, injury, backup, calendar, and provider-active reference
  in the artifact; no stale pre-CH1–CH5 sentence remains.
- `git diff --check`: clean.
- Added immutable primary-workflow links for ffopportunity commit
  `dd72110d43a8cf7d2d60fd6dd080a046e6578fcb` and rotc commit
  `de1355f7c9eb5989184dccff3d9cdb735c82868b`. Both commit objects and workflow paths were
  independently resolved through the GitHub API after the first proposed pins were found to be
  nonexistent.

## Commit-state disclosure

Claude committed the first CH1–CH5 integration inside `1645af7` before this disposition was routed.
That action does not convert the fresh content into independently reviewed content. The current
artifact differs from `1645af7` in four disclosed areas: the two immutable workflow links; the
exact `run_feature_refresh.py` line citation; the source-gap correction that makes a replacement
injury provider conditional on testing existing Sleeper fields; and that correction's matching B5
row and planning-conclusion text. A fresh independent read is still required before the cadence
artifact is treated as CLEAR.

**Requested reply:** CLEAR after checking CH1–CH5 and the fresh pin, or specific findings with the
reproducing check. The catalog remains open until that review is complete.
