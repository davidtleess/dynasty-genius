# The dynasty asset number — state as of 2026-09-06

Durable record of two days of work that until this commit existed only in `/tmp`.
Nothing here is wired to anything served. It is preserved so it can be checked.

## What the number is

    V = (served − bar_served) × [ 1.0 + Σ over h=1..5 of dʰ · R(h) ]

* `served` — P(qualifying season) × E[points per game | plays]. Availability enters
  here and nowhere else.
* `bar_served` — the same quantity for the **best genuinely unrostered player** in
  David's league. His ruling 2026-09-05: *"the next who is actually available."*
  Measured ranks QB37 / RB45 / WR71 / TE21, and the line did not move once across
  52 daily snapshots.
* `R(h)` — Bob's unconditional cell-mean ratio (`retention_R_v3.json`, canonical).
  **Survival is inside R.** Multiplying by S(h) double-counts the exit.
* `1.0` — the season about to start, at full weight. David ruled 2026-09-05 that
  this season counts; before that the board valued only 2027 onward.
* `d` — the contend/rebuild lean. Defaults to 1.0, which is the **rebuild extreme**.

## What is verified

* **Proportionality gate** — two players in one cell must have V in exactly the ratio
  of their A. 172 pairs, worst discrepancy 8.9e-16. *Proven able to fail*: corrupting
  24 pairs' cell assignment produces discrepancies up to 2.9.
* **Zero-floor assertion** — no player above the bar may be zeroed and none at or
  below it may carry a positive value. This is the rule `WARNING_zero_floor` states
  in the input file and that an earlier build ignored.
* **No-double-count assertion** — every survival value is perturbed in a copy of each
  cell and V must not move. Fires if anything multiplies R by S again.
* **Universe invariant** — rows out must equal *pre-filter* skill rows in. An earlier
  version compared a filtered list against itself and would have passed if the filter
  had dropped everyone.

## What is NOT verified, and must not be assumed

* An independent reproduction returned **PARTIAL**. Findings not yet fixed:
  61 players receiving BLANK who should be 0.0; Travis Hunter dropped when his
  position changed overnight; four unclamped players appearing on neither board.
* Three earlier checks were **tautologies** — they could not fail and two were
  reported as evidence. Deleted, not replaced in kind.
* **Rate vs season-total margin is chosen, not derived.** Two lanes defended it with
  incompatible arguments. It rests on an unmeasured assumption about what David does
  in the weeks his replacement quarterback does not play.
* **80 rookies cannot be priced at all.** David ruled 2026-09-05 that rookie horizons
  come from college production translated to NFL careers; that is DG-165, unbuilt.

## Reproducing it

The runtime artifact for the vintage below was overwritten by the 14:00 refresh.
`input_snapshot_2026-09-05T1300Z.json` is the durable record of what was consumed,
reconstructed from `model_forward_capture.db` (`artifact_vintage` =
`2026-09-05T13:00:48.017163+00:00`). Ages come from the league runtime snapshots.

## Why this directory exists

Every file here lived in `/tmp` for two days. The session scratchpad is durable for
the session; `/tmp` is durable until something reboots. **Nothing distinguished them
until someone asked**, and it went unnoticed all day precisely because nothing
rebooted — the same shape as every green check thrown out this week, where the
failure path and the success path were indistinguishable until challenged.
