# Footballguys `adp.csv` — identity resolution measured, and it fails silently

Date: 2026-08-09 · Claude (implementing lane) · **Layer 1 (ingest) / Layer 2 (curate — identity)**
Scope: **read-only measurement.** No repository mutation, no store, no intake, no code landed.
Addendum to `footballguys_adp_pilot_framing_claude_v1.md` (framing v1, under Codex review).
Method: the **production** `IdentityIndex.from_governed_crosswalk()` — `01` §Identity Resolution
bars inventing a parallel resolution path, so none was written.

---

## 1. The finding

A naive PFR-id join of this file **silently attaches market ranks to the wrong players**, and it
does so most often at the **top** of the board.

The governed crosswalk is `app/data/identity/_runs/ff_playerids_20260516.json`
(`nflreadpy.load_ff_playerids`, pull `2026-05-16T03:28:22Z`, 7,952 entries, 7,768 clean
`pfr_id → gsis_id`, 3 held conflicts).

| Outcome for the 608 rows | n | note |
| :-- | --: | :-- |
| Crosswalk **accepted** the id (reads as "resolved") | **453** | |
| ‣ name agrees with Footballguys' own name | 359 | true match |
| ‣ nickname/spelling variant, same human | 5 | Gainwell, Okonkwo, Tinsley, Borregales, Hibner |
| ‣ **WRONG HUMAN** | **34** | **7.5% of everything the crosswalk accepted** |
| ‣ **unverifiable** — id absent from `projections.csv`, no name to check against | **55** | could contain more |
| Crosswalk rejected (`source_only`) | 155 | includes 32 team-DST pseudo-ids (`htxxxx99`, `ramxxx99`, …) |
| Held conflicts | 0 | |

**The wrong matches concentrate where the money is:**

| Consensus rank window | wrong-human rows |
| :-- | :-- |
| top 25 | **3** |
| top 50 | **7** |
| top 100 | **12** |
| top 200 | 16 |

**Rank 1 of the entire file is wrong.** `GibbJa00` — first overall in every populated market —
is Jahmyr Gibbs to Footballguys and resolves in our crosswalk to **Jack Gibbens**, a linebacker.
Others, unabridged at the top: Jaxon Smith-Njigba → Jared Smith (#5) · Christian McCaffrey →
Chris McCain (#6) · Josh Allen → Jonathan Allen (#27) · DeVonta Smith → Devin Smith (#29) ·
Emeka Egbuka → Emeke Egbule (#34) · TreVeyon Henderson → **Trey Hendrickson**, a defensive end
(#50) · Marvin Harrison Jr. → Maurice Harris (#66) · Brian Thomas Jr. → Brandon Thompson (#67).

## 2. Why it happens, and why nothing catches it

A PFR id is a name stem plus a **disambiguation counter** (`GibbJa00`, `GibbJa01`). The stem is
derived from the name; the counter is assigned by whoever built the id space. **Footballguys'
counter does not agree with Pro-Football-Reference's.** Measured pairs: Breece Hall is `HallBr01`
to them and `HallBr03` to us; Josh Jacobs `JacoJo00` vs `JacoJo01`; Jordan Love `LoveJo01` vs
`LoveJo03`; Jayden Reed `ReedJa01` vs `ReedJa03`; Jahmyr Gibbs `GibbJa00` vs `GibbJa01`.

The divergence is **worst for recent entrants**, because counters are handed out in career order and
the two id spaces were populated at different times — which is precisely why the damage lands on
young high-value dynasty assets rather than on veterans.

**No existing guard fires.** The crosswalk's conflict mechanism holds ids that map to *two* players;
these map cleanly to *one* — the wrong one. A false match is indistinguishable from a true one at
the id layer, so `identity_status = canonical_resolved` is returned with full confidence.

**And `adp.csv` cannot detect it from inside the pilot's declared scope.** The file's only
non-market column is `id`: no name, no team, no position. The 34 above are provable **only** because
`projections.csv` — a file the framing explicitly placed out of scope — carries `first`, `last`,
`pos`, `team` in the same id space. The 55 unverifiable rows are unverifiable for exactly this
reason. **A one-file intake of `adp.csv` has no way to know it is wrong.**

## 3. Consequences

1. **The predecessor investigation's identity claim is FALSE and is withdrawn.**
   `footballguys_web_only_data_investigation_claude_v1.md` §2 states the PFR-style id makes this
   *"a join we already know how to do, not a fuzzy-name problem."* It is a fuzzy-name problem
   wearing an id's clothing — the worst shape, because it presents as exact. **I wrote that claim;
   I am withdrawing it.**
2. **Framing v1 seed F8 is insufficient as written.** It asks for resolved/608 with the unresolved
   listed. That measures the 155 and would have reported **453 resolved and looked healthy** while
   34 rows pointed at the wrong human. **A resolution count is not a correctness measure.** F8 must
   require an independent attribute check (name + position + team) on every accepted id, with
   accepted-but-unverifiable counted as its own third state — never folded into "resolved".
3. **Any name-stem id from a third party carries this class.** Recorded as a general finding, not
   opened as work. The repo's own `snap_counts` PFR join is **not** implicated by this measurement —
   it consumes nflverse ids from the same family that built the crosswalk — and this artifact makes
   **no claim** about it beyond that it was not tested here.
4. **This lands on layers 1–2, not on the pilot.** The pilot is the messenger.

## 4. Bearing on whether the pilot proceeds

Combined with the framing's headline — the file carries **ranks, not prices** — the honest position
is that the two decisive facts are now both measured and both negative, **before any code was
written**:

- the signal is an ordering, so it competes directly with `dynastyprocess_ecr_2qb`, the comparison
  that returned Spearman .99 and got `ff_rankings` ruled `blocked_for_use`; and
- the join needed to use it is **7.5% wrong on accepted rows and 12-in-100 wrong at the top**,
  requiring a second file to detect at all.

My lane position: **do not build intake yet.** The redundancy check (F10) and a corrected identity
protocol are read-only measurements that can settle whether anything here is worth landing.
**Codex owns the ruling; this is my read, not a decision, and no build is authorized regardless.**

## 5. Reproduction

Governed crosswalk `app/data/identity/_runs/ff_playerids_20260516.json`; source
`DraftDominator.app/Contents/Resources/adp.csv` from `~/Downloads/DraftDominator_v2026i.zip`,
30,388 bytes, SHA-256 `1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9`
(independently reproduced by Codex this session), plus `projections.csv` (1,546 rows × 65 columns)
as the name key. Resolution via `IdentityIndex.resolve(id, kind="pfr")`.

**Stated limits.** The 5 nickname exclusions are a hand-verified whitelist, so the wrong-human count
is **conservative by construction** — reclassifying any of them raises 34, never lowers it. The 55
unverifiable rows are excluded from the numerator, so the true rate may be higher. Name comparison
normalizes case, punctuation, diacritics and generational suffixes. **Nothing here tests position or
team**, which would tighten the check further and is what §3.2 asks F8 to require.
