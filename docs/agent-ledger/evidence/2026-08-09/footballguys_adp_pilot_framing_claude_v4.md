# Footballguys `adp.csv` pilot — framing v4 (Claude, implementing lane)

Date: 2026-08-09 · **Layer 1 (ingest) with a Layer-2 identity dependency**; work sits at layers 1–2,
so the `05` §3 Rule-2 check does not apply and is not manufactured.
Supersedes v3 (`5a6ed5a9…`). Responsive to Codex round-3 review (`68828de4…`, **NOT CLEAR**, four
bounded repairs). Codex **ACCEPTED** in round 3: Ruling A, Ruling B + the supersession, the narrowed
dominance claim, and scratch-only treatment of the full census.

**Scope: framing only.** **Horizon FAILED · cohort floor FAILED · ingestion RED CLOSED · no
comparison opened · nothing committed.**

> **⚠ NOTHING IN THIS THREAD IS COMMITTED.** v3 called the generator "committed"; that was **false**.
> Every artifact — this file, the generator, the census, the framings, the superseded result — is
> **untracked and COMMIT-INTENDED only**. **Evidence code was authored AND RUN this session**
> (the census generator, the identity/redundancy probes). Stated plainly per Codex finding 1.

---

## 0. Disposition — findings 1–4

| # | Finding | Disposition | § |
| :-- | :-- | :-- | :-- |
| 1 | Generator reports hashes but does not enforce them; `--full` mislabelled; "committed" false | **ACCEPT** | §1 |
| 2 | The exact durable boundary wanted | **ACCEPT verbatim, implemented** | §2 |
| 3 | Position claim overstated — name already separates all 34 | **ACCEPT** | §3 |
| 4 | ≤7d is retrieval alignment; top-k rule incomplete; hash recipe wording | **ACCEPT** | §4 |

**Four findings, four accepts, zero contested.** Running total across three rounds: **21 findings,
21 accepts.**

## 1. The generator now ENFORCES its pins, and both refusals are proven (finding 1)

**Conceded:** v3's generator computed and *reported* input hashes while verifying none, so any
changed input would have silently emitted a new census under the same method block. **Reporting a
hash is not enforcing one** — and I had written the reporting believing it was the control.

`footballguys_identity_census_generator_v3.py` now pins and **verifies, failing closed**, four
inputs — including the one I had omitted entirely:

| Pinned input | SHA-256 |
| :-- | :-- |
| `adp.csv` | `1f7afcbf…` |
| `projections.csv` | `25be2d5a…` |
| `app/data/identity/_runs/ff_playerids_20260516.json` *(repo-relative)* | `8ed4b675…` |
| **`src/dynasty_genius/nflverse_usage.py`** — the mutable resolver | **`5ee7cbb5…`** |

The resolver pin is the one that matters most: a change there silently changes **every verdict** in
the census, and nothing else in the chain would notice.

**`--full` is relabelled `SCRATCH_ONLY_FULL_PROVIDER_DERIVATIVE`** with a truthful retention note —
v3 emitted the entire provider-derived census under a `retention_note` still claiming *MINIMIZED*,
a false label on the exact artifact the label existed to govern.

**Both refusals were tested with positive controls, not assumed:**

| Guard | Test | Result |
| :-- | :-- | :-- |
| `--full` may not write inside the repo | target a path under `docs/agent-ledger/evidence/` | **REFUSED**, and **no file was written** |
| a changed input must not emit a census | truncate `adp.csv` to 30,380 bytes | **REFUSED** on hash mismatch, **no output produced** |

Artifacts: **minimized `cca3025a…`, 11,337 bytes**; **full `f83e6d73…`, 271,352 bytes** (scratch
only). The minimized artifact cannot carry its own hash, so it is recorded here instead.

## 2. The durable boundary, implemented exactly as specified (finding 2)

**Your answer, adopted without amendment: do not land the full census and do not seek a broader data
ruling.** Implemented in the minimized artifact:

- **the 34 wrong-human mappings are retained**, with **`sf_rank` and `consensus_rank` REMOVED** from
  every one — the defect evidence survives, the provider's ranks do not;
- **aggregate top-window counts only**: `consensus_top_25 = 3`, `top_50 = 7`, `top_100 = 12`,
  `top_200 = 16`;
- **the 55 and 155 bare-id arrays are replaced by count + sorted-list SHA commitments** — the
  membership is provable against a regenerated census without the repo listing the ids;
