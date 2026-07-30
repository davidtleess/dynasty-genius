# Diagnosis v2 — the daily valuation republish: what is actually established

**Claude Code, 2026-07-30. DIAGNOSIS ONLY.** TW30-LAYERS-J. **v1 NOT CLEAR — 7 findings, all
accepted, none challenged.** v1 (`6aa15732…c4e74`) is byte-unmodified on disk as the frozen prior.
**No producer, config, or contract touched. No remediation thread opened.**

**Every observation below was read at a stated clock time, singly.** v1 claimed a completed window of
"11:20–11:35 ET" in a file written at **11:23:27** — a window that had not finished when the claim
was made. That is false precision in the document that declares the anchoring rule.

---

## §0 — The correction that changes the conclusion

**v1's headline layer attribution was wrong, and my own trace contradicted it.**

v1 said the defect *presents at layer 3 and originates at layers 1–2*, while §2 of the same document
concluded that **ingestion and curation are behaving correctly**. Both cannot be true.

**Corrected:** the freshness-presentation defect **originates at layer 3 and in reader/health logic** —
the writer that stamps `source_as_of` at write time (`run_pvo_refresh.py:371-382`), the registry that
judges the artifact by mtime, and the suppression rule (`what_changed/report.py:178-185`). **Correct
upstream stillness is a dependency of the defect, not its origin.**

**I asserted a root layer without the check the rule demands — the exact error `05` §4 records — and
I did it in a document written under an instruction to focus on layers 1–2, having explicitly asked
the reviewer to check me for that error.** Recorded rather than quietly fixed.

**The genuine layers-1–2 finding, which survives and is sharper than v1's:** *nothing in the estate
ingests the inputs that would distinguish "correctly still" from "wrongly frozen."* Transactions are
never ingested; depth charts, team changes and injuries are not streams at all. **A pipeline cannot
report that it should have moved when the evidence that it should have moved was never collected.**
That is a layer-1 gap, and it is the part of this diagnosis that belongs in David's frame.

---

## §1 — What is established, stated at the strength the evidence supports

| Claim | Status |
| :-- | :-- |
| The feature layer no-ops daily; the log holds 32 `noop` and 1 `ok` | **Established** — `feature_refresh.out.log`, read 2026-07-30 11:2x ET |
| Engine B feature runtime last changed 2026-07-10 09:21 | **Established** |
| The daily rebuild resolves that frozen runtime | **Established** — `build_universe_pvo_batch.py:243-245` |
| `source_as_of` is stamped at write time regardless of content | **Established** — `run_pvo_refresh.py:371-382` |
| **Overlapping scored players' values are unchanged vs the 06-26 seed** | **Established** — `mean_abs_value_delta 0.0` over that population |
| ~~The runtime is byte-for-byte the 06-26 baseline~~ | **RETRACTED — false** (§2) |
| ~~Every divergence change for 33 days came from the market alone~~ | **RETRACTED — not established by this evidence** (§3) |

## §2 — RETRACTED: "byte-for-byte identical". The population moved; the metric cannot see it

**Reproduced myself:** the seed carries **12,201** rows and the runtime **12,203**. The artifacts are
**not identical**, and the PVO hashes differ.

**Why the 0.0 could not have proved what I claimed it proved** — `run_pvo_refresh.py:81-90,136-150`:

- `_player_values()` admits a row **only if both the sleeper id and the score are non-null**.
- The diff loop **skips any candidate id absent from the seed** (`if pid not in seed_vals: continue`).

So `mean_abs_value_delta = 0.0` describes **the overlapping, scored intersection only.** It is
structurally blind to rows added or removed, and to players **gaining or losing a score** — which the
reviewer measured (scored population 469 → 468; Brady Russell and Reggie Gilliam gained scores;
Andrew Beck, Adam Prentice and Connor Heyward lost them). I have reproduced the row-count movement
directly and take the per-player figures as the reviewer's, attributed.

**This makes the finding sharper, not weaker: the metric that exists to report staleness is blind to
the one dimension that actually moved.** A zero on that metric says "the players we can compare did
not change," and is silent about the population changing underneath it.

## §3 — RETRACTED: the interval claim. Point-to-point ≠ time series

`_compute_seed_staleness` performs **one per-publish diff against the committed seed**
(`:102-116,136-185`). `seed_age_days = 33.8` is the age of the *baseline*, not a measurement across
33.8 days. **A single current-vs-seed comparison cannot establish what happened on the intervening
days**, so v1's "every divergence change for 33 days came from the market side alone" is withdrawn.

**What can carry that weight is different evidence I did not use:** the model-forward capture store
(the daily PIT series) corroborates unchanged overlapping numeric scores after 06-26, and the
divergence history begins **07-09 with 19 dates**. Establishing the interval claim properly means
reading that series — **not opened here.**

## §4 — "Same inputs" was incomplete

v1 named features and the model artifact as though exhaustive. The builder also reads the **current
Sleeper snapshot, prospect cards, and the FF crosswalk** (`build_universe_pvo_batch.py:29-34,239-248,359-368`).
**That is precisely why the population moved while the values did not** — the league/identity inputs
advance daily while the feature inputs are frozen. v1 contained the evidence of this in its own
population-delta row and did not follow it.

## §5 — The source hash is wider than I said

v1: *"it spans five nflreadpy frames only."* **False.** `compute_source_hash`
(`feature_refresh_runner.py:33-58`) hashes the season window, package version, builder config, TE
rubric/eligibility artifacts, identity inputs **and** the loader frames. **The no-op therefore means
more than "no new games" — it means none of that wider input set changed.** The gap named in §0
stands regardless: what is *not* in the hash is what is *not ingested at all*.

## §6 — The disclosure: two mechanisms, not three, and it is read in one place

**Corrected: `seed_staleness` is not unread.** `promote_pvo_seed.py:78-113,135-158` resolves and
surfaces it in its dry-run, abort and promoted reports. It is **absent from the daily surfaces**, not
from the codebase.

Two mechanisms keep it off the daily path (v1 listed three; the third was the *condition* driving the
second, not an independent mechanism):

1. **The health registry does not look.** `pvo_refresh` is registered with `timestamp_field: null` and
   `status_field: null`, so the evaluator judges it by **file mtime** and it reads fresh permanently.
2. **The one daily consumer suppresses it.** `what_changed/report.py:178-185` sets the block to
   `None` unless `promotion_review_threshold_crossed` — and the code comment is explicit:
   *"Silent-unless-threshold-crossed."* **Zero drift is exactly the state that suppresses it**, so a
   surface built to report movement cannot report stillness.

**Tower established the file-discloses-its-own-staleness fact by opening the artifact. This section is
mechanism and correction, not a discovery of mine.**

## §7 — What this diagnosis does NOT establish

1. **Why the 07-10 run produced its single `ok`.**
2. **What happened on the intervening days** — needs the model-forward PIT series (§3).
3. **Whether the population movement matters** — 5 players changing scored status is a fact; whether
   it is correct behaviour is unexamined.
4. **Anything about the front end.** Not read, not opened.
5. **Whether the layer-3 origin means the defect should be worked** — priority is not authorization,
   and the corrected attribution is a finding, not a licence.

## §8 — The stopping point, unchanged

Every remaining step is a change: registering the artifact with its embedded timestamp and status;
teaching the suppression rule to distinguish stable from frozen; deciding whether an unmoved
republish should stamp a new date; ingesting the streams that would make `unchanged_unexpected`
detectable at all. **None authorised. The diagnosis stops here.**
