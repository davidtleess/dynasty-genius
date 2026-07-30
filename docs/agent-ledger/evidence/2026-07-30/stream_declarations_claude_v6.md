# Stream Declarations v6 — corrections to v5

**Claude Code. Written 2026-07-30 12:48:02 EDT** *(machine clock, pasted — not typed).*
**v1 (7) · v2 (5) · v3 (6) · v4 (6) · v5 (4). All 28 findings accepted, none challenged.**
Priors re-hashed at the timestamp above and byte-unmodified: v4
`4e238259db29925e…`, v5 `c149098a6a160684…`
(v1–v3 hashes recorded in v5's header, unchanged).

**v4 remains the base and v5 its corrections; both stand except where corrected below.**

---

## §0 — The four v5 findings

| # | Finding | Disposition |
| --: | :-- | :-- |
| 1 | Cited ONE plist as proof about FOUR different jobs | **ACCEPTED** — §1 |
| 2 | "no other agent reads / no machine consults" — unsupported, and false as to agents | **ACCEPTED** — §2 |
| 3 | Row 5 described as recordless, when it is worse than that | **ACCEPTED** — §3 |
| 4 | "written 12:1x ET" | **ACCEPTED** — machine clock above |

## §1 — The four plists, each read individually

v5 proved a claim about four jobs from `com.davidleess.dynasty-model-pvo-refresh.plist` alone — a fifth job,
and not one of the four. **Each of the four has now been read separately, at the timestamp above:**

| Pipeline | plist | stdout / stderr |
| :-- | :-- | :-- |
| FC capture | `com.davidleess.dynasty-fc-snapshot.plist` | `fc_forward_capture.out.log` · `fc_forward_capture.err.log` |
| feature refresh | `com.davidleess.dynasty-feature-refresh.plist` | `feature_refresh.out.log` · `feature_refresh.err.log` |
| league capture | `com.davidleess.dynasty-league-capture.plist` | `league_capture.out.log` · `league_capture.err.log` |
| realized outcome | `com.davidleess.dynasty-realized-outcome-scoring.plist` | `realized_outcome_scoring.out.log` · `realized_outcome_scoring.err.log` |

**All four do capture stdout and stderr.** The conclusion v5 drew is unchanged; **the evidence it drew
it from was one file, and that is the defect.**

## §2 — What "no durable record" is narrowed to

v5 said a traceback in a log is "a record no machine consults" and that no other agent reads it.
**Both overreach.** An agent can read those logs — one did today — and I established nothing about
every consumer.

**The narrow, established claim:** for rows 1–4, a failure leaves **no structured status, report or
marker consumed by the registered health surface** (`app/config/report_freshness.json` and the
capture-health route). Whether a human or an agent later reads a traceback is outside what was
measured and is not claimed either way.

## §3 — Row 5 is worse than recordless

v5 filed row 5 alongside "leaves no durable record." **It leaves no failure record AND a positive
false one:** termination between the ok-marker write and the scorecard publish leaves
**`status=ok` asserting a scorecard that does not exist.** An absent record is a gap; **a present
record asserting success for a missing artifact is a false statement a consumer will act on.**
Those belong in different rows, and v5 flattened them.

## §4 — Everything else in v4/v5 stands

The orchestrator removal, the trigger floors without exclusivity, the `OSError` condition, the
authority correction (an uncleared artifact governs nothing), and the prior-hash anchoring are
unchanged and were cleared.
