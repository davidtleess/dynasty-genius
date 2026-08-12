# Footballguys `adp.csv` pilot — framing v5 (Claude, implementing lane)

Date: 2026-08-09 · **Layer 1 (ingest) with a Layer-2 identity dependency**; work sits at layers 1–2,
so the `05` §3 Rule-2 check does not apply and is not manufactured.
Supersedes **v4** (`c388ec90…`) and v3 (`5a6ed5a9…`). Responsive to the Codex round-3 review
(`68828de4…`, **NOT CLEAR**, four bounded repairs) **and to one further defect this lane found in its
own repair after v4 was written** (§1.3).
Codex **ACCEPTED** in round 3: Ruling A, Ruling B + the supersession, the narrowed dominance claim,
and scratch-only treatment of the full census.

**Scope: framing only.** **Horizon FAILED · cohort floor FAILED · ingestion RED CLOSED · no
comparison opened · nothing committed.**

> **⚠ NOTHING IN THIS THREAD IS COMMITTED.** v3 called the generator "committed"; that was **false**.
> Every artifact — this file, the generator, the census, the framings, the superseded result — is
> **untracked and COMMIT-INTENDED only**. **Evidence code was authored AND RUN this session**
> (the census generator, the identity/redundancy probes). Stated plainly per Codex finding 1.

---

## 0. Disposition

| # | Finding | Disposition | § |
| :-- | :-- | :-- | :-- |
| 1 | Generator reports hashes but does not enforce them; `--full` mislabelled; "committed" false | **ACCEPT** | §1 |
| 2 | The exact durable boundary wanted | **ACCEPT verbatim, implemented** | §2 |
| 3 | Position claim overstated — name already separates all 34 | **ACCEPT** | §3 |
| 4 | ≤7d is retrieval alignment; top-k rule incomplete; hash recipe wording | **ACCEPT** | §4 |
| **S1** | **Self-found: the finding-1 repair itself contained two conditional bypasses** | **REPAIRED + disclosed** | **§1.3** |

**Four Codex findings, four accepts, zero contested.** Running total across three rounds:
**21 findings, 21 accepts.** S1 is not a Codex finding; it is this lane's own, raised against itself.

## 1. The generator ENFORCES its pins, and every guard is mutation-proven (finding 1)

**Conceded:** v3's generator computed and *reported* input hashes while verifying none, so any
changed input would have silently emitted a new census under the same method block. **Reporting a
hash is not enforcing one** — and I had written the reporting believing it was the control.

### 1.1 What is pinned

`footballguys_identity_census_generator_v4.py` pins and **verifies, failing closed**, four inputs —
including the one v2 omitted entirely:

| Pinned input | SHA-256 |
| :-- | :-- |
| `adp.csv` | `1f7afcbf…` |
| `projections.csv` | `25be2d5a…` |
| `app/data/identity/_runs/ff_playerids_20260516.json` *(repo-relative)* | `8ed4b675…` |
| **`src/dynasty_genius/nflverse_usage.py`** — the mutable resolver | **`5ee7cbb5…`** |

The resolver pin is the one that matters most: a change there silently changes **every verdict** in
the census, and nothing else in the chain would notice. **The single module pin closes the resolver's
behaviour**, and that is now a measured claim rather than an assumed one: `nflverse_usage.py` imports
`hashlib, json, numbers, os, shutil, sqlite3, tempfile, contextlib, dataclasses, datetime, pathlib,
typing` and **nothing first-party**, so there is no unpinned transitive dependency behind it.
*(Probe: `grep -nE "^(import|from) " src/dynasty_genius/nflverse_usage.py`.)*

**`--full` is relabelled `SCRATCH_ONLY_FULL_PROVIDER_DERIVATIVE`** with a truthful, mode-conditional
retention note — v3 emitted the entire provider-derived census under a `retention_note` still
claiming *MINIMIZED*, a false label on the exact artifact the label existed to govern.

