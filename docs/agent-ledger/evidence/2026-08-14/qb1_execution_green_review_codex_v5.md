# TW14-QB1-1 GREEN review — round 5 / cap round (Codex, 2026-08-14)

## Verdict

**NOT CLEAR.** The round-4 cardinality, lane/direction, nonnegative-count, and exact-panel-id
defects are corrected, and the repaired current run now contains five cap-bearing GREEN-review
rounds. Two BLOCKERs remain at the exact requested pins. This is the cap round, so these findings
route to the Judge after the structured round closes; no sixth correction round exists.

Reviewed request:
`docs/agent-ledger/evidence/2026-08-14/qb1_green_round5_review_request_claude_v1.md`
SHA-256 `090d5df43ea62d16004d1441ae1b42ea5caaac5f076725d1fc30217bde13bc2c`.

## Findings

### BLOCKER R5-G1 — the claimed complete D5 gate remains presence-only below its top-level shells

`validate_registered_report_blocks` now binds the eight fold ids, 14 contrast ids, lane/direction,
status vocabulary, nonnegative top-level counts, and the three panel ids. It still accepts an `ok`
public-runner publication carrying analytical placeholders that violate the registered output
contract:

- every fold's `metrics_with_CIs` may be the empty mapping, although D5/F6 requires the metric
  readout and CIs;
- every case row may contain only `id`, a generic `scope_note`, and `decision_supported`, with no
  player/fold/state/lane result at all;
- the qualifying-games panel may omit both primary and ≥4-games `pooled_deltas`, and the H5 margin
  panel may omit its entire per-contrast readout;
- `manifest_missing` accepts an arbitrary lane key instead of the registered ridge lanes;
- comparison values are presence-only: `evaluable_folds=-9`, `ci95="not-an-interval"`,
  `p_ni="not-a-probability"`, and `ni_met="not-a-boolean"` all publish as `ok`;
- the F13 pair accepts `binary_dual_threat_gate=True`,
  `continuous_rushing_moderator=None`, and an unrelated `999` boundary.

This is not a theoretical direct-helper bypass. All payloads pass through the public
`run_qb1_study` publication boundary and are atomically published with `run_status="ok"`.
The Claude-authored `_complete_ok_payload` fixture itself pins the empty metric/panel shells as a
valid success, so the regression surface currently certifies the defect.

Reproducer:
`docs/agent-ledger/evidence/2026-08-14/qb1_green_round5_adversarial_probe_codex_v1.py` — tests
`test_public_runner_accepts_metric_free_registered_panels`,
`test_public_runner_accepts_invalid_retained_comparison_values`, and
`test_public_runner_accepts_unknown_manifest_lanes_and_empty_panel_results` all pass at the pinned
boundary.

Smallest remediation: validate the actual registered analytical content, not only key presence:
exact per-fold metric/contrast coverage and value types; exact ridge-lane `manifest_missing` keys;
typed comparison/NI fields with registered numeric domains; case rows containing their produced
fold/state/lane results; exact 14-contrast primary/≥4 slice content; exact four-H5-contrast margin
readout; and computed F13 result structures. Replace the partial `_complete_ok_payload` oracle with
a genuinely complete payload and add one public-runner mutant per rejected class.

### BLOCKER R5-G2 — cap count repaired, but the safety record is malformed and its round-4 churn is false

The run object now has framing/1 plus GREEN-review/1–5, and a read-only hypothetical round-5
BLOCKER/close returns `ADJUDICATION_REQUIRED` with `PHASE_ROUND_CAP`. The counter portion of R4-G2
is therefore fixed.

The repair directly rewrote `run.json` and changed the live round index from 1 to 4, but it did not
move the script-owned open snapshot from `snapshots/green-review-1/open` to
`snapshots/green-review-4/open`. Round 4 subsequently closed into
`snapshots/green-review-4/close`. The installed churn function treats `git diff --no-index` exit 1
as an ordinary diff without distinguishing the stderr-only “Could not access .../open” failure,
so the run now records `filesChanged=0, linesChanged=0` against a nonexistent baseline.

Reproduction:

```text
$ test -e .../snapshots/green-review-4/open
# false
$ test -e .../snapshots/green-review-4/close
# true
$ git diff --no-index --numstat .../green-review-4/open .../green-review-4/close
error: Could not access '.../green-review-4/open'
$ jq '.reviewRounds[] | select(.phase=="green-review" and .index==4) | .churn' run.json
{"filesChanged":0,"linesChanged":0,...}
```

The fourth fresh probe test pins the same contradiction. The `dg-review` hard gate says a malformed
safety hook is BLOCKED. This also matters beyond record cosmetics: churn is an input to the
ratified diminishing-returns detector. The historical count is now usable, but the safety record
that claims to have measured the cap round's predecessor did not measure it.

Smallest remediation is not another GREEN round: route this cap-round finding to the Judge, and
repair the run only under the Judge/David-authorized state-repair path. A valid repair must preserve
the five-round cap while restoring the round-4 open snapshot identity (or recording an explicit,
mechanically recognized unavailable-churn state), use the revision-guarded atomic state writer or
an equally validated CAS/atomic mechanism, and prove the current loop consumes the repaired state.

## Checks that passed

1. Request and boundary pins reproduce exactly:
   `execution.py` `12ed99057185…`; runner `e457d647656f…`; corrections
   `2e16956cfc3c…`; cap script `2c88697e6a9e…`.
2. Unchanged pins reproduce: `status.py` `67651821…`; package `d8876020…`; amended execution RED
   `5d3bc660…`; program RED `7e950792…`; inference ratchet `25c4ffde…`; reinforcement
   `db351f8c…`.
3. The substantive R4 cardinality/identity fixes work: exact eight folds, exact 14 registered
   contrasts in order, registration-bound lane/direction, disjoint status vocabularies, nonnegative
   census checks, H5 retention-field presence, exact case ids, and exact sensitivity-panel ids.
4. Focused contracts: **607/607 passed** = 211 frozen + 344 reinforcement + 52 correction.
   With the four fresh reproducers: **611/611 passed**, 14 numerical warnings.
5. Carried round-2/3/4 defect probes: **13/13 fail**, establishing those prior exploit assertions
   are no longer true.
6. Ruff, strict Python compilation, and `git diff --check` are clean on the reviewed/new evidence
   files.
7. The five F25 frozen pins remain exact; raw QB-validation storage is gitignored and backup
   manifest-covered.
8. No secret assignment was found in the reviewed boundary. The terminal report is absent. No
   study execution, provider call, model/product mutation, commit, push, or publication occurred.

## Boundary

David's held execution trigger does **not** fire. QB rushing production H2 remains **UNDER TEST**
with no result; `decision_supported=False` remains the only permitted study status. The cap-round
BLOCKER disposition must be recorded and routed mechanically to the Judge.
