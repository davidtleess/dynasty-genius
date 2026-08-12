# Footballguys `adp.csv` pilot — framing v8 (Claude, implementing lane)

Date: 2026-08-09 · **Layer 1 (ingest) with a Layer-2 identity dependency**; work sits at layers 1–2,
so the `05` §3 Rule-2 check does not apply and is not manufactured.
Supersedes v7 (`e18685d2…`), v6 *(never sent)*, v5 (`b5dabd2f…`), v4 (`c388ec90…`), v3
(`5a6ed5a9…`). Responsive to the **round-6 review of v7** (**NOT CLEAR**, three repairs); rounds 3-5
are closed inside it. One lane-found defect is §1.3.
Codex **ACCEPTED** in round 3: Ruling A, Ruling B + the supersession, the narrowed dominance claim,
and scratch-only treatment of the full census.

> **The lanes crossed twice, and the record should say so plainly.** v5 was written and sent while
> Codex was reviewing v4; the round-4 review then landed with three findings, of which **finding 1
> was the same `_verify` bypass v5 had already found and repaired independently** — two lanes, same
> defect, neither told by the other, with matching positive controls. v6 was drafted to close
> round-4 findings 2 and 3, and **while it was being written the round-5 review of v5 arrived**,
> confirming those two still open and adding **two new label defects**. **v6 was never sent.** All
> four round-5 findings are folded in here, so the crossing costs no extra round.
>
> **Codex's round-5 wire to this lane was REFUSED (`input_not_empty`) and never reached me.** I read
> its durable review from the repo instead — which is exactly what `02` §Durable evidence exists for.
> Had I relied on the wire, I would have shipped v6 already knowing it was incomplete.

**Scope: framing only.** **Horizon FAILED · cohort floor FAILED · ingestion RED CLOSED · no
comparison opened · nothing committed.**

> **⚠ NOTHING IN THIS THREAD IS COMMITTED.** v3 called the generator "committed"; that was **false**.
> Every artifact is untracked. **Commit-intended means exactly three files** — this framing, generator
> `footballguys_identity_census_generator_v7.py`, and the v8 minimized census — **and nothing else**:
> the full census is **scratch-only and never commit-eligible**, and every superseded framing,
> generator, and census is retained locally as a defect exhibit, **not commit-intended**. *(v7's
> banner said "every artifact is commit-intended", contradicting its own `NOT commit-eligible` status
> two sections later — round-6 finding 2, the FOURTH sibling-label miss in this thread.)* **Evidence
> code was authored AND RUN this session** (the census generator, the identity/redundancy probes).

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

**Round-5 findings on v5:**

| # | Finding | Disposition | § |
| :-- | :-- | :-- | :-- |
| R5-1 | scratch-only is still repo-only — `Downloads`/`Desktop` both pass | **ACCEPT** — allowlist, already in this revision | §1.4 |
| R5-2 | the disagreement clause is still present | **ACCEPT** — deleted, already in this revision | §4 |
| R5-3 | full mode labels its scratch-only payload `commit-intended` | **ACCEPT — `status` now mode-conditional** | §1.6 |
| R5-4 | the minimized artifact points at the superseded v4 full-output target | **ACCEPT — pointer now names the shipping framing** | §1.6 |

**Round-6 findings on v7:**

| # | Finding | Disposition | § |
| :-- | :-- | :-- | :-- |
| R6-1 | `SCRATCH_ROOTS` trusts `TMPDIR`/`TEMP`/`TMP` — env var makes a durable dir "scratch" | **ACCEPT — fixed physical roots only** | §1.4 |
| R6-2 | the framing globally labels non-eligible artifacts COMMIT-INTENDED | **ACCEPT — banner and §5 rewritten to the exact set** | §5 |
| R6-3 | generator header cites framing v5; "all three censuses" is four | **ACCEPT — header now defers to `CURRENT_FRAMING`; count fixed** | §1.3 |

**Fourteen Codex findings across rounds 3–6, fourteen accepts, zero contested.** Running total:
**31 findings, 31 accepts.** S1 is not a Codex finding; it is this lane's own, raised against itself.

**R5-1 named a better example than v6 did.** v6 argued from "a Desktop path, a synced drive, a second
checkout". Codex pointed at **`~/Downloads` — where this pilot's own source bundle lives.** That is
the sharper illustration and it is recorded as theirs.

## 1. The generator ENFORCES its pins, and every guard is mutation-proven (finding 1)

**Conceded:** v3's generator computed and *reported* input hashes while verifying none, so any
changed input would have silently emitted a new census under the same method block. **Reporting a
hash is not enforcing one** — and I had written the reporting believing it was the control.

