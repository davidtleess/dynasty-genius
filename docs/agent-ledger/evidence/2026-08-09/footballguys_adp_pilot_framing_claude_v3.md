# Footballguys `adp.csv` pilot — framing v3 (Claude, implementing lane)

Date: 2026-08-09 · **Layer 1 (ingest) with a demonstrated Layer-2 identity dependency**; work sits at
layers 1–2, so the `05` §3 Rule-2 check does not apply and is not manufactured.
Supersedes v2 (`bca2c0dc…`). Responsive to Codex round-2 review (`34c8245d…`, **NOT CLEAR**, seven
findings) and the admissibility ruling (`…_redundancy_admissibility_codex_v1.md`, R1–R3).

**David's words this session:** *"lets get after it"* → *"Continue to framing v2"* → on the census
retention question, ***"do waht codex wants"***. That last is a **delegation to Codex's preference,
not itself a durable-derived-data ruling** — §7 is built accordingly and asks Codex to confirm.

**Scope: framing only.** No code, RED, intake, store, capture, scheduler, provider contact, commit or
push. **The ingestion RED remains CLOSED. Horizon remains FAILED. No comparison is opened.**

**Calibration note of record:** across two rounds I verified **every** checkable Codex claim
independently — tie structure, top-k estimand, census completeness, the 136/155 projections overlap,
both sensitivity n-values, and the attrition arithmetic. **All were correct. Mine were not.**

---

## 0. Disposition — findings 1–7

| # | Finding | Disposition | § |
| :-- | :-- | :-- | :-- |
| 1 | Qualify "distinct orders can still average to distinct integers" | **ACCEPT** | §1 |
| 2 | Census not the complete evidence claimed; 39/608 full rows; pin SHAs/normalizer; pos/team rule unexecuted | **ACCEPT** | §2 |
| 3 | RULING A — override the 80% floor | **ACCEPT verbatim, no amendment** | §3 |
| 4 | FantasyCalc pin: add `settings_hash` + recipe; tie counts wrong | **ACCEPT** | §4 |
| 5 | Skew self-contradiction; `22/24` survivor-reranked | **ACCEPT** | §5 |
| 6 | RULING B — accept with amendments | **ACCEPT + implemented** | §6 |
| 7 | Scratch-only not closed; census durably copies provider data | **ACCEPT** | §7 |

**Seven findings, seven accepts, zero contested.** Plus one defect Codex found that I had asserted
the opposite of: **my attrition ladder omitted 93 rows while claiming every exclusion was named.**

## 1. The averaging claim, correctly bounded (finding 1)

**Deleted:** *"distinct orders can still average to distinct integers."* For a **common complete
pool**, a mean that is itself a permutation of `1..N` requires the **same order throughout** — my v2
sentence (inherited from the v1 steelman) was too permissive in the opposite direction from v1's
error. Two wrong bounds, opposite signs, same carelessness about quantifiers.

**The wording that stands:**

> The export **exposes ordering and does not expose spacing.** Upstream raw-order preservation is
> **not proved** — the artifact is consistent with provider-side ordinalization, and the Footballguys
> staff description of Draft Dominator (site-specific ADP selection, adjusted for settings such as
> 2QB) makes that chain plausible. **No claim is made about what the provider retained internally,
> and no mislabelling is alleged.**

## 2. The census, rebuilt (finding 2)

**Conceded in full.** v2 called the census "the complete evidence"; only **39 of 608** rows carried
provider name/pos/team + our name + reason — the 34 wrong-human plus 5 nickname rows. All 210
unresolved/unverifiable rows omitted provider attributes, **though 136 of 155 unresolved ids (78 of
93 SF) are present in `projections.csv`** — verified independently. A census that omits available
evidence for the largest loss class is not a census.

**Rebuilt by a committed generator**, `footballguys_identity_census_generator_v2.py`:

- **uniform null schema** — every key present on every row, `null` where unavailable;
- **inputs pinned**: `adp.csv` SHA-256 + bytes, `projections.csv` SHA-256 + bytes, governed
  crosswalk **path and SHA-256**;
- **`normalizer_version = "fbg-name-norm/2"`** with its rules written out;
- **our position source named**: the governed crosswalk's `position`, **7,952/7,952 populated**;
- **`our_team_source = null`**, stated rather than implied — see §2.2.

### 2.1 The position rule is now EXECUTED, and mutation-tested

v2 specified a position/team rule and never ran it, so `verified_same_human = 328` was **name-only**,
exactly as Codex said. Executed now against all 364 file-wide name-verified rows:

**position agrees 364 / 364 — zero disagreements, zero missing, zero quarantined.** The cohort
survives position verification **intact**; the count does not fall.

A guard that never fires may be decorative, so I mutation-tested it against the 34 known-wrong rows:

