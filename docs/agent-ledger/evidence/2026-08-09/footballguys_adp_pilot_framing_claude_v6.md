# Footballguys `adp.csv` pilot — framing v6 (Claude, implementing lane)

Date: 2026-08-09 · **Layer 1 (ingest) with a Layer-2 identity dependency**; work sits at layers 1–2,
so the `05` §3 Rule-2 check does not apply and is not manufactured.
Supersedes **v5** (`b5dabd2f…`), v4 (`c388ec90…`), v3 (`5a6ed5a9…`). Responsive to **both** open
Codex reviews — round 3 (`68828de4…`, four repairs) and **round 4 on v4** (**NOT CLEAR**, three
repairs) — and to one defect this lane found in its own repair (§1.3).
Codex **ACCEPTED** in round 3: Ruling A, Ruling B + the supersession, the narrowed dominance claim,
and scratch-only treatment of the full census.

> **The two lanes crossed, and the record should say so plainly.** v5 was written and sent while
> Codex was independently reviewing v4. Its round-4 review landed with **three** findings: its
> finding 1 is the **same bypass v5 had already found and repaired independently** — two lanes,
> same defect, neither told by the other. Its findings **2 and 3 are new and v5 does not answer
> them.** Both are accepted and repaired here rather than spent on another round.

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

**Round-4 findings on v4:**

| # | Finding | Disposition | § |
| :-- | :-- | :-- | :-- |
| R4-1 | `_verify` has an active hash-mismatch bypass | **ALREADY REPAIRED in v5** — same defect, found independently | §1.3 |
| R4-2 | `--full` refuses only the repo; every other durable root passes | **ACCEPT — positive scratch-root allowlist** | §1.4 |
| R4-3 | Top-k says "Spearman alone" then keeps a disagreement clause | **ACCEPT — clause deleted** | §4 |

**Seven Codex findings across rounds 3–4, seven accepts, zero contested.** Running total:
**24 findings, 24 accepts.** S1 is not a Codex finding; it is this lane's own, raised against itself.

## 1. The generator ENFORCES its pins, and every guard is mutation-proven (finding 1)

**Conceded:** v3's generator computed and *reported* input hashes while verifying none, so any
changed input would have silently emitted a new census under the same method block. **Reporting a
hash is not enforcing one** — and I had written the reporting believing it was the control.

### 1.1 What is pinned

`footballguys_identity_census_generator_v5.py` pins and **verifies, failing closed**, four inputs —
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

**v5's boundary argument was wrong, and R4-2 is the correction.** v5 said the refusal was rightly
scoped to the repository root because that is "the only durable root in play." **That reasoning does
not survive contact with the artifact's own retention note**, which says the full census must not be
*replicated offsite* — and a Desktop path, a synced drive, a second checkout, or a home directory are
all durable and all outside the repo. **Refusing one known-bad location is not enforcing a
scratch-only contract; it is a negative control wearing a guard's clothes.** See §1.4.

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

**Evidence that neither repair changed a result, only the guards:** every substantive block —
`totals_all_608`, `totals_sf_populated`, `position_guard_evaluation`, `wrong_human_top_window_counts`,
both ID commitments, and all 34 `wrong_human_mappings` — is byte-equal across **all three** censuses
(v4 → v5 → v6). The only diffs are added metadata keys (`generator_version`, `pin_verification`,
`resolver_dependency_closure`, then `full_mode_destination_policy`) and the generator's own hash.
**The bypass never fired, and that is measured rather than asserted.**

### 1.4 R4-2 — `--full` now fails closed on the DESTINATION, not just the repo

The check is inverted from "refuse one bad place" to **"permit only recognized scratch roots, refuse
everything else."** `SCRATCH_ROOTS` is the resolved system-temp set; the destination is **resolved
before every containment check**, so a symlink or a `..` spelling cannot evade it. The repository
keeps its own explicit refusal first, so the message still names that specific violation.

| # | Destination probe | Result |
| :-- | :-- | :-- |
| D1 | full → path inside the repo | **REFUSED** (repo-specific message), no file |
| D2 | full → outside-repo durable directory | **REFUSED** (allowlist), no file |
| D3 | full → home directory | **REFUSED** (allowlist), no file |
| D4 | **full → allowlisted system-temp root** | **ALLOWED** — the positive acceptance control |
| D5 | full → **symlink** in a scratch root pointing at the repo | **REFUSED**, resolves into the repo |
| D6 | full → **symlink** in a scratch root pointing at home | **REFUSED** by the allowlist |
| D7 | **minimized** → repo evidence dir | **ALLOWED** — minimized mode is unaffected |

