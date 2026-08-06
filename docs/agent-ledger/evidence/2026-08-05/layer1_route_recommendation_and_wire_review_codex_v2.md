# Layer 1 route recommendation + WIRE-GEMINI-3 review — Codex v2

**Reviewed:** 2026-08-05 23:22 ET  
**Layer:** Layer 1 data foundation; cross-layer cockpit reliability  
**Recommendation artifact pin:** `31088036a3a7d259b8fd1c2bb80f15a623982f382015b27d0b44eba6454b2da2`  
**Wire code pin:** `0e4ad90d65490cf8c31c7d6f24a4391ffcb7a448abaa7e90486ee289370aad8a`  
**Wire test pin:** `5e10cfb0560ab29da1dea7a7913883b6585e400383be35fa7bf622c125b18354`  

## Verdicts

- **Artifact 1: NOT CLEAR as a completed three-lane recommendation.** The Option-A conclusion
  faithfully represents Codex's position, but the artifact contains two factual/attribution defects
  and explicitly lacks the Gemini recommendation David ordered.
- **Artifact 2: NOT CLEAR.** `LAST` is the correct direction relative to `FIRST`, but the fallback
  has two independently reproduced false-empty/overwrite paths because it accepts a closing border
  without proving the matching opening border and resolves the prompt from the last prompt-like
  input line.

## Artifact 1 findings

### A1 — HIGH: the required Gemini recommendation is absent

The artifact says Gemini received a facts-only prompt and gave no verdict. David later instructed
Codex directly to *"tell gemini to pressure test it and recommend something as well."* That is a
narrow, task-specific explicit David exception to Gemini's standing charter, not a permanent
restoration of review/CLEAR authority. The corrected request was delivered and positively verified
in Gemini's transcript as `[w#azmg33kj-1]`; the recommendation is pending. Until it lands, this is a
two-binding-lane recommendation plus Gemini telemetry, not the completed three-lane response David
requested.

### A2 — HIGH: "no raw snapshots of the five" is false for `snap_counts`

Fresh filesystem measurement found **129** `snap_counts_*.json` raw snapshots under
`app/data/nflverse_usage/raw`, totaling **1,120,520,543 bytes** (~1.04 GiB). The correct split is:

- `snap_counts`: canonical rows, export, and substantial raw JSON history already exist; the daily
  Feature Refresh still bypasses them.
- `player_stats`, `rosters`, `pbp`, `participation`: no equivalent governed raw capture exists.

This matters to retention: B4 is an existing inefficient representation to replace/reconcile, not a
blank raw-evidence lane.

### A3 — MEDIUM: the NGS precedent holds, but "David ruled this exact question" over-attributes

The repository precedent is real. Commit `1131d102` removed the live NGS calls from the same 09:15
job, routed it to the verified last-good local export, and recorded exact candidate parity. However,
the direct David wording preserved in the evidence was *"work with the team - go forward on all 4"*
after asking for a better design. The specific last-good route was the team's design under that
word, later committed and pushed on David's authority. Call it a **David-ratified repository
precedent**; the available record does not support saying David personally selected this exact
technical answer in those words.

### A4 — LOW: metadata and backup operands need one-line reconciliation

The artifact is filed under the 2026-08-05 ET session but says `Authored: 2026-08-06` without a UTC
label. Use `2026-08-05 ET` or label UTC explicitly. Also retain the requested distinction among the
1,994,594,012-byte retained staging read, the 2,203,656,626-byte failed-marker operand, and the live
recovery staging operand; they are different measurements, not a discrepancy.

## Artifact 2 findings

### W1 — HIGH: a closing border without an opening border false-READies ordinary history

Probe:

```text
ordinary history
>
────────────────────────────────────────
? for shortcuts Gemini
```

with Gemini profile and unusable cursor returns `PaneState.READY`, input region `">"`, and
`_visible_empty=True`. The new fallback treats the one rule below an ordinary bare history quote as
a composer close even though there is no opening border. Before the fallback this held fail-closed;
after it, a send may paste over a non-composer state.

Required control: the fallback must prove a structural **pair**, not merely `profile.bordered` plus
any last rule below a prompt-like line. The closing rule should match a real opening rule and the
prompt must be located inside that pair.

### W2 — HIGH: last prompt-like line can hide earlier multiline input

Probe:

```text
history
────────────────────────────────────────
> first line
>
────────────────────────────────────────
? for shortcuts Gemini
```

with unusable cursor returns input `">"`, `_visible_empty=True`, and moves `"> first line"` into
the conversation region. A user can legitimately paste a later bare Markdown quote line. Scanning
upward for the **last** prompt prefix chooses that continuation as the prompt and makes occupied
input look empty.

Required control: once the final composer border pair is proven, bind the prompt to the **first
prompt row after the opening border**, preserving every continuation through the closing border.
This must be tested on both usable- and unusable-cursor paths because the prompt locator is shared.

### W3 — LOW: the named extra-border residual has the wrong failure direction

If another border exists below the actual closing border, selecting the last border includes the
real close/footer/text between the borders in the input region. That produces a false refusal, not
a swallow. `LAST` is safer than `FIRST`, but only after W1/W2 establish the actual composer pair.