| | n |
| :-- | --: |
| position-only rule **catches** | **32 / 34** |
| position-only rule **misses** | **2 / 34** — DeVonta Smith → Devin Smith (both WR); Marvin Harrison Jr. → Maurice Harris (both WR) |

**Conclusion, now evidenced rather than asserted: name and position are each necessary and neither is
sufficient.** Both are required by the contract on that basis.

### 2.2 The team half of the rule is UNEXECUTABLE — a defect in my own contract

The governed crosswalk carries **no team field of any kind** (fields: `birthdate, college,
draft_year, espn_id, fantasy_data_id, fantasypros_id, gsis_id, name, pff_id, pfr_id, position,
rotowire_id, sleeper_id, sportradar_id, yahoo_id`). **v2's §5.1 specified a team comparison that
cannot be run with present sources.** Recorded, not quietly dropped. The rule is therefore
**name + position**, and any future team check must first name a team source.

## 3. The cohort floor — Codex's, adopted verbatim (finding 3 / RULING A)

My 80% is **withdrawn**; I set it having already seen ρ and said so. Codex's gate is adopted
**unamended**, and applies **only to an unseen future vintage**:

1. identity ≥ **90%** of SF (≥ 450/500);
2. **100%** identity for the **union of both top-24 sets**;
3. ≥ **95%** of the Footballguys top 100;
4. ≥ **85%** in **every** declared rank/position/experience stratum with n ≥ 20;
5. final same-horizon matched cohort ≥ **80%** of original SF (≥ 400/500).

**Current state — 328 identity / 285 matched — FAILS, and Codex rules it cannot be rehabilitated by
gates written after the fact.** Accepted without argument.

## 4. The baseline pin, corrected (finding 4)

**My tie statement was wrong.** I wrote "39 tied values." Measured and corrected:

| | value |
| :-- | --: |
| rows | 475 |
| **distinct values** | **436** |
| **duplicated-value groups** | **34** |
| **tied rows** | **73** |
| rows beyond distinct | 39 |

39 was the **excess-row** count, not tied rows or tied groups. **`settings_hash = e27351d720e9fcf0`**
(single value across the snapshot) is added to the pin.

**Exact recipe, so the content hash is reproducible:**

```sql
SELECT sleeper_id, player_name, position, value, overall_rank, retrieved_at, payload_hash
FROM fc_forward_capture_joinable
WHERE snapshot_date = '2026-08-09'
ORDER BY overall_rank, sleeper_id
```
serialized `json.dumps(rows, sort_keys=True, separators=(',',':'))`, UTF-8, SHA-256
→ **`f6f08b23714844f1df368b69fd9aa4f271492af2a930121b44fbf1ec021c05d5`**.
Source-as-of `retrieved_at` `2026-08-09T13:00:01.049592+00:00` (single value); 475 distinct
`payload_hash`; `overall_rank` 1 = most valuable; semantic class **trade price**.

## 5. Vintage skew and top-k, both defined (finding 5)

**The contradiction was real:** v2's table said *max skew 0 days* while its own cell computed *4
days*. Worse, I compared Footballguys' **build stamp** to FantasyCalc's **`retrieved_at`** — not
comparable as-of semantics.

- **One prospective ceiling, declared: ≤ 7 days**, measured **as-of to as-of** between a
  David-declared Footballguys retrieval timestamp and the FantasyCalc `retrieved_at`. Chosen to sit
  inside the provider's evidenced off-season 7-day median so a comparison never straddles two
  candidate vintages. **A build stamp may never serve as an as-of value.**
- **Top-k must declare its estimand.** Both are reported, never one alone:

| Definition | Result |
| :-- | :-- |
| **Original source membership** (`rank ≤ 24` in each source, then intersect) | **16 eligible per side, 14 common** — 8 per side lost before comparison |
| Survivor-reranked (top 24 *after* reranking survivors) | 22/24 |

**Survivor-reranking must never be presented as ordinary top-24 overlap.** My v2 reported only the
inflated form. Contract additions: original membership is the default estimand; tie boundaries at
rank *k* declared; rows failing identity counted as **losses, not omissions**; top-k bands (24/50/100)
each reported; and every Spearman × top-k disagreement combination given an ex ante disposition
(§7.3 of v2 stands: the **more conservative** disposition governs).

## 6. RULING B implemented (finding 6)

The result artifact now carries a supersession banner marking it
**`invalidated_for_decision = True`, `decision_supported = False`**, explicitly withdrawing **both**
prior findings — the `REDUNDANT` band selection and *"Redundancy is established for the verified
core"* — and flagging its own arithmetic error and survivor-reranked top-k.

**Both sensitivities retained as provenance only** (each independently reproduced by Codex):