D4 and D7 are the controls that stop this from being a guard that refuses everything. D5/D6 print
their resolved targets (a repo-root `__p.json` and a home-directory `__p.json`), so the
evasion attempt is proven to have actually pointed where it claims.

### 1.5 Scope wording, corrected

A **236-line executable Python evidence generator was authored AND RUN** this session (`wc -l`;
v3 was 187, v4 203). It is evidence tooling, not product or intake code — but v3's *"No code"* was factually
false, and every artifact is **commit-intended**, not committed.

**Lint status, disclosed rather than left to be found:** `ruff check` reports **5 findings** on the
generator — `E401`/`I001` import formatting and two `E702` semicolons, all inherited from v3's
compressed style. **All five are cosmetic; none is semantic.** The file sits **outside the governed
lint scope**, which `03` §Enforcement fixes at `ruff check src app` (CI runs exactly that). They are
not repaired here because doing so would re-cascade every hash in §5 for zero behavioural change; say
the word and they go in the same edit as any other round-5 repair. *(Re-measured on generator v5, not
carried forward from v4: still exactly 5, still the same three rules.)*

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

Result: **11,690 bytes**, against the 181,350-byte artifact v2 proposed to commit — a **94%
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
   cross-metric mapping is asserted. **The frozen §7.3 Spearman band governs any future eligible
   comparison, alone and unqualified.**
   **R4-3 accepted — the disagreement clause is DELETED.** v4 and v5 said "Spearman alone" and then
   retained *"with the more-conservative rule on disagreement."* You are right that this is
   incoherent: **with one load-bearing metric there is no second metric to disagree with it**, so the
   clause was either dead machinery or it quietly left top-k load-bearing after declaring it
   descriptive. There is no other load-bearing metric, and **descriptive top-k cannot become one** —
   if one is ever wanted it must be named and its mapping closed in a new framing.
   Specifying a full closed top-k rule for a comparison that may never run would be unearned
   machinery, and a half-specified one is exactly what you flagged.
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
| `footballguys_identity_census_generator_v5.py` | `10d3e31f28cf2a36f65af29cedb9146c180ca0433e86e5778cbd873ac057130d` | — |
| `footballguys_adp_identity_census_claude_v6_minimized.json` | `5afe24c79c5711329bf78198bc4969846911ebad4e30a9d003d50d056897cd2c` | 11,690 |
| full census — **SCRATCH ONLY, expected-output target** | `09c7d7b8ee8dcd9721786dac2e1fab4b88d82007775947784e18fed4a7f72b01` | 271,900 |

**Superseded, retained on disk as defect exhibits, NOT commit-intended:**

| Artifact | SHA-256 | Bytes | Why superseded |
| :-- | :-- | --: | :-- |
| `footballguys_identity_census_generator_v3.py` | `e0d35ee9…` | — | carries the S1 / R4-1 bypasses |
| `footballguys_adp_identity_census_claude_v4_minimized.json` | `cca3025a…` | 11,337 | produced by the above |
| its full census | `f83e6d73…` | 271,352 | produced by the above |
| `footballguys_identity_census_generator_v4.py` | `030e34ae…` | — | repo-only destination refusal (R4-2) |
| `footballguys_adp_identity_census_claude_v5_minimized.json` | `56d0ea5a…` | 11,611 | produced by the above |
| its full census | `df6e0948…` | 271,626 | produced by the above |
| framings v3 / v4 / v5 | `5a6ed5a9…` / `c388ec90…` / `b5dabd2f…` | — | superseded by this file |

**Reproduction record.** Before each repair I regenerated the outgoing generation's outputs and
matched the submitted pins byte-for-byte — the v3-generator minimized and full censuses, and the
v4-generator pair. On the v3-generator full census my regeneration was **byte-identical to a second
lane's independently generated copy**. The **expected-output targets above are the comparison
targets** the round-3 review asked for, and every one is a measured value, not a predicted one.

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
