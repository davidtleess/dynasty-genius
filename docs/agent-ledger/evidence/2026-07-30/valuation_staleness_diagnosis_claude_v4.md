# Diagnosis v4 — corrections to v3

**Claude Code. Written 2026-07-30 12:48:02 EDT** *(machine clock, pasted — not typed).*
**v1 (7) · v2 (6) · v3 (2). All 15 findings accepted, none challenged.**
Priors re-hashed at the timestamp above and byte-unmodified:
v1 `6aa157328928fce7…`,
v2 `d148b24b160772b8…`,
v3 `5f630996172d05ca…`.

**v3 stands except where corrected below. Diagnosis only; no producer, config or contract touched.**

---

## §0 — The two v3 findings

| # | Finding | Disposition |
| --: | :-- | :-- |
| 1 | v3 §4 still said "the population moved while the values did not" — but v3's own §1 and §3 establish population and coverage movement | **ACCEPTED** — §1 below |
| 2 | v3's header said "written 12:1x ET" while declaring the anchoring rule | **ACCEPTED** — this header carries a machine-produced clock |

## §1 — The corrected causal sentence

**What is established, and nothing wider:**

- **The overlapping scored intersection showed `mean_abs_value_delta = 0.0` at that publish.** That is
  a statement about the players present and scored in *both* artifacts, at *one* comparison.
- **Population and coverage DID move**, and the same marker says so: `coverage_count_deltas`
  **ENGINE_B −2, INACTIVE +2, PRE_MODEL +2**, alongside seed 12,201 rows vs runtime 12,203.

**So "the values did not move" is not an established sentence and is withdrawn.** The established
sentence is narrower: **the numeric values of players scored in both artifacts were identical at that
comparison, while the scored population itself changed.** Those are compatible facts about different
sets, and v3 wrote the first as though it described the artifact.

**No input was causally isolated.** The builder reads the Sleeper snapshot, prospect cards and the FF
crosswalk in addition to features; that the daily-moving league inputs explain the population
movement is **plausible and undemonstrated**, and is not asserted.

## §2 — Everything else in v3 stands

The layer-3 origin, the narrowed layer-1 claim (transactions omitted; the value loop blind to
identities entering and leaving), the withdrawn interval claim, `identity_inputs=None`, the
aggregate-vs-value-loop distinction, and the narrowed mtime wording are unchanged and were cleared.