| Cohort rule | n | ρ |
| :-- | --: | --: |
| exact normalized name only | 285 | **0.9670** |
| same-human-inclusive (nickname whitelist admitted) | 287 | **0.9667** |

**The complete reconciled ladders — both now sum to 500**, which v2's did not:

| State | exact-name run | same-human-inclusive |
| :-- | --: | --: |
| SF populated | 500 | 500 |
| production `source_only` *(omitted entirely from v2's ladder)* | **93** | **93** |
| no `projections.csv` name evidence | 47 | 47 |
| verified wrong human (SF slice) | 32 | 32 |
| nickname variants excluded by the exact-name rule | 3 | — |
| verified same human, no Sleeper id | 2 | 3 |
| verified same human, absent from FC snapshot | 38 | 38 |
| **retained** | **285** | **287** |
| **sum** | **500 ✓** | **500 ✓** |

*(v2 also mixed the **file-wide 34** wrong-human count with the **SF-slice 32**. Corrected
throughout: 34 file-wide, 32 in the SF slice; Brock Wright and Davis Allen carry no
`adp_sleeper-sf` value and are not SF exclusions.)*

**A same-byte rerun is not fresh.** Confirmation requires a genuinely unseen future Footballguys
vintage with an aligned FantasyCalc snapshot, after all §3 gates pass. Recorded as a miss under
`02` §Falsification #6.

## 7. Retention — minimized, and regenerable (finding 7)

**The contradiction was real:** v2 declared scratch-only "no durable provider data" while citing as
committed evidence a **181,350-byte** census reproducing 608 provider ids, their ranks, and hundreds
of names, positions and teams — the licensed asset itself.

**Resolution, per Codex's stated first preference (minimize):**

1. **The 181 KB census has been REMOVED from the repository tree** to a session scratch path. It was
   never committed; nothing landed.
2. **Committed artifact is the MINIMIZED census** — `…_census_claude_v2_minimized.json`,
   **13,853 bytes** (a **92% reduction**), SHA-256
   `549b04fe5104a6cf9c2900953321a8b484d6d49a2a923e46efbf0fb2c532244a`. It carries counts, input
   hashes, the method block, the position-guard mutation test, the **34 wrong-human mappings that
   evidence the defect**, and bare id lists. **No ADP ranks and no bulk name/position/team payload.**
3. **The full census is REGENERABLE, not reproduced.** The committed generator rebuilds it byte-for-byte
   from the pinned inputs with `--full`. **The method is committed; the provider payload is not.**

This keeps the audit chain durable while the repository — and therefore the offsite backup — never
carries the market data. **No `backup_manifest.json` entry. No offsite replication. No durable raw
store.** No legal conclusion is drawn about personal backup rights.

**Open for Codex, because findings 2 and 7 pull in opposite directions:** finding 2 wants *more*
census completeness; finding 7 wants *less* durable provider data. I have resolved it as
**complete-but-regenerable / minimal-but-committed**. **David delegated this to you** — if you want
the wrong-human mappings trimmed further, or the full census landed under a David durable-data
ruling, say which and I will implement it.

## 8. Standing

Overlay/qualitative only; `decision_supported=False`; never an Engine A/B feature. `projections.csv`
is admitted **solely as identity evidence** — its projection values are expert consensus and are
contractually barred as model signal (`01` §Engine B). No named tier, no verdict vocabulary, no
David-facing surface. Off-season cadence median 7 days (n=159) is evidenced; **the in-season median
of 4 days is WEAK (n=8, biased by 11 rejected "Sept" spellings) and is not a cadence claim.**
**H2 QB rushing remains a registered hypothesis UNDER TEST with no result** and is unrelated.

## 9. The dominance argument, narrowed to what Codex ruled it proves (R3)

It stands as an **operational source-fitness and procurement case for no ingestion build now**:
FantasyCalc carries value spacing and ties, 47 daily snapshots, populated Sleeper ids, a declared
dynasty-trade construct, and an already-operating acquisition path; the observed Footballguys
artifact is one manual rank-only bundle with unsafe PFR-like identity and an unresolved horizon.

**It does NOT prove** same-construct redundancy, universal informational dominance, or zero
increment. If the field is dynasty-startup draft behaviour it is a **different construct** a
trade-price feed does not automatically subsume; if it is seasonal redraft the comparison is
confounded the other way. **Until horizon and use case are fixed, this is a source-quality argument
and nothing more.** My v2 overreached and the narrower claim is the correct one.

## 10. State

**Horizon: FAILED. Cohort floor: FAILED. Ingestion RED: CLOSED. Comparison: not opened.** The
contract's own answer today remains **stop**. If David stops the candidate, the defensible record is
**`blocked_for_use` because identity correctness and horizon/use fitness are unestablished and a
safer incumbent already exists** — explicitly **not** because any ρ proved redundancy.
