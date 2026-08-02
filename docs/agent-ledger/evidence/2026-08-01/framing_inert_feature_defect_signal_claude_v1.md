# Framing — `enriched_features_equal_baseline` is a defect signal, not a null result

**Lane:** Claude Code (framing author) · **Status:** v1, awaiting Codex adversarial challenge
**David's word:** "all three green light approved" (2026-08-01), item 3.
**Layer served: 3 (models) — presenting.** This is a reporting-honesty defect in the bakeoff
harness, not an ingest defect.

**Layers 1-2 dependency check (required for layers 3-6).**
- *Check performed:* read `app/data/backtest/phase20/phase20_bakeoff_20260524T183807Z_db568d44.json`
  `positions.QB`, and the ingest defect it depended on (this session's CFBD repair, commit `4d8127d`).
- *Result:* the QB arm's four features were `dropped_features` at `coverage_pct` 39.5/39.5/39.5/0.0;
  both models `skipped: true`, `reason: enriched_features_equal_baseline`. The **cause** was a
  layers-1/2 ingest defect (now repaired).
- *Conclusion:* **the ingest cause is fixed, and a distinct layer-3 defect remains.** The harness
  reported a non-test inside a "null result" and nothing surfaced that. Repairing ingestion does not
  repair the reporting. This work is genuinely at layer 3.

---

## 1. The concrete situation this serves

David reads a model bakeoff and decides whether a feature family is worth pursuing. On 2026-05-24 a
bakeoff was committed as **"null result"**. It reported real numbers for WR (−1.4%, −5.7%) and RB
(+5.6%, −7.4%). For QB it reported nothing, because the QB arm **never ran** — every enriched feature
had been dropped, so the enriched matrix equalled the baseline matrix and both models were skipped.

The record read as *"we tested QB college passing and it did not help."* What actually happened was
*"we never tested it, because the ingest was broken."* Ten weeks later that distinction is what this
session had to rediscover from an artifact.

**The moment served:** David asks "have we tried X?" and the answer he gets is trustworthy.

## 2. Mislead / nudge risks

- **The dangerous direction is a false negative that closes a line of inquiry.** A feature family
  wrongly recorded as tested-and-useless never gets retried. That is a silent, permanent narrowing of
  the search space — the most expensive kind of error in a system whose edge comes from finding
  things the market has not.
- **Verdict-by-the-back-door:** a "defect" label must not become an implicit claim that the feature
  *would* have worked. It says the test did not happen. Nothing more.
- **Alarm fatigue:** if a legitimately-equal enriched set (e.g. enrichment genuinely adds columns
  already present in baseline) trips the signal, the signal gets ignored and is worse than nothing.

## 3. Candidate falsification seeds for the RED

1. All enriched features dropped → enriched matrix == baseline → **must surface as a defect**, not a
   null result.
2. **Partial** drop (some enriched features survive) → runs, but the report must name what was dropped
   and at what coverage.
3. A declared family at **0.0 coverage** (`qb_sack_rate_final`) → distinct, louder signal than "low".
4. Enriched set **legitimately identical** to baseline by construction → must NOT read as a defect
   (this is the false-positive boundary; the RED needs it or the signal is unusable).
5. Baseline itself degenerate/empty → separate refusal, not this signal.
6. `n_eligible_rows` below a power floor → the arm is unpowered, which is again not a null result.
7. A skipped arm must never be aggregated into a headline that implies a completed test.
8. Historical artifacts: the signal must be derivable from an **already-written** artifact, so past
   bakeoffs can be re-read rather than re-run.

## 4. Overclaim check against the No-Verdict Line

This surface reports **execution status of a test**, not a football claim. It says "this arm did not
run and here is why". It must not say a feature is promising, and must not rank families.
`decision_supported=False` is unaffected — no player-facing value moves. Under `00`
§Descriptive Tools Issue No Verdicts this is a status field, and the banned-language discipline
applies to any prose it emits.

**Explicitly out of scope, each needing a separate David word:** re-running the Phase-20 bakeoff;
re-testing QB college passing features against the repaired ingest; any feature promotion; any
change to a gate threshold.

## 5. Open question for the challenge round

Where does the signal live — in the bakeoff **runner** (fail loud at run time), in the **artifact
schema** (a `status` field future readers cannot miss), or in a **reader/linter** over existing
artifacts? My own lean is the artifact schema plus a reader, because it makes the ten-week-old
artifact self-describing rather than requiring a re-run. I state it as a lean, not a decision;
`02` §No-anchor framing applies and Codex owns the technical scope call.
