# Horizon Divergence plan v1 — redraft-market vs dynasty-market lens (Claude, implementing lane)

Date: 2026-08-10 · Status: **plan for cockpit challenge — nothing here is authorized to build until
its phase completes the cockpit cycle and David's word lands per phase.**

**David's order, verbatim (2026-08-10):** *"ok - determine how to plan and execute your
recmmendation in #2"* — the #2 recommendation being: the Footballguys-vs-incumbent delta is
valuable **only** when the redraft-vs-dynasty horizon mismatch is made the subject rather than a
confound, with the identity contract as a hard prerequisite.

## 0. What David's word changes, and what it does not

- **It changes:** the delta question is no longer open — David has ordered planning + execution of
  the horizon-divergence lens. The prior "no delta work without David's word" hold is lifted **for
  this plan's scope**.
- **It does NOT change:** the pilot's `blocked_for_use` record for the *redundancy/replacement* use
  case stands; ADP stays market data — **overlay only, never an Engine A/B input, cordoned from
  decision mechanics**; every output is descriptive, `decision_supported=False`, No-Verdict
  compliant. A divergence view **describes two markets disagreeing; it never says which is right**
  — the moment it implies "the dynasty market is wrong, buy X," it has issued a verdict.

## 1. The product object (layer 5, descriptive)

For each player verified present in BOTH sources under the identity contract:

> **horizon divergence = redraft market position (Footballguys seasonal ADP, SF market) vs dynasty
> market position (incumbent FantasyCalc SF values), as rank-space delta, with both raw ranks
> disclosed alongside.**

The interesting tails are structural, and the surface names the *structure*, not an action:
redraft-high / dynasty-low ≈ win-now assets and aging veterans; redraft-low / dynasty-high ≈
prospects and picks-adjacent youth. This serves the constitution's named decision tension
(contender vs future-value) descriptively.

**Known limits stated up front:** ADP is a drafting artifact (positional scarcity, ADP-vs-value
convention differences); rank-space comparison inherits tie and pool-depth asymmetries the pilot
measured (500-rank SF ladder, 34 tied-value groups); the two sources' vintages must satisfy the
pilot's retrieval-alignment ceiling (≤7 days) or the snapshot is marked `alignment_failed` and
renders as unavailable — never silently computed.

## 2. Layer map and the `05` §3 Rule-2 check (recorded, not skipped)

**Presenting layer: 5 (data analysis).** Dependency check, run against the repo this session:
Footballguys has **no layer-1 substrate** (no intake — ingestion RED closed unbuilt; the manual
bundle sits in Downloads) and **no layer-2 binding** (identity verification exists only as
evidence-grade census tooling; 34 known wrong-human links in a naive join). **Conclusion: the
layer-5 view cannot open first.** The plan is therefore sequenced foundation-first, which is also
David's standing §1 ruling.

## 3. Phases — each is its own cockpit cycle (framing → challenge → disposition → RED → GREEN → CLEAR → David's word)

**Phase A — Layer 1: manual-drop intake + monthly refresh notice (merged with David's #3).**
The reminder thread and the intake are one substrate: A records David's drop with declared
provenance (drop event: source id, schema version, system `recorded_at`, David-declared
`retrieved_at`, raw-bytes SHA-256 per file — the `pff_intake.py` declared-provenance pattern), and
the monthly notice reads that record. **Codex's seven challenge findings on the notice framing v1
are all folded into Phase A's framing v2** — registry home reconciled with the open
PlayerProfiler/PFF manual-feed design rather than forked; "recorded" copy, not "downloaded";
closed timing/state machine (`no_record`/`current`/`due`/`unverifiable`); composition artifact
before any surface work; backup-manifest landing-order law; the full mutant-per-seed control set.
**The vintage series (drop dates + hashes) that finding 4 struck as unearned for a bare reminder is
now earned here** — it is the input Phase C consumes — and is admitted through intake design, not
smuggled through a reminder.

**Phase B — Layer 2: identity contract.** Promote the census machinery from evidence tooling to a
tested contract: PFR-id → canonical id via the governed crosswalk with **exact-normalized-name
verification (whitelist for known nicknames) + position corroboration; quarantine on
name-pass/position-fail; position-only resolution prohibited** (pilot-measured: name separates
34/34 known wrong links, position only 32/34). Unresolved and unverifiable ids stay excluded with
their counts disclosed as the join's denominator. Contract tests are the RED; the pilot's minimized
census is the frozen known-answer fixture.

**Phase C — Layer 5: the divergence computation.** Deterministic, versioned, descriptive artifact:
per-player rank pair + delta + verification status; snapshot stamped with both source vintages,
alignment verdict, identity-contract version, and counts (verified / quarantined / unresolved /
unverifiable). **Monthly cadence, tied to the Phase-A drop event — capture-and-accumulate**, so the
series compounds into the benchmark David's Q2 asked about. Banned-language scan on every emitted
field; tails labeled structurally, never imperatively.

**Phase D — Layer 6: surface.** Only after A–C are CLEAR and David has seen a real Phase-C artifact.
Full design-foundation route: impeccable, pre-code composition artifact, unanchored fresh-agent
visual audit. Not sketched further here — a surface designed before its data exists is the
anti-pattern `00` §Frontend names.

## 4. Open parameters presented for the challenge round (not pre-decided)

1. **Market pairing:** `adp_sleeper-sf` vs FantasyCalc SF is the lead candidate (league is SF);
   whether consensus ADP appears as a disclosed secondary column is open.
2. **Delta form:** raw rank delta vs percentile-space delta over the common verified pool —
   tradeoff: interpretability vs pool-depth robustness. Challenge should pressure both.
3. **Eligibility floor:** minimum common-pool size below which the snapshot reports
   `insufficient_overlap` rather than a delta (pilot measured 328 verified SF identities; the floor
   needs a declared number, not a vibe).
4. **Where the Phase-C artifact lives** relative to the market-overlay cordon (existing overlay
   destinations vs a new `horizon_divergence` store) — architecture question for `01` alignment.

## 5. Falsification seeds (initial; RED authors own the matrix)

Wrong-human join rows (the 34) must be excluded and counted · misaligned vintages must refuse ·
empty/tiny overlap → `insufficient_overlap` · tie ladders must not fabricate distinct ranks ·
delta crossing zero renders unclamped · a player in one source only never appears with an imputed
rank · banned-language scan on all payloads · `decision_supported=False` recursive · snapshot
replay: same inputs → byte-identical artifact · vintage-series append never rewrites history.

## 6. Sequencing note

Phase A's framing v2 is the next concrete artifact (it also discharges David's #3). B can draft in
parallel as spec work but lands only after A (its fixtures come from A's first real drop record).
C blocks on A+B. D blocks on C + David.

**PLEASE CHALLENGE (Codex): the §4 open parameters, the phase boundaries (especially B's fixture
dependency on A), whether Phase C's store placement threatens the market-overlay cordon, and any
place this plan pre-decides what is David's.**
