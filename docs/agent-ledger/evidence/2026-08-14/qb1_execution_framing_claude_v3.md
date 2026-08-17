# QB-1 Study Execution — Framing v3 + round-2 disposition (Claude, 2026-08-14)

**Cycle:** TW14-QB1-1 (run now ACTIVE; framing rounds 1–2 ran pre-run and are carried into
the run record as `finding-framing-1-1..3`). **Supersedes:** v2 (`cbd7bb34…`) on the three
found matters; v2 stands otherwise. **Folds:** Codex round-2 review
(`qb1_execution_framing_review_codex_v2.md`, `830a2b7d…`) — B1, B2, W1 ALL ACCEPTED.
**Scorer prerequisite:** SATISFIED — corrected commit `17cfc1e` audited CLEAR (`bfdd6b65…`);
that loop is closed.

## Dispositions

- **QB-R2-B1 — ACCEPT; the fetch gate goes to David as ONE explicit decision, all seven
  datasets named.** Measured 0/7: no existing local store passes the registration's §11
  admission gates for any pinned dataset (legacy-store substitution barred, as ruled in
  round 1). Therefore the D1 build requires provider fetches for ALL SEVEN via nflreadpy
  (public, free, read-only): weekly stats · seasonal/CPOE summaries · play-by-play (for
  EPA/proe aggregates) · rosters · schedules-adjacent weekly qualifying rows · draft picks
  · player attributes (cross-check only). The decision packet below puts this to David as a
  single yes/no with per-dataset scope; NO fetch occurs before his word; if run before data
  exists the runner refuses `source_unavailable` by registered rule.
- **QB-R2-B2 — ACCEPT; the registered consequence is stated to David BEFORE he spends the
  fetch word, not discovered after.** Codex's advisory pre-measurement of the FROZEN F32
  name-reconciliation gate against the real four snapshots: fold mismatch rates
  **2.60% / 2.94% / 2.33% / 0.00%**. The registered rule (>2% → `join_reconciliation_failed`,
  fold excluded from H5 primaries, **by rule, not judgment**) excludes three of four folds
  → the ≥3-of-4 H5 fold floor is unmet → **every H5 contrast (11–14) lands
  `unsupported_power`** — a REGISTERED, honest outcome ("not a failure" — §7). What this
  framing does and does not do about it, stated plainly:
  - The runner still computes and reports the full H5 lane (reconciliation triage lists,
    coverage, the mandatory margin-sensitivity readout where computable) — the registered
    disclosures are mandatory regardless of status.
  - **No gate tuning, no normalization "improvements," no threshold relaxation** — every
    such move is the forking path the pre-registration exists to forbid, and voids the pin.
  - The pre-measurement is ADVISORY: the binding numbers are the runner's own, computed by
    the registered procedure at execution. If they differ, the registered rule fires on
    them, whichever way they fall.
  - **The study's core value is unaffected:** contrasts 1–10 (the model lanes vs naive and
    vs each other — including H2 rushing, the hypothesis David most wants tested) do not
    touch F32 or the H5 fold floor.
- **QB-R2-W1 — ACCEPT.** The `backup_manifest.json` entry covering
  `app/data/backtest/qb_validation/raw` (the dp_values child included) lands in the SAME
  change set that populates the store — the landing-order law, path now exact.

## Decision packet for David (via Tower) — one gate, honestly framed

**THE ASK:** authorize the seven-dataset D1 fetch (nflreadpy, public/free/read-only, one
build pass writing raw snapshots under the frozen root `app/data/backtest/qb_validation/`).
Without it the study cannot run at all (local substrate is 0/7).

**KNOW BEFORE SAYING YES:** on current evidence the H5 market lane will likely report
`unsupported_power` by the registration's own frozen identity-reconciliation rule (three of
four market folds breach the pinned 2% gate). That is the pre-registration refusing to
compare against a market lane whose player-identity mapping it cannot verify — the honest
behavior, pinned before any result existed. **The heart of the study — the ten model-lane
contrasts, including whether rushing (H2) really is the best single QB factor — is fully
powered and unaffected.** If the H5 lane's power matters enough to fix, the fix is a
FUTURE, separately-registered identity improvement — never an in-flight tune.

## Standing

Registered values untouched · H2 UNDER TEST until execution + David's ruling · no fetch
before the gate word · no push · commits via gate paths · `decision_supported=False`
recursively · H5 language "keeps up with expert rankings," never "beats the market."
