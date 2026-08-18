# Footballguys `adp_sleeper-sf` horizon — provider-authentic evidence report (Claude, v1)

Date: 2026-08-17 · Thread: `[w#fbg-horizon-1]` · Status: EVIDENCE ONLY — no semantic-state write, no adjudication performed. Per plan v2 §1 (`docs/agent-ledger/evidence/2026-08-10/footballguys_horizon_divergence_plan_claude_v2.md`), the horizon may be established only by provider-authentic evidence; adjudication is David's ruling after cockpit review.

## Pre-registered acceptance criterion (David's word, BEFORE this inspection — 19:23 ledger entry, verbatim there)

Eligibility for the comparison requires `horizon = dynasty_startup` (startup draft position = market read of current dynasty value). `seasonal_redraft` renders the field ineligible. Recorded before any evidence was read.

## Evidence source and provenance

All evidence below is read from INSIDE the retained first-capture object — no new provider contact, no store mutation:
- Retained archive: `app/data/footballguys/objects/d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c.zip` (receipt `77984aaf…`, offering `fbg-offering-2026-08-09-a`, retrieved 2026-08-09T04:02:50Z, David's own download).
- Members read (SHA-256 prefixes): app binary `DraftDominator.app/Contents/MacOS/DraftDominator` `d9bc9b2d9329fea1…` · `ReadMe.txt` `9a1237a33807bfca…` · `version.txt` `77842efa0f6db5d0…` · `adp.csv` (role-pinned in the receipt at `1f7afcbf…`).

## Provider-authentic facts (each independently re-derivable from the pinned bytes)

1. **The app's own UI vocabulary has exactly two Sleeper ADP sources.** The shipped binary's ADP-source picker string table reads: Bestball10s · CBS · Consensus · ESPN · MFL · NFFC · RTSports · **"Sleeper Dynasty"** · **"Sleeper Redraft"** · Underdog (byte offset ~6785993; strings verbatim). No other Sleeper label exists in the binary.
2. **The data ships five Sleeper columns** (`adp.csv` header): `adp_sleeper-1qb`, `adp_sleeper-1qb-rookie`, `adp_sleeper-redraft`, `adp_sleeper-sf`, `adp_sleeper-sf-rookie`.
3. **The format split (1QB/SF + rookie variants) exists ONLY on the non-redraft side.** There is exactly one `-redraft` column with no 1QB/SF/rookie variants.
4. **Coverage in the captured vintage (2026i, ADP updated to Aug 5 2026 per ReadMe):** `sleeper-sf` 500/608 populated (ranks 1–500 — the pilot's universe) · `sleeper-1qb` 435 · `sleeper-1qb-rookie` 66 · `sleeper-sf-rookie` 77 (rookie-class-sized pools; rookie drafts exist only in dynasty) · `sleeper-redraft` **0/608 — empty**.

## The inference step, stated honestly

The mapping "`adp_sleeper-sf` ↔ the UI's *Sleeper Dynasty* source under a Superflex league configuration" is a **structural inference over provider-authentic artifacts**, not a prose statement by the provider. The argument: with only two Sleeper labels in the app's vocabulary, the five columns must partition under them; `-redraft` is the sole candidate for "Sleeper Redraft"; the format-split family (1QB/SF/rookie) — including the dynasty-only rookie-draft constructs — is the "Sleeper Dynasty" family; in an SF league the app's Sleeper Dynasty ADP is therefore `adp_sleeper-sf`.

**Named counter-argument (steelman):** the column↔label mapping is positional in code, not name-tied (no `adp_sleeper` string exists in the binary), so conceivably "Sleeper Dynasty" consumes only `-1qb` and `-sf` is something unlabeled. Against this: no third Sleeper label exists for `-sf` to map to; "Sleeper Redraft" mapping to `-sf` would leave the empty `-redraft` column as its own source's data while redraft is the August use-case; and the `-sf-rookie` sibling is a dynasty-only construct sharing the `-sf` stem. The counter-argument is weakened but not byte-level eliminated; eliminating it fully would require decompiling the picker's column-index table or a provider documentation statement.

## What this evidence does NOT establish

- It does not adjudicate the horizon — that is David's ruling after independent review (plan v2 §1).
- Plan v2 §1 bars inference "from the empty `adp_sleeper-redraft` column" alone — fact 4's empty-column observation is corroboration context only, and carries no weight by itself.
- If adjudicated `dynasty_startup`, plan v2 §0 requires a fresh *startup-draft-vs-trade-price* framing before Phase C — the adjudication alone does not open it.

## Requested next steps

1. Codex adversarial review of this evidence chain (are the facts re-derivable; does the inference step survive attack; is the evidence sufficient for a §1 semantic contract entry, or is a decompilation/provider-doc step required first).
2. On review, the packet goes to David for the adjudication ruling.
3. Only after his ruling: the governed semantic-state write (its own cockpit cycle; the intake module's assertion/adjudication machinery is the write path, and it is not touched until then).