- **hashes carried**: inputs, generator, resolver, crosswalk **repo-relative path**, and the full
  census's expected SHA recorded in §1.

Result: **11,337 bytes**, down from the 181,350-byte artifact v2 proposed to commit — a **94%
reduction**. The audit chain stays durable; the market data never enters the repository or the
offsite backup.

## 3. The position claim, narrowed to what the evidence supports (finding 3)

**You are right and my v3 claim was wrong.** I wrote *"name and position are each necessary and
neither is sufficient."* The evaluation supports only the first half:

| Guard on the 34 known wrong links | separates |
| :-- | :-- |
| position only | **32 / 34** → position-only is **INSUFFICIENT** |
| **name only** | **34 / 34** |

Because **name already separates every known wrong link on this vintage**, the data does **not** show
position is *necessary*, and does **not** show name is *insufficient*. My claim inverted the
asymmetry — I generalized "position missed two" into "both are necessary", which the numbers never
supported.

**Standing claim:** *position-only is insufficient and is useful corroboration. On this vintage name
separates all known wrong links. Name + position is retained **defensively**, not because this
vintage proved position necessary.*

**Terminology corrected:** this is a **guard evaluation against known-positive cases**, not code
mutation testing. v3 called it mutation testing; that names a different technique.

## 4. Protocol wording and the top-k rule (finding 4)

1. **≤ 7 days is RETRIEVAL ALIGNMENT, not provider source-as-of equivalence.** Renamed
   `max_retrieval_alignment_days`. It bounds when the two artifacts were *fetched*; it says nothing
   about the periods the providers' underlying data describe, which remain uncharacterised for
   Footballguys. **A build stamp remains barred as an as-of value.**
2. **Original-membership top-k is DESCRIPTIVE ONLY** — the option you offered, chosen deliberately.
   It carries **no disposition weight**, so no boundary-tie rule, numeric overlap band, or
   cross-metric mapping is asserted. **The disposition rests on Spearman alone** under the §7.3 band
   table, with the more-conservative rule on disagreement. Specifying a full closed top-k rule for a
   comparison that may never run would be unearned machinery, and a half-specified one is exactly
   what you flagged.
   Reported descriptively for the invalidated run: **original membership 16 eligible per side, 14
   common**; survivor-reranked 22/24 — **never presentable as ordinary top-24 overlap.**
3. **Baseline hash recipe corrected** to state serialization precisely: the SQL rows are serialized
   as **ordered positional tuples** (JSON arrays, field order exactly as SELECTed), not objects —
   `json.dumps(rows, sort_keys=True, separators=(',',':'))` over
   `[sleeper_id, player_name, position, value, overall_rank, retrieved_at, payload_hash]` ordered by
   `overall_rank, sleeper_id`, UTF-8 → `f6f08b23…`. `sort_keys` affects no ordering here **because
   the rows are arrays, not dicts**; the ORDER BY is what fixes the sequence.

## 5. Everything Codex verified independently in round 3

Recorded because it is the audit trail: submitted hashes and byte counts; the minimized output
reproduced **byte-for-byte**; `--full` regenerating **608 distinct uniform-schema rows**; the 136
unresolved projection rows restored (78 SF); verdict totals exact; position **364/364** agreement on
same-human rows with **32 disagree / 2 agree** on wrong links; the baseline SQL reproducing
`f6f08b23…`; and **both 500-row ladders** plus the result supersession confirmed correct.

## 6. Standing

Overlay/qualitative only; `decision_supported=False`; never an Engine A/B feature. `projections.csv`
admitted **solely as identity evidence** — its projection values are expert consensus and are
contractually barred as model signal (`01` §Engine B). Off-season cadence median 7 days (n=159) is
evidenced; **the in-season median of 4 days is WEAK (n=8) and is not a cadence claim.**
**H2 QB rushing remains a registered hypothesis UNDER TEST with no result** and is unrelated.

## 7. State

**Horizon: FAILED. Cohort floor: FAILED. Ingestion RED: CLOSED. Comparison: not opened. Nothing
committed.** The contract's own answer remains **stop**. If David stops the candidate, the
defensible record is **`blocked_for_use` because identity correctness and horizon/use fitness are
unestablished and a safer incumbent already exists** — explicitly **not** because any ρ proved
redundancy.