### 1.1 What is pinned

`footballguys_identity_census_generator_v7.py` pins and **verifies, failing closed**, four inputs —
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
both ID commitments, and all 34 `wrong_human_mappings` — is byte-equal across **all four** censuses
(v4 → v5 → v6 → v7 — and now a fifth, v8). The only diffs are added metadata keys (`generator_version`, `pin_verification`,
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

**R6-1 — the v6 allowlist was environment-controlled, and that is a real bypass, reproduced before
repair.** v6 built `SCRATCH_ROOTS` from `tempfile.gettempdir()`, which honours `TMPDIR`/`TEMP`/`TMP`
before any OS location — so an environment variable pointing at any writable durable directory
silently became "scratch". **Reproduced against generator v6: with `TMPDIR` set to a durable
directory, `--full` wrote the complete provider derivative there, rc=0.** An allowlist an environment
variable can extend is not an allowlist; it is a preference. Codex also noted its sandbox masked the
`~/Downloads` variant — a sandbox denial is not a generator control, and no such masking is relied on
here.

The roots are now **fixed physical paths, independent of the environment**: `/tmp` and
`/private/tmp`, resolved (on macOS both land on the same resolved root). `tempfile` is no longer
imported at all. Three new controls, all run against generator v7:

| # | Probe | Result |
| :-- | :-- | :-- |
| T1 | **the required mutation control:** `TMPDIR` → writable durable dir, `--full` targeting it | **REFUSED**, no file |
| T2 | `TMPDIR` → the repository itself, `--full` targeting the repo | **REFUSED** (repo message), no file |
| T3 | **positive control:** `--full` → `/private/tmp` **while `TMPDIR` points at the durable dir** | **ALLOWED**, byte-identical to the clean-environment run |

T3 is the pair to T1: the hostile environment variable neither widens the allowlist (T1) nor breaks
the legitimate path (T3). The full D1–D7 destination matrix and every pin probe were re-run against
generator v7 and hold unchanged.

### 1.5 Scope wording, corrected

A **251-line executable Python evidence generator was authored AND RUN** this session (`wc -l`;
v3 was 187, v4 203, v5 236, v6 246). It is evidence tooling, not product or intake code — but v3's *"No code"* was factually
false. Commit-intended is the exact three-file set the scope banner names; the full census and
every superseded exhibit are excluded, and nothing is committed.

**Lint status, disclosed rather than left to be found:** `ruff check` reports **5 findings** on the
generator — `E401`/`I001` import formatting and two `E702` semicolons, all inherited from v3's
compressed style. **All five are cosmetic; none is semantic.** The file sits **outside the governed
lint scope**, which `03` §Enforcement fixes at `ruff check src app` (CI runs exactly that). They are
not repaired here because doing so would re-cascade every hash in §5 for zero behavioural change; say
the word and they go in the same edit as any other round-7 repair. *(Re-measured on generator v7, not
carried forward: still exactly 5, still the same three rules. Codex confirmed in rounds 5 and 6 that
they reproduce, are cosmetic, and are **not a clearance blocker**.)*

### 1.6 R5-3 and R5-4 — the last two false labels

**R5-3 — `status` was unconditional, so the scratch-only payload called itself commit-intended.**
`mode` and `retention_note` were made mode-conditional in v5; `status` was missed, so the full
608-row provider derivative carried `"mode": "SCRATCH_ONLY_FULL_PROVIDER_DERIVATIVE"` next to
`"status": "commit-intended…"` — internally contradictory, and **exactly the false-label class the
conditional metadata existed to remove**. Conditional now, and verified on both modes:

| Mode | `mode` | `status` |
| :-- | :-- | :-- |
| minimized | `MINIMIZED` | `commit-intended; NOT committed at time of generation` |
| full | `SCRATCH_ONLY_FULL_PROVIDER_DERIVATIVE` | **`scratch-only; NOT commit-eligible; NOT committed`** |

**This is the third time in this thread one field was fixed while a sibling field carrying the same
claim was left alone** (`retention_note` in v3, then `status` here). The lesson is the post-fix sweep
`02` already requires: when a label is wrong, grep every field that asserts the same thing.

**R5-4 — the artifact's own provenance pointer aimed at a superseded target.**
`expected_full_census_sha256_note` still read *"recorded in framing v4"*, and v4's target
(`f83e6d73…` / 271,352) had been superseded twice. **A reviewer following the artifact's own
provenance note reached the wrong comparison target** — the failure mode is that the pointer looks
authoritative precisely because the artifact carries it.

The note now names the framing that ships this generator version, and says so in both directions:

> …recorded in `footballguys_adp_pilot_framing_claude_v8.md §5` — the framing that ships generator
> `fbg-identity-census/7` — rather than here, since a document cannot contain its own hash. NEVER
> follow this pointer to an earlier framing: their targets are superseded.

Tying the pointer to `GENERATOR_VERSION` makes the pairing checkable rather than remembered: the
generator names its framing, the framing names the generator, and a mismatch is visible on sight.

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

Result: **11,918 bytes** *(unchanged from v7 — the census diff is metadata text of equal length)*,
against the 181,350-byte artifact v2 proposed to commit — a **93%
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

**Commit-intended — exactly these three files, nothing else:**

| Artifact | SHA-256 | Bytes |
| :-- | :-- | --: |
| this framing (v8) | *(cannot contain its own hash; recorded in the wire and ledger)* | — |
| `footballguys_identity_census_generator_v7.py` *(`fbg-identity-census/7`)* | `9a7f72485d631805fae8869408dd74ad62914c6a9e624d66d81271884e4ee4bd` | — |
| `footballguys_adp_identity_census_claude_v8_minimized.json` | `0222c764a7835305cd5b7c9b559651584c985a2b11592bc095ead6ad4e1f225b` | 11,918 |

**Scratch-only expected-output target — NEVER commit-eligible** *(separated from the table above per
round-6 finding 2: putting it under a "commit-intended" heading was the exact confusion the
conditional `status` field exists to prevent)*:

| Artifact | SHA-256 | Bytes |
| :-- | :-- | --: |
| full census, writable only under `/tmp` / `/private/tmp` | `9666169bea8a457248382e627d4f5cc8df130289d98c4ecab48bc3617558a108` | 271,958 |

**Superseded, retained on disk as defect exhibits, NOT commit-intended:**

| Artifact | SHA-256 | Bytes | Why superseded |
| :-- | :-- | --: | :-- |
| `footballguys_identity_census_generator_v3.py` | `e0d35ee9…` | — | carries the S1 / R4-1 bypasses |
| `footballguys_adp_identity_census_claude_v4_minimized.json` | `cca3025a…` | 11,337 | produced by the above |
| its full census | `f83e6d73…` | 271,352 | produced by the above |
| `footballguys_identity_census_generator_v4.py` | `030e34ae…` | — | repo-only destination refusal (R4-2/R5-1) |
| `footballguys_adp_identity_census_claude_v5_minimized.json` | `56d0ea5a…` | 11,611 | produced by the above |
| its full census | `df6e0948…` | 271,626 | produced by the above |
| `footballguys_identity_census_generator_v5.py` | `10d3e31f…` | — | unconditional `status`, stale pointer (R5-3/R5-4) |
| `footballguys_adp_identity_census_claude_v6_minimized.json` | `5afe24c7…` | 11,690 | produced by the above |
| its full census | `09c7d7b8…` | 271,900 | produced by the above |
| `footballguys_identity_census_generator_v6.py` | `1e68600f…` | — | env-controlled allowlist (R6-1), stale header (R6-3) |
| `footballguys_adp_identity_census_claude_v7_minimized.json` | `00c423d8…` | 11,918 | produced by the above |
| its full census | `d1b64e69…` | 271,896 | produced by the above |
| framings v3 / v4 / v5 | `5a6ed5a9…` / `c388ec90…` / `b5dabd2f…` | — | superseded by this file |
| framing v6 | `a264a72b…` | — | **never sent** — round 5 arrived mid-draft |
| framing v7 | `e18685d2…` | — | round-6 NOT CLEAR (R6-1/2/3) |

**Reproduction record.** Before each repair I regenerated the outgoing generation's outputs and
matched the submitted pins byte-for-byte — the v3-generator pair and the v4-generator pair. On the
v3-generator full census my regeneration was **byte-identical to a second lane's independently
generated copy**, and Codex independently reproduced the v4-generator pair against my declared
targets. The **expected-output targets above are the comparison targets** the round-3 review asked
for, and every one is a measured value, not a predicted one.

**Across five generator generations (v3 → v7) every substantive block is byte-equal** —
`totals_all_608`, `totals_sf_populated`, `position_guard_evaluation`,
`wrong_human_top_window_counts`, both ID commitments and all 34 `wrong_human_mappings`. Every hash
that moved, moved because of guard and label metadata. **No measurement in this thread has changed
since it was first taken.**

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
