# 003-RESPONSE — engineering disposition on league-data freshness

**Studio's 60-second read**

| ID | Disposition | One line |
|----|-------------|----------|
| F1 | CONFIRMED — and the better case | No schedule exists to fail; capture is absent, not silently failing. Fix accepted |
| F2 | CONFIRMED | All three derived artifacts come from the same June-23 capture run as the snapshot; chain rides the fix |
| F3 | CONCURRED | Counterparty reads are June photographs today; this is the moment the fix serves |
| F4 | ACCEPTED with shape | One module-level age badge, descriptive only; plus a skew guard you didn't ask for |

## F1 — confirmed, with the mechanism corrected

Your evidence holds under independent verification: seven scheduled daily jobs exist and none
captures the league; every snapshot file in that directory is a hand-run development artifact
(May 21, May 24, Jun 23). Your closing question gets the better answer: **nothing is failing
silently — there is no league capture schedule to fail.** Market data has a robot; league data
waits for a human, exactly as you said.

The fix is accepted: a scheduled league snapshot capture. Three corrections to your read of
the mechanism, all of which make it stronger:

1. **The daily output will not write the files you found.** Those are committed copies; daily
   runs publish to a runtime location with the committed copies retained as fallback — an
   established pattern in this codebase (two other daily producers already work this way).
2. **Runs are retained, not overwritten.** A past roster or posture state cannot be re-fetched
   from anywhere once it's gone, so each capture is an immutable per-run record plus a "latest"
   pointer. Your Bo Nix case becomes answerable historically, not just currently.
3. **Each run publishes as one atomic set.** The snapshot and everything derived from it
   (posture, value matrix, cut report) become readable together or not at all — a consumer can
   never composite a new snapshot with an old matrix. A failed or aborted run leaves the last
   complete set readable and raises a named degraded state instead of a silent gap.

## F2 — confirmed

`team_posture_latest.json`, `team_value_matrix_latest.json`, and `roster_cut_report_latest.json`
were all produced by the same June-23 capture run as the snapshot — their internal timestamps
sit seconds apart in the derivation sequence — and your live League Pulse check (June and
same-day stamps composited on one screen) reproduces. The derivation chain runs on the same
schedule as the capture and inside the same atomic set per F1(3).

## F3 — concurred

No technical dispute, and the product read concurs on the stakes: with the client actively
rebuilding, counterparty scouting is the weekly question, and a surface that requires a manual
Sleeper cross-check to be trusted defeats its purpose. This item is the priority argument for
the F1 fix, and it is accepted as such.

## F4 — accepted, with one shape constraint and one addition

**Shape:** artifact age renders as **one module-level badge per league-derived module** — plain
("updated N days ago" / "stale — N days"), always descriptive, never directive — rather than
repeating on every row and card. Missed runs become visible the morning they happen.

**Addition beyond your ask:** an age-skew guard. When the league snapshot's capture time and
the market data's actual vintage diverge beyond a defined threshold, every surface compositing
both (Trade Lab counterparty inputs, League Pulse) raises a named degraded flag — fresh prices
over stale rosters won't pass silently even between runs. The comparison uses the true source
capture clocks, never report build times, which your own F2 live-check shows can disagree with
the underlying data's age.

## Cadence

Daily matches the rest of the pipeline and the league's daily waivers; the exact morning slot
is an implementation detail. What is contractual: downstream consumers gate on a completed
run's published record — never on clock positions — so a late capture degrades loudly instead
of racing.

## Relationship to 001b N7

The live-ownership read for the availability flag remains right and complementary; this item
fixes the artifact chain behind everything else. Neither waits on the other.

## Costing note

Same engineering constraint as the 001b response: no slice here is done until every direct
consuming renderer has been seen working on real payloads — nominal plus every defined
missing/degraded state, desktop and mobile viewports, mid-scroll where composition matters.

— Engineering
