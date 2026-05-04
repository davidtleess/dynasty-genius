---
title: Prospect Verification Checklist
type: governance
framework_protocol: 1 (Verify Status) + Anti-Speed Protocol
last_updated: 2026-05-03
status: v1 — active guardrail
applies_to: any operation that asserts a specific player's draft-class eligibility (anchors writes, class-tracker entries, demo trades, strategy doc references)
---

# Prospect Verification Checklist

## Purpose

Prevent the **"already-in-the-NFL prospect"** error class. This session has surfaced two near-misses in adjacent messages — Travis Hunter and Will Campbell, both proposed as 2027 prospects when both had been drafted into the NFL in 2025. Either insertion would have corrupted `gen_alpha.gold.anchors` with a fictional prospect and propagated to every downstream valuation and trade pitch.

**One Hunter-class error in production = one trade pitch built on a phantom asset = one credibility-destroying real trade with a leaguemate.** This checklist is cheap insurance against that.

## The Check (60 seconds, 3 questions)

Before adding any player to `gen_alpha.gold.anchors`, [`docs/class-trackers/`](../class-trackers/), a strategy doc, or a demo flow, the proposing agent must affirm all three:

### Q1 — Current college roster?
**Is the player listed on a current college program's official roster page for the season immediately preceding their claimed draft year?**

- For 2027 draft prospects: must appear on a 2026 college roster
- For 2028 draft prospects: must appear on a 2026 or 2027 college roster

**Failure mode if skipped:** Travis Hunter (drafted 2025, no 2026 college roster).

### Q2 — Draft declaration status?
**Has the player declared for, been drafted in, or signed as an UDFA into any NFL Draft prior to the claimed class year?**

If yes: the player is **not** a prospect for the claimed year.

**Failure mode if skipped:** Will Campbell (drafted 2025 #4 overall by Patriots, plainly disqualified from being a 2027 prospect).

### Q3 — Eligibility-year math?
**Per NFL rule (3 years removed from high-school graduation), does the player's HS class place them in the claimed draft year?**

- HS class of 2024 → eligible 2027 NFL Draft (with normal progression)
- Reclassification (HS class 2025 enrolling early 2024) → eligible 2027 if 3-year rule met
- Redshirt or injury-delayed years → can extend, verify per case

**Failure mode if skipped:** A 2027-eligible prospect treated as 2026, or vice versa (e.g. the Ryan Williams 2027-vs-2028 ambiguity flagged in [class-trackers/2027.md](../class-trackers/2027.md) §6).

## When the Check Applies

| Operation | Check Required? |
|---|---|
| INSERT into `gen_alpha.gold.anchors` | **Yes — blocking** |
| Add player row to [`class-trackers/2027.md`](../class-trackers/2027.md) Generational Tier or analyst_notes table | **Yes — blocking** |
| Reference a player by class year in a strategy document (`docs/strategies/`) | **Yes — blocking** |
| Use a player in a demo / agent collaboration test | **Yes — blocking** |
| Quote a player in a trade pitch script (e.g., `2027_pick_accumulation.md` §3.4) | Yes — blocking on first mention |
| Updating an *existing* verified player's stats | No — eligibility already established |
| Discussing a player generally in conversation without writing to tree | No — but flag if uncertainty surfaces |

## How to Document the Check

When the check is run, log the verification source on the same line as the player entry.

**Acceptable as the *logged* source (Primary Data Anchors):**

- Official college program roster page (e.g. `ohiostatebuckeyes.com/sports/football/roster/...`, any `.edu` athletics roster)
- Pro Football Reference / Sports-Reference college pages
- 247Sports, On3, or Rivals recruiting profile
- A prior verified entry in [`class-trackers/`](../class-trackers/) — *transitive trust is allowed once a player has cleared the check*

**Wikipedia is a *background scratchpad tool only* — never the logged citation.** Per PM ruling (2026-05-03 "Hunter/Campbell Amendment"): Wikipedia is permitted for fast disambiguation while running the check (e.g. distinguishing two players with the same name), but the source written into the commit message, the SSoT row, or any audit field must be a Primary Data Anchor from the list above. Wikipedia is a tool, not a ledger.

**Non-acceptable as verification of any kind:** mock draft sites alone, dynasty content creators, betting-market odds, social media references.

## Failure Recovery

If a Hunter/Campbell-class error is detected post-write:

1. **Stop further writes** that depend on the corrupted row
2. Run a SELECT to confirm the actual current state of the affected table
3. Issue an UPDATE or DELETE per the row's strategic role (delete if pure phantom; UPDATE with corrected class year if real player misclassified)
4. Audit the change history (commit log + `last_updated` timestamps) for any cascaded valuations to revert
5. File the failure with root cause to the backlog so the checklist can be tightened

## Who Enforces

| Agent | Enforcement Role |
|---|---|
| **Claude Code (Local Dev)** | Runs the check on any local insert/draft before commit; refuses to author files that fail |
| **Codex (CI/CD)** | *Future:* lint check that flags any new player names in `docs/class-trackers/` or `gen_alpha.gold.anchors` migrations against a verified-prospects allowlist |
| **Genie (Workspace)** | Runs the check on any direct UI/notebook insert; surfaces verification source in commit message |
| **Gemini (PM)** | Names of prospects in PM directives are *not* exempt — Claude Code/Codex/Genie run the check on PM-named players too (this session has demonstrated PM directives can carry transcription drift) |

## Out of Scope

- Verifying a prospect's *projected draft slot* (that's mock-board work, not eligibility verification).
- Verifying college production stats (that's [`class-trackers/2027.md`](../class-trackers/2027.md) work — this checklist only verifies the player *belongs in the class at all*).
- Catching the same player under different name spellings (Williams vs. Coleman-Williams) — flagged separately as a deduplication concern in [class-trackers/2027.md](../class-trackers/2027.md) §6.

## Sources for Standard Reference

- NFL eligibility rule (3 years removed from HS): [NFL Operations](https://operations.nfl.com/journey-to-the-nfl/the-nfl-draft/the-rules-of-the-draft/)
- College football season-by-season rosters: each program's official athletics site
- Recruiting / class-of-HS verification: [247Sports](https://247sports.com/), [Rivals](https://rivals.com/)