### W4 — HIGH, fresh repair audit: W2 composes with an interior border

The first W1/W2 repair selected the last two arbitrary borders and required a prompt between them.
That still swallows this occupied composer on both cursor paths:

```text
history
────────────────────────────────────────
> first line
────────────────────────────────
>
────────────────────────────────────────
? for shortcuts Gemini
```

It selects the 32-character interior rule plus the final closing rule as the pair, treats the later
bare `>` continuation as their prompt, moves `> first line` into conversation, and returns
`_visible_empty=True` for cursor `0` and cursor `4`. A candidate opening/closing pair must not be
the nearest arbitrary rules. Border signatures must match, and ambiguity must preserve the larger
possible input region (false-refuse) rather than discard it.

### W5 — HIGH, signature matching still swallows equal-width interior rules

The signature repair closes W4 only when the interior rule has a different width. With all three
rules identical, the same swallow remains on both cursor paths:

```text
history
────────────────────────────────────────
> first line
────────────────────────────────────────
>
────────────────────────────────────────
? for shortcuts Gemini
```

At the reviewed `dc77045…` pin, `split_regions` selects the nearest matching rule as the opening,
moves `> first line` into conversation, and reports `_visible_empty=True` at cursor `0` and cursor
`4`. The ambiguity must resolve toward the earliest same-signature candidate, or otherwise preserve
the earliest possible input and false-refuse. The measured six-character conversation separator is
not a counterexample to this narrower rule because it does not match the 97-character composer
signature.

The cursor-1 exclusion in the authored interior-rule test is consistent with the standing round-6
contract: rows below the actual cursor are chrome. The property test's name and prose are broader
than its proof, however—it checks that the prompt-line marker survives every cursor position, not
that every apparent continuation survives when the cursor is above it.

### W6 — HIGH, the unproven-pair fallback retains W2

W5 itself is closed at `4421e8e…`, but `split_regions` still binds the **last** prompt whenever a
border pair cannot be proven. The existing missing-closing-border topology composes with W2:

```text
history
────────────────────────────────────────
> first line
>
```

At cursor `0` and cursor `3`, the reviewed code returns only `>` as input, moves `> first line`
into conversation, and reports `_visible_empty=True`. This topology is already declared supported
by `test_wire_gemini_3_bordered_without_closing_border_holds_fail_closed`; that test's single empty
prompt cannot detect the continuation swallow. A complete 40-wide box followed by an unmatched
32-wide lower rule produces the same failure because last-border selection prevents pair proof.

Required direction: when a bordered pair is unproven, fail-closed must preserve the earliest
possible prompt/input rather than falling back to the last prompt. The no-closing and unmatched
lower-border variants require controls on usable and unusable cursor paths.

### W7 — HIGH, ordinary continuation defeats the W6 upward walk

At `d4c9a40…`, the no-pair walk crosses only border and prompt rows. A plain typed continuation
therefore stops it inside the composer:

```text
history
────────────────────────────────────────
> first line
second line
>
```

At cursor `0` and cursor `4`, only the bare `>` remains input; both typed lines move into
conversation and `_visible_empty=True`. The property matrix puts `cont` after the bare prompt, not
between the typed prompt and the later continuation prompt, so it does not exercise this placement.

The claimed hold/cursor asymmetry is also absent in the reviewed implementation: `region_start` is
widened before the cursor-usability branch and is shared by both paths. An unbordered Codex frame
`› quoted conversation / › ` at cursor `1` becomes falsely occupied, contradicting the stated
“unbordered cursor path unchanged” scope. The robust safety boundary is to hard-hold bordered frames
whose pair cannot be proven, while leaving the established unbordered cursor path separate.

### Chip semantics and the submit retry

- The one observed Gemini sample rejects blindly reusing Claude's `M+1` rule: the source file had
  21 newline-terminated records and the chip displayed `+21 lines`. It does **not** establish a
  general formula across leading/trailing-newline topologies. Keep Gemini `chip=False` until an
  isolated, sender-owned agy test pane measures controlled bodies of several lengths.
- Claude's single Enter was **inside** the sender-owned submit-retry carve-out: the composer was
  verified empty immediately before the helper's atomic paste, the new chip was paste `#1`, its
  advertised count matched the exact sent file for this sample, and only one Enter was sent. The
  chip count is not sufficient for automatic body verification, but the manual submit retry did not
  adopt or submit somebody else's strand.

## Independent checks

- Focused wire suites plus chip-profile suite: **215 passed, 1 skipped**.
- `git diff --check`: clean at the reviewed pins.
- The initial two adversarial probes and the fresh combined W4 probe reproduce outside the authored
  test set.
- Commit `9567fb4` contains Codex's three planning/evidence files at their exact prior pins. No
  revert is requested; the recommendation/catalog content remains subject to the findings above and
  the commit remains unpushed.

**Boundaries:** no code/test repair, commit, push, scheduler, capture, consumer, or model action is
authorized by this review. H2 QB rushing remains **UNDER TEST** with no result.
