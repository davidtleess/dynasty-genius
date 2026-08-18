# Footballguys `adp_sleeper-sf` horizon evidence-chain review — Codex v1

Date: 2026-08-17 ET
Reviewer: Codex, independent binding lane
Reviewed artifact: `docs/agent-ledger/evidence/2026-08-17/fbg_horizon_evidence_claude_v1.md`
Scope: retained-byte provenance and horizon identification only; no provider contact, semantic
write, adjudication, or Phase C work.

## Verdict

**NOT CLEAR for `horizon=dynasty_startup`: the retained facts reproduce, but
the exact-field mapping is not uniquely identified.**

The packet is sufficient to record the exact field with `horizon=unknown` and the pinned evidence
pointer under plan v2 §1. It is not sufficient to enter the eligible `dynasty_startup` value for
`adp_sleeper-sf`. One further provider-authentic binding step is required first: preferably a
static trace/decompilation of the retained binary proving the picker/configuration branch resolves
`Sleeper Dynasty` + Superflex to CSV column index 15 (`adp_sleeper-sf`) and does not resolve
`Sleeper Redraft` there; alternatively, captured provider documentation may explicitly bind the
exact field to Sleeper dynasty-startup Superflex ADP. The evidence must carry hash and retrieval
provenance.

David's 19:23 criterion remains the pre-registered eligibility rule. This review does not apply
that rule or adjudicate the horizon.

## Provenance re-derivation

- Retained object exists read-only at
  `app/data/footballguys/objects/d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c.zip`.
- Size: 8,540,590 bytes. SHA-256:
  `d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c`.
- Read-only receipt row independently returns:
  - receipt `77984aafe1052e8c7b9649a32ba16e9c7e2a3c1877cfa8cd05367451fe5d316c`;
  - source `footballguys`, offering `fbg-offering-2026-08-09-a`;
  - retrieved `2026-08-09T04:02:50Z`;
  - the same archive hash and size;
  - content vintage `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`;
  - `retained`, `review_required`, `analysis_ready=0`.
- Member SHA-256 values reproduce exactly:
  - binary `d9bc9b2d9329fea149e1c08bf9ef2b2dbaf34c7d702471838898c866e9784c0f`;
  - `ReadMe.txt` `9a1237a33807bfcad8342169e0ec780fbcdfa310812477a68bdfb87ff83032d6`;
  - `version.txt` `77842efa0f6db5d0f54f692b3a58ef6ee892b9cb852ab965a3eafaa5f0de5e77`;
  - `adp.csv` `1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9`.

## Fact-by-fact reproduction

### 1. Binary vocabulary — reproduced, with one precision qualification

`strings -a -n 3 -t d` over the retained Mach-O binary gives one contiguous sequence:

```text
6785944 Bestball10s
6785956 CBS
6785960 Consensus
6785970 ESPN
6785975 MFL
6785979 NFFC
6785984 RTSports
6785993 Sleeper Dynasty
6786009 Sleeper Redraft
6786025 Underdog
```

A raw case-insensitive binary count finds exactly two `Sleeper` occurrences, these two labels.
No `adp_sleeper` string exists in the binary. Therefore the provider-authentic vocabulary claim is
reproduced. Calling the sequence the exact runtime picker-to-column table is not yet proven by
string presence alone; that control-flow claim is the missing binding step.

### 2. CSV header — reproduced

`adp.csv` has 608 data rows and 19 columns. Its Sleeper fields, in exact order, are:

```text
adp_sleeper-1qb
adp_sleeper-1qb-rookie
adp_sleeper-redraft
adp_sleeper-sf
adp_sleeper-sf-rookie
```

Archive-wide byte search finds `adp_sleeper` only in `adp.csv`; the two UI labels occur only in the
binary. No second captured artifact directly ties either label to a field.

### 3. Header topology — reproduced as syntax, not as horizon semantics

