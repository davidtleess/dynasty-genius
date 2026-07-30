# Provenance addendum — the Tower measurement, and what does and does not rest on it

**Claude Code, 2026-07-30, written 11:56 ET.** Attaches to **diagnosis v2**
(`d148b24b…dcfd8`) and **stream declarations v4** (`4e238259…c9d858`). **Neither frozen artifact is
modified by this addendum.** Findings/provenance only; nothing opened.

## Why this exists

Tower disclosed, unprompted and to David directly, that **its own measurement — the one this lane was
instructed to treat as corroboration rather than as its own finding — was produced by a comparison
blind to a value appearing or disappearing.** Re-run properly it returns the same answer on that
table, which makes it **right by luck, not by method.** Tower's instruction: if any part of the live
artifacts rests on it, mark that part **unestablished rather than Tower-verified, in the artifact.**

**That instruction was conditional, so I ran the dependency check rather than assuming either way.**

## The check, and its result

Two lines in the live artifacts attribute anything to Tower:

| Location | Attributed claim | Does it rest on the Tower measurement? |
| :-- | :-- | :-- |
| `valuation_staleness_diagnosis_claude_v2.md:113` | the artifact discloses its own staleness | **No.** I read `seed_staleness` in `universe_pvo_runtime.ready.json` myself, twice, anchored (08:05 and ~11:20 ET): `seed_age_days 33.8`, `seed_as_of 2026-06-26T18:16:37Z`. |
| `stream_declarations_claude_v4.md:187` | the file-newer-than-its-data condition | **No.** Independently instanced below. |

**Conclusion: no claim in either artifact rests on the Tower measurement**, so nothing in them is
downgraded to unestablished. What changes is the **attribution**, which is recorded here rather than
left to read as a verified basis.

## The independent instance, re-verified for this addendum

**Read at 11:56 ET, 2026-07-30** — `app/data/valuation/league_opportunity_latest.json`:

- file mtime **`2026-07-23T03:49:11Z`**
- embedded `captured_at` **`2026-07-15T00:40:23Z`**

**The file is roughly eight days newer than the data inside it.** That is the condition, in a file I
read myself, and **Gemini's 2026-07-29 telemetry is the earliest record of it in the repo** (logged
there as "Stale (Mtime 2026-07-23, content 2026-07-15)").

**A precision the artifacts should not blur, and which I am recording rather than quietly fixing:**
`pvo_refresh` demonstrates a *different* property — that freshness is judged by **mtime basis** when
no timestamp field is registered. Both of my anchored readings of it showed mtime and `capture_date`
*agreeing* (07-29/07-29, then 07-30/07-30). **`pvo_refresh` is not an instance of file-newer-than-data;
`league_opportunity_latest.json` is.** The two facts are adjacent and were sitting under one heading.

## Corrected provenance, for any later reader

- **Tower raised the condition** and directed it into this thread. That stands, and it is why the
  work happened.
- **The Tower measurement's method is disclosed as blind to value appearance/disappearance** and is
  **not** a verified basis for anything. It is not cited as evidence in either artifact.
- **The evidence carrying the condition is:** my own anchored read above, and Gemini's 2026-07-29
  telemetry.
- **The same blindness class is already recorded in diagnosis v2 §2** as a defect in the shipped
  `_compute_seed_staleness` (`run_pvo_refresh.py:81-90,136-150`), which admits only rows with a
  non-null id **and** score and skips candidate ids absent from the seed. **A comparison that can only see the
  intersection cannot see which identities entered or left it** — the same failure mode, in the
  product and in a hand measurement, found on the same day. **Corrected 2026-07-30 12:1x ET:** an
  earlier wording here said "cannot see the population change," which is wrong —
  `_compute_seed_staleness` DOES emit aggregate `coverage_count_deltas`. The blindness is in the
  **value loop**, to identities gaining or losing a score, not in the metric as a whole.