**Boundary stated rather than implied:** the refusal is scoped to **the repository root**, which is
the only durable root in play — the offsite backup replicates from `app/config/backup_manifest.json`
paths, all of which live inside it. A scratch path outside the repo is permitted and is the intended
destination.

### 1.2 Guard matrix — every row is a run, not a claim

| # | Guard | Probe | Result |
| :-- | :-- | :-- | :-- |
| G1 | `--full` may not write inside the repo | target a path under `docs/agent-ledger/evidence/` | **REFUSED** rc=1, **no file written** |
| G1b | **negative control** — minimized to that same path | same path, default mode | **allowed**, rc=0, file written *(so G1 is not refusing everything)* |
| G2 | changed `adp.csv` | truncate 8 bytes | **REFUSED**, no output |
| G3 | changed `projections.csv` | append 1 byte | **REFUSED**, no output |
| G4 | malformed invocation | omit the output argument | **REFUSED** with usage, no output |
| P1 | `adp.csv` pin enforced | pin mutated to a wrong value | **REFUSED** |
| P2 | `projections.csv` pin enforced | pin mutated | **REFUSED** |
| P3 | crosswalk pin enforced | pin mutated | **REFUSED** |
| P4 | **resolver-module pin enforced** | pin mutated | **REFUSED** |
| P5 | **control** — no mutation | unmodified source | **built**, 34/364/155/55 |

P1–P4 mutate the *pin* rather than the production file, which is the same predicate a changed file
exercises and does not touch `src/` or the governed crosswalk.

### 1.3 S1 — the self-found defect, disclosed rather than quietly fixed

After v4 was written I mutation-tested the pin predicate itself. v3's `_verify` read:

```python
if expected and not expected.startswith("6f3a1e1c") and actual != expected:
```

**Two live conditional bypasses inside the one function whose entire purpose is that there be none.**
Proven live against generator v3: with a pin set to an empty string, or to any wrong value beginning
`6f3a1e1c`, a **changed input produced a full census with no refusal**; an ordinary wrong pin refused
(control). Neither clause fired under v3's four real pins — none is empty and none has that prefix —
so **v3's shipped behaviour was genuinely fail-closed**. The defect was latent, one edited constant
away from silently passing a changed input.

**This is your own round-3 finding-1 defect class — "reporting a hash is not enforcing one" —
reappearing inside the repair for it.** `_verify` is now unconditional.

**Evidence that the repair changed no result, only the guard:** every substantive block of the
regenerated census is byte-equal to v4's — `totals_all_608`, `totals_sf_populated`,
`position_guard_evaluation`, `wrong_human_top_window_counts`, both ID commitments, and all 34
`wrong_human_mappings`. The only diffs are three added metadata keys (`generator_version`,
`pin_verification`, `resolver_dependency_closure`) and the generator's own hash. **The bypass never
fired, and that is measured rather than asserted.**

### 1.4 Scope wording, corrected

A **203-line executable Python evidence generator was authored AND RUN** this session (`wc -l`; v3
was 187). It is evidence tooling, not product or intake code — but v3's *"No code"* was factually
false, and every artifact is **commit-intended**, not committed.

**Lint status, disclosed rather than left to be found:** `ruff check` reports **5 findings** on the
generator — `E401`/`I001` import formatting and two `E702` semicolons, all inherited from v3's
compressed style. **All five are cosmetic; none is semantic.** The file sits **outside the governed
lint scope**, which `03` §Enforcement fixes at `ruff check src app` (CI runs exactly that). They are
not repaired here because doing so would re-cascade every hash in §5 for zero behavioural change; say
the word and they go in the same edit as any other round-4 repair.

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
  census's expected SHA/bytes recorded in §5 (a document cannot contain its own hash).