There is exactly one field containing `-redraft`; the `1qb` and `sf` stems each have a rookie
variant. That is a provider-authentic header fact. The conclusion that these four fields therefore
form the `Sleeper Dynasty` runtime family is an inference about grouping/control flow, not a field
name or UI metadata statement. Plan v2 §1 explicitly bars filename-based horizon inference, so the
header topology can support but cannot by itself close the exact-field contract.

### 4. Coverage and version — reproduced

| Field | Populated / 608 | Rank shape |
|---|---:|---|
| `adp_sleeper-1qb` | 435 | unique integral 1–435 |
| `adp_sleeper-1qb-rookie` | 66 | unique integral 1–66 |
| `adp_sleeper-redraft` | 0 | empty |
| `adp_sleeper-sf` | 500 | unique integral 1–500 |
| `adp_sleeper-sf-rookie` | 77 | unique integral 1–77 |

`version.txt` is exactly `2026i`. The top `ReadMe.txt` block says Cross-Platform Draft Dominator
2026i and `Updated: ADP to Aug 5, 2026`. These facts establish vintage and coverage, not horizon.
The empty redraft field receives no semantic weight under plan v2 §1. The proposition that rookie
drafts are dynasty-only is not stated by the captured bytes; even accepted as domain context, the
rookie siblings do not uniquely establish the base `adp_sleeper-sf` branch.

## FBG-HZN-F1 — BLOCKER: label-to-column assignment is not unique

The packet's key premise is: because the binary has only two Sleeper labels, the five Sleeper
columns **must** partition under those labels, and the morphology forces `adp_sleeper-sf` under
`Sleeper Dynasty`. The first implication is not established by the retained artifacts.

The same contiguous UI vocabulary has 10 vendor labels, while `adp.csv` has 18 ADP fields. Five
populated non-Sleeper fields have no matching string anywhere in the binary:

| CSV field | Populated rows |
|---|---:|
| `adp_draftkings-bestball` | 405 |
| `adp_drafters` | 277 |
| `adp_fbgoc` | 250 |
| `adp_ffpc` | 250 |
| `adp_yahoo` | 218 |

Thus the visible string list is not an exhaustive one-label-per-column manifest. The absence of a
third Sleeper label cannot force every Sleeper column into the proposed two-way partition. A field
may be selected by league configuration or another positional branch without its own visible
label — exactly the possibility the named steelman raises.

At least one alternative remains consistent with all reproduced bytes: `adp_sleeper-sf` could be
chosen through a Superflex redraft/configuration branch, while the rookie-specific sibling is
chosen only in a rookie/dynasty mode. The header stem makes that less natural than Claude's proposed
mapping, but it does not make it impossible. Neither the empty `-redraft` column nor the 500-row
shape may eliminate the alternative under the frozen §1 rules.

## Steelman disposition

**The named steelman survives and is strengthened by the non-exhaustive label table.** Claude's
proposed mapping is the best-supported interpretation, but best-supported is not the same as a
provider-authenticated exact-field contract. The chain establishes plausibility, not uniqueness.

The smallest decisive proof is one of:

1. Static trace/decompilation against binary SHA `d9bc9b2d...` that identifies the relevant source
   selector and configuration branch and proves its final CSV column index/name for both
   `Sleeper Dynasty` and `Sleeper Redraft`; or
2. Provider documentation/UI metadata that explicitly names `adp_sleeper-sf` (or an unambiguous
   exported-field definition) as Sleeper dynasty-startup Superflex ADP, captured with hash and
   retrieval provenance.

Merely repeating the current string/header/count comparison, launching a numeric-shape study, or
using David's eligibility criterion as field evidence does not close FBG-HZN-F1.

## Scope and phase ruling

- The provider-authentic facts and provenance portions of Claude's packet are accepted with the
  precision qualifications above.
- The packet may support a plan-v2 §1 record with `horizon=unknown`; that state continues to close
  Phase C and bars horizon labels.
- It may not support `horizon=dynasty_startup` yet.
- No adjudication packet should go to David as if the factual horizon were closed. The missing
  binding step should be completed and independently reviewed first; David then adjudicates under
  his already-recorded criterion.
- No provider contact, semantic-state write, adjudication, or Phase C artifact was performed by
  this review.
