# Diagnosis v3 — the daily valuation republish: what is established, at the strength it is established

**Claude Code, 2026-07-30, written 12:1x ET.** TW30-LAYERS-J.
**v1 NOT CLEAR (7) · v2 NOT CLEAR (6). All 13 findings accepted, none challenged.**
Priors on disk, hashes **re-verified 2026-07-30 12:10 ET**: v1 `6aa15732…c4e74`, v2 `d148b24b…dcfd8`.
**Diagnosis only. No producer, config, scheduler or contract touched. Nothing opened.**

**Anchoring is a requirement here, not a recurring correction.** Three artifacts today asserted
observation windows that had not happened. Every reading below carries the clock time it was taken.
**No window is claimed.**

---

## §1 — Established, and nothing beyond it

| Claim | Evidence | Read at |
| :-- | :-- | :-- |
| The feature layer no-ops daily: 32 `noop`, 1 `ok` in the whole log | `app/data/logs/feature_refresh.out.log` | 11:22 ET |
| Engine B feature runtime last changed 2026-07-10 09:21 | file mtime + report `generated_at` | 11:22 ET |
| The daily rebuild resolves that frozen runtime | `build_universe_pvo_batch.py:243-245` | 11:24 ET |
| `source_as_of` is stamped at write time regardless of content | `run_pvo_refresh.py:371-382` | 11:28 ET |
| **Overlapping scored players' values were identical to the 06-26 seed at that publish** | `mean_abs_value_delta 0.0` over that intersection | 11:20 ET |
| Seed and runtime are **not** identical: 12,201 vs 12,203 rows | direct read of both artifacts | 11:52 ET |

**Withdrawn in v2 and still withdrawn:** byte-for-byte identity; the 33.8-day interval claim.

## §2 — The layer-1 claim, narrowed in the text

**v2's headline — "nothing ingests the inputs that would distinguish correctly-still from
wrongly-frozen" — is REFUTED, and it does not survive in softened form.**

Refuting evidence, reproduced: the live feature refresh loads and hashes nflreadpy **rosters**, and
`depth_chart_position` is consumed as a real feature (`feature_assembly.py:149,154`;
`engine_b_contract.py:129,264`). The daily Sleeper universe snapshot persists **team**, **status**
and roster **`on_ir`** (12,201 `on_ir` occurrences in the current snapshot, read 12:05 ET).

**So depth charts, team changes and injury/IR status are ingested to some degree. The three named
categories were wrong, and "nothing" was wrong.**

**What is established, and it is narrow:**

1. **Transactions are never ingested** — no adapter function exists for the endpoint. A demonstrated
   omission.
2. **The value-drift comparison is intersection-only** — `_player_values` admits a row only with a
   non-null id **and** a non-null score, and the diff loop skips candidate ids absent from the seed
   (`run_pvo_refresh.py:81-90,136-150`). **It is blind to identities entering and leaving the scored
   population.**

**That is the whole surviving claim. It is not a foundation-wide gap and must not be relayed as one.**

## §3 — What the staleness metric does and does not see (corrected)

v2 said the metric is "structurally blind to population movement." **That is false as written, and I
had the disproof in my own first reading of the marker.**

`_compute_seed_staleness` **does** emit `coverage_count_deltas`, and today's marker carries
`ENGINE_B −2`, `INACTIVE +2`, `PRE_MODEL +2` — I quoted those numbers in my own 08:05 read and then
wrote that the metric could not see population change.

**Corrected and precise:** the metric reports **aggregate coverage movement**; its **value loop** is
blind to **which identities gained or lost a score**. A zero on `mean_abs_value_delta` says "the
players present and scored in both did not change value" — it does not say the population held, and
the aggregate deltas beside it say the population did not hold.

## §4 — Causality: stated at the strength it is established

v2 still said "the population moved while the values did not" and called the extra inputs "precisely
why." **Both overclaim.** What is established: **the overlapping scored intersection showed 0.0 at
that publish**, and the builder reads the current Sleeper snapshot, prospect cards and the FF
crosswalk in addition to features (`build_universe_pvo_batch.py:29-34,239-248,359-368`). **No input
was causally isolated.** The daily-advancing league/identity inputs are a *plausible* source of the
population movement; that has not been demonstrated and is not asserted here.

## §5 — The source hash (corrected again)

v2 corrected v1's "five frames only" and then overreached in the other direction by listing identity
inputs as hashed. **The signature accepts `identity_inputs`, but production passes `None`**
(`run_feature_refresh.py:159`). Hashed in production: the loader frames, `seasons_window`,
`package_version`, `builder_config`, `te_rubric_artifacts`.

## §6 — The disclosure path (narrowed)

- `seed_staleness` **is** read — `promote_pvo_seed.py:78-113,135-158` surfaces it in dry-run, abort
  and promoted reports. It is absent from the **daily** surfaces.
- `what_changed/report.py:178-185` drops it unless `promotion_review_threshold_crossed`; the comment
  reads *"Silent-unless-threshold-crossed."* Zero drift is the state that suppresses it.
- **`pvo_refresh` registers neither `timestamp_field` nor `status_field`, so the evaluator falls back
  to mtime.** v2 said this makes it "read fresh permanently." **Too strong** — the evaluator can still
  report missing, corrupt, future-dated, overdue or stale. **The narrow truth: each daily rewrite
  renews the mtime, so within that window the artifact reads fresh without its content having
  advanced.**

## §7 — Not established

1. Why the 07-10 run produced its single `ok`.
2. What happened on the intervening days — needs the model-forward PIT series.
3. Whether the population movement is correct behaviour.
4. Whether any ingested-but-unhashed signal *should* trigger a rebuild.
5. Anything about the front end.

## §8 — Stopping point, unchanged

Every remaining step is a change. **None authorised.**