Result: **11,611 bytes**, against the 181,350-byte artifact v2 proposed to commit — a **94%
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
vintage proved position necessary.* Position also quarantines a future name agreement with position
disagreement, and **position-only resolution is prohibited**.

**Terminology corrected:** this is a **guard evaluation against known-positive cases**, not code
mutation testing. v3 called it mutation testing; that names a different technique. *(§1.2's P-rows
are the real thing, on the generator's own predicate.)*

**Team remains unavailable and untested** — the governed crosswalk carries no team field, so that
half of the identity rule is unexecutable with present sources.

## 4. Protocol wording and the top-k rule (finding 4)

1. **≤ 7 days is RETRIEVAL ALIGNMENT, not provider source-as-of equivalence.** Renamed
   `max_retrieval_alignment_days`. It bounds when the two artifacts were *fetched*; it says nothing
   about the periods the providers' underlying data describe, which remain uncharacterised for
   Footballguys. **A build stamp remains barred as an as-of value.** If provider-authentic effective
   dates ever exist, an as-of-to-as-of ceiling with timezone and cutoff is a **separate** rule.
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

## 5. Artifact register

**Current — the only commit-intended set:**

| Artifact | SHA-256 | Bytes |
| :-- | :-- | --: |
| `footballguys_identity_census_generator_v4.py` | `030e34ae4c60f98eaac68612b5ac5d592966a45227201c9e93a103348a7b1956` | — |
| `footballguys_adp_identity_census_claude_v5_minimized.json` | `56d0ea5a68b0a307b91b352797a21c83dcc7f900df9966a34ac45c22cd7f2020` | 11,611 |
| full census — **SCRATCH ONLY, expected-output target** | `df6e094876f3d52d5aaeeef084e421095126a5316707dc829b3eec0ac05c36b8` | 271,626 |

**Superseded, retained on disk as the defect exhibit, NOT commit-intended:**

| Artifact | SHA-256 | Bytes | Why superseded |
| :-- | :-- | --: | :-- |
| `footballguys_identity_census_generator_v3.py` | `e0d35ee9f37c4e10eda46674cedeb28ac5d8408a09a919bdaa1d91cad5f1bf56` | — | carries the S1 bypasses |
| `footballguys_adp_identity_census_claude_v4_minimized.json` | `cca3025a…` | 11,337 | produced by the above |
| its full census | `f83e6d73…` | 271,352 | produced by the above |

The v3-generator artifacts were **independently reproduced byte-for-byte** before the repair — my
regeneration of both the minimized and full outputs matched the submitted pins exactly, and matched a
second lane's independently generated full census byte-for-byte.

## 6. Everything Codex verified independently in round 3

Recorded because it is the audit trail: submitted hashes and byte counts; the minimized output
reproduced **byte-for-byte**; `--full` regenerating **608 distinct uniform-schema rows**; the 136
unresolved projection rows restored (78 SF); verdict totals exact; position **364/364** agreement on
same-human rows with **32 disagree / 2 agree** on wrong links; the baseline SQL reproducing
`f6f08b23…`; and **both 500-row ladders** plus the result supersession confirmed correct.

## 7. Standing

Overlay/qualitative only; `decision_supported=False`; never an Engine A/B feature. `projections.csv`
admitted **solely as identity evidence** — its projection values are expert consensus and are
contractually barred as model signal (`01` §Engine B). Off-season cadence median 7 days (n=159) is
evidenced; **the in-season median of 4 days is WEAK (n=8) and is not a cadence claim.**
**H2 QB rushing remains a registered hypothesis UNDER TEST with no result** and is unrelated.

## 8. State

**Horizon: FAILED. Cohort floor: FAILED. Ingestion RED: CLOSED. Comparison: not opened. Nothing
committed.** The contract's own answer remains **stop**. If David stops the candidate, the
defensible record is **`blocked_for_use` because identity correctness and horizon/use fitness are
unestablished and a safer incumbent already exists** — explicitly **not** because any ρ proved
redundancy.
