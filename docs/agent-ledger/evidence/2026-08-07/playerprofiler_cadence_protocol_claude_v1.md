# Closing the PlayerProfiler source clock — the protocol, and who can execute it

**Author:** Claude Code, implementing lane · **Layer:** Layer 1 (ingest)
**Occasion:** David said *"ok do it"* against my statement that closing this clock needs his word to
authorize a forward observation protocol.

---

## 0. STOP — the thing I asked him to authorize is not a thing I can execute

**I was wrong about the shape of the gate, and the correction matters more than the protocol.** I
described the blocker as *authorization* for a forward capture. **It is not an authorization gate. It
is a capability gap.** Authorizing me changes nothing, because **no automated retrieval path exists.**

**Measured, read-only, no network calls made:**

| Fact | Evidence |
| :-- | :-- |
| The ingest path consumes **files David downloads by hand** | `scripts/run_playerprofiler_roster_ingest.py:7` — usage is `--exports ~/Downloads`; `:42` `--exports` is a path list |
| **No live HTTP client exists** anywhere in the PlayerProfiler modules | `rg` for `httpx`/`requests.`/`urllib` across `src/dynasty_genius/playerprofiler*.py` and `scripts/run_playerprofiler*.py` → **zero hits** |
| The old shadow route is **dead and was never sanctioned** | `src/dynasty_genius/playerprofiler.py:12-17` — it posted to an unauthenticated `wp-admin/admin-ajax.php`, returned **874 parse errors out of 874 players**, and that endpoint now answers **HTTP 400 body `0`**: the action is no longer registered. **It never used David's credentials at all** |
| The sanctioned path is stated in the module itself | *"The sanctioned path is the product's own export button… No scripted login, no terms-of-service exposure, no account risk."* |

**Consequence.** The only way to obtain a second observation of the same PlayerProfiler content is
**David exporting it again from his own subscription.** No word he gives me produces that. Writing an
automated fetcher would mean reviving a scripted path the codebase deliberately refused on
terms-of-service grounds — **so I am not proposing one, and "ok do it" is not read as asking for one.**

**⚠ Separately noted, not acted on:** `scripts/probe_playerprofiler.py` — the dead, never-sanctioned
shadow probe — **is still present in the repo.** Recorded as an inventory fact. **Removing it is a
separate decision and is not taken here.**

---

## 1. What David would actually have to do

**One action, repeated.** Export the **same** PlayerProfiler report he already exports, on a fixed
clock, and drop each file in a distinct folder. Nothing else changes.

| Step | Detail |
| :-- | :-- |
| **Which report** | The **Data Analysis / `player_season`** export — the one with the widest coverage and the one whose freshness matters most downstream |
| **How many** | **Minimum 3 exports → 2 intervals.** Two exports give one binary observation, which the open-clocks artifact already establishes is **non-diagnostic** |
| **Spacing** | **Weekly**, and the reason is stated rather than assumed: weekly is the finest cadence that is **cheap for David** and **coarse enough to be informative**. It bounds the answer to "changes at least weekly" vs "does not" — **it cannot resolve anything faster than weekly**, and this protocol does not pretend otherwise |
| **Where** | Any folder outside the repo. **The raw exports are private subscriber data**: they stay gitignored and outside the repo, and **only content hashes and derived features may ever travel** — the existing rule, unchanged |
| **What I do** | Hash each export and compare. Nothing else — no ingest, no store mutation, no consumer, unless separately authorized |

---

## 2. What the result would and would not establish

**Would establish:** whether the provider's `player_season` content changed across each observed
weekly interval — a **lower-resolution bound** on publication rhythm, measured **in the season phase
the exports fall in**.

**Would NOT establish, stated up front so the result cannot be over-read later:**

1. **Any cadence finer than the sampling interval.** Weekly sampling cannot detect daily publication.
2. **Anything about a different season phase.** The current window is **off-season**; PlayerProfiler's
   in-season rhythm is a separate question needing in-season exports.
3. **A publication *schedule*.** Observed change is evidence of change, not of a provider's declared
   or committed cadence — the R3 distinction the catalog already enforces.
4. **That no-change means static.** A no-change interval is weak evidence and, with few intervals,
   **non-diagnostic** — the exact F2 correction from the open-clocks artifact, and it applies here
   with equal force.
5. **Anything about the other three streams.** `medical_history`, `roster_week`, `pbp` have their own
   export paths and would each need their own series.

---

## 3. Boundaries

- **This document authorizes nothing.** It is a procedure description. No capture, scheduler,
  consumer, store mutation, provider access or catalog edit follows from it.
- **A-C stays OPEN.** The PlayerProfiler source clock remains **`UNMEASURABLE from held evidence`**
  until a series exists, and **N19 remains OPEN** under §6A regardless of anything here.
- **No §1 checkbox moves.**
- **H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
