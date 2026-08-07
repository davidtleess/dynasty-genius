# A-C closure-contract asymmetry — Codex ruling v2

**Reviewer:** Codex, independent reviewing lane  
**Layer:** Layer 1 ingestion inventory  
**Artifact:** `docs/agent-ledger/evidence/2026-08-07/ac_clock_closure_contract_asymmetry_claude_v1.md`  
**Reviewed SHA-256:** `7069c31cff4b9846bf3d0387c578c449818d48b74e4b6fbc66c0d4e8f2b14bca`

## Ruling

**Branch (b) holds under the current contract and evidence.** One qualification is load-bearing:
`continuous` / event-driven is admissible **in principle** as a source-publish value, but only when
it is independently verified as the measured upstream change rhythm or as authoritative endpoint
semantics. The label is not evidence for itself.

The current record does not independently establish N18's `continuous league state` or N12/N13's
`continuous league events`:

- `docs/strategies/2026-08-05-layer1-automatic-refresh-planning-v1.md` defines source-publish
  cadence as a measured upstream change rhythm or `UNVERIFIED`.
- `docs/layer-1-data-inventory-catalog.md` §6A/M4 requires independent verification or evidenced
  `N/A` / `not scheduled`; `UNVERIFIED` remains open.
- `docs/agent-ledger/evidence/2026-08-06/layer1_source_publish_cadence_codex_v1.md` pins nflverse
  clocks. Its non-nflverse Sleeper section proposes or retains **local checks**; it does not pin a
  Sleeper publication rhythm.

Therefore N19 remains source-publish `UNVERIFIED`, and N18 plus N12/N13 must also be treated as
source-publish `UNVERIFIED` unless a fresh evidence packet earns their event-driven
classifications. N14b inherits N12's clock and cannot be stronger than N12. N14 proper remains an
evidenced `N/A` because it is Dynasty Genius's capture ledger, not a provider source. The §6A C row
currently under-reports its open members. **No checkbox moves.**

## The row distinction

- **N12/N13** are discrete transaction-event records with `created` / `status_updated` semantics.
  That makes an event-driven classification plausible and likely cheaper to evidence, but
  plausibility does not satisfy M4.
- **N18** is a heterogeneous normalized bundle: league, rosters, users, traded picks, drafts, and
  the global player map. One blanket `continuous league state` value hides endpoint-specific
  clocks; the player-map documentation separately gives once-daily client polling advice.
- **N19** overlaps N18 but adds matchups and per-endpoint draft/pick history. Same provider is not
  the same endpoint set. The difference requires per-family evidence; it does not justify applying
  M4 only to N19.

## Measurement 1 admissibility

**Admissible only in bounded form.** On 2026-08-07 I independently inspected the current
`https://docs.sleeper.com/` API page (870 rendered lines). The `1000 API calls per minute` statement
and the players endpoint's `once per day at most` statement are client-polling guidance, not
server-side publication cadence. Page searches for `publish` and `update frequency` returned no
cadence declaration.

That supports this sentence:

> No server-side publication cadence was found on the inspected public Sleeper API page as of
> 2026-08-07.

It does **not** support `no such declaration exists` or `N19 cannot be closed by obtaining a Sleeper
declaration`. A direct provider answer or other support/subscriber material could still supply one,
exactly as the reviewed artifact's §4.5 concedes. The negative search forecloses only the inspected
public-page route.

The PlayerProfiler negative is likewise admissible only as the bounded result of the named public
search, not as proof that no declaration exists anywhere.

## Findings against v1 as written

### F1 — “every other clock” is overbroad

Section 1 says every other source-publish value was obtained from provider-published documentation
or scheduling configuration. Section 6E also contains non-nflverse descriptive values—including
N9/N10, N12/N13, N18, and manual/paid-source rows—that the independently cleared cadence artifact
did not establish as provider publication schedules. Narrow the claim to the B-row clocks actually
enumerated in the table, or inventory the exceptions explicitly.

### F2 — the absolute Sleeper negative contradicts the artifact's own bound

Section 2.1 says no Sleeper declaration exists and N19 cannot be closed by obtaining one. Section
4.5 correctly says a subscriber-facing help centre or direct provider answer could still carry a
declaration. Replace the absolute language with the bounded inspected-page sentence above.

Neither finding defeats the concrete divergence. Both prevent a negative public search from being
promoted into universal proof.

## Recommendations requested after the ruling

1. **Landing the evidence:** yes, after F1–F2 are repaired and the revised pin is reviewed. The
   divergence is real and belongs in the durable record. This is a recommendation, not commit or
   push authority.
2. **Sleeper response-header probe:** do not run it for this gate. A single response can describe
   transport/cache headers; it cannot establish an endpoint family's upstream change rhythm or
   publication SLA. This ruling creates no provider-call authority. If David separately authorizes
   a later probe, its result must remain bounded to the headers actually returned and cannot by
   itself close M4.
3. **PlayerProfiler protocol:** provide the written P1–P8 disposition before rewriting protocol
   v2. This ruling does not remove that protocol's need; it changes only the Sleeper-side catalog
   defect.

## Boundary

No catalog edit, checkbox movement, provider call, response-header probe, scheduler, capture, store
mutation, commit, or push is authorized or performed by this ruling. Both original clocks remain
open, and the additional under-reported Sleeper fields are findings pending reconciliation.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
