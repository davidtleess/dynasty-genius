# Dynasty Genius — Proposed Amendments to Product Law

**Date:** 2026-08-20
**Status:** PROPOSED. Nothing applied. Product law is David's to set.
**Basis:** the 127-rule product law audit (`2026-08-20-dg-product-law-audit.md`), its 52 recommended
changes and 13-rule keep list, and both adversarial challenges.

---

## 1. The argument

David asked whether "buy this player" should really be banned. **No — and the reason is stronger than
convenience.**

```
The goal is decision_supported — knowing the product's calls are worth acting on.
  ↓ requires  evidence that its decisions were good
  ↓ requires  graded decisions
  ↓ requires  recorded decisions
  ↓ requires  the product to actually make one
```

**The no-verdict law forbids the last step, so the first can never happen.**

**Verified 2026-08-20:** there is **no decision ledger anywhere in the repository** — zero files
matching `decision_ledger` / `decision_receipt` / `decision_capture`. The realized-outcome scorer
grades *predictions* (captured player forecasts) and has no concept of a decision. The product has
never made a recommendation and has nowhere to put one.

So the law is not merely costing convenience. **It starves the accountability loop that is the entire
moat.** Every judgment David makes happens in his head, where it leaves no record, earns no track
record, and can never be scored.

Second reason, specific to this product: the no-verdict line protects a user who might over-trust an
unproven model. **David is the only user and knows this system's limits better than anyone** — he
spent a full session finding them. The rule defends him from a naivety he does not have, at the cost
of the data he most needs.

But the danger it points at is real: a confident "sell" from a model that loses to free consensus on
3 of 4 QB folds would be actively harmful. So the amendment is not *allow verdicts*. It is:

> **The product may recommend — if and only if every recommendation is recorded, claim-levelled, and
> displayed beside the standing record of how recommendations at that level have actually done.
> Verdict, receipt and scoreboard travel together, or there is no verdict.**

That converts the verdict from the thing the architecture fears into **the thing the architecture
measures**.

---

## 2. What it looks like day one (ledger empty, nothing proven)

```
Sell Puka Nacua                                    [diagnostic]
model 71.4 xVAR · market 78.2 · band crossed 3d ago
basis engine_b@a3f91c · spec 7d2e · interval ±11.8
─────────────────────────────────────────────────────────────
Track record for diagnostic sells: 0 graded, 4 pending,
first grades ~Nov 2026. This engine currently loses to free
ECR consensus on 3 of 4 QB folds and is tied at WR.
Counter-argument: target share up 6 pts since wk2; the model
does not see the Week 4 role change.
```

Nothing overclaims. And the moment it renders, **a ledger row starts accruing toward an answer.**

---

## 3. The amendments

### A1 — The Recommendation Amendment
The product may state a recommended action. Every recommendation must carry: action · basis receipt ·
`as_of` · claim level · interval · mandatory counter-argument. Emitting one **writes an append-only
decision-ledger row at display time.** Presentation is governed by claim level, never suppressed by
vocabulary. **A recommendation that cannot show its record does not render — that is the only gate.**

**Repeals:** the blanket no-verdict line · banned standalone words (`buy`, `sell`, `hold`, `cut`,
`start`, `target`) · the 25 banned phrases · `banned_fields` incl. `recommended_action`.

### A2 — Check things, not words
Every rule inspecting *language* is repealed and replaced by one inspecting *structure*. All 13
surviving rules check a thing; every casualty checked a word. Proof: the vocabulary filter
**suppressed 10 of 12 honest bear cases and passed 17 of 17 real verdicts.** It is inverted, and it
deletes the counter-argument the constitution makes mandatory, for saying "depth chart."

**Repeals:** the runtime vocabulary filter on counter-arguments/evidence entirely; the AST scanner
survives only as non-blocking advisory.

### A3 — A rule must name its danger
Every rule names, in one sentence, the concrete failure it prevents and the mechanism that catches it.
**Any rule that cannot is repealed.** New rules ship with that sentence or do not ship. This is what
would have caught the composite-score ban (Ruling 10) before it nearly cost cross-positional
comparison. Cheapest amendment here and the one that stops the silt returning.

### A4 — Prohibitions ship with their permissions
No amendment lands its restricting half without its enabling half. **Applied retroactively:** the
2026-07-14 calibrated-tier ruling was issued to *relax* a ban; its prohibition shipped in full and now
reaches further than what it replaced, while the calibration producer was never built (zero hits
repo-wide). **That prohibition is suspended** until its permission exists.

### A5 — The diagnostic lane
Exploratory columns may exist in the assembled dataset behind an explicit diagnostic flag, leakage
protection intact, results structurally unable to reach a product surface. Today adding one column
requires a promotion-shaped edit *plus* rewriting the test asserting nothing may change. **Predicted
bypass: a scratch notebook with zero leakage protection** — ungoverned work wearing a governed face.

### A6 — Repeal the market denylist; keep the closed-world contract
Measured: every position intersects both prohibited lists at `[]`. The X matrix is built closed-world
by intersection, so the denylist **cannot fire where the model is.** Zero model safety bought; its
whole live effect is blocking a comparator column *alongside* features. Keep the contract, drop the
layer, fix the regex that blocks `value_over_replacement` / `market_share_yds` while passing
`sleeper_adp` / `fantasycalc_value`.

### A7 — Honest speech is never suppressible
No mechanism may delete, truncate or silently replace a caveat, counter-argument, limitation or
uncertainty statement. Failures are loud at build time, never quiet at render time. Today a suppressed
caveat and an absent one are indistinguishable on screen — the most dangerous possible failure for a
product whose thesis is that you can see where every claim came from.

---

## 4. What does NOT change

**REFUSED — do not drop `CI_WIDTH_MAX`.** The audit recommended it; the guardian checked the shipped
artifacts. Claimed benefit is zero (TE ships VALIDATED either way). Cost: it is the *sole* reason QB is
PROVISIONAL, and dropping it certifies a model that **loses to free ECR on 3 of 4 folds.**

| Stays or tightens | Why |
|---|---|
| Market never in model features | Enforced by the closed-world contract — the mechanism that works. Denylist goes; wall stays. |
| Temporal leakage guards | Highest-consequence defect. **Tightens** — name regex becomes a lineage check. |
| Point-in-time truth, append-only | The archive is the moat; holes are permanent and already opening. |
| Mandatory counter-argument | **Tightens** — A7 makes it unsuppressible, which it currently is not. |
| Claim level governs presentation | New, load-bearing. It is what makes A1 safe. |

**Fix first:** all 16 model-vs-market CIs straddle zero by 10–50× the effect, and ~80% of that width
traces to a **bootstrap implementation bug**, not real uncertainty. Until fixed, every claim-level
decision rests on intervals that are mostly artifact. This may move more than every amendment combined.

---

## 5. Order of operations

1. **A3** — one sentence per rule; prevents the silt returning.
2. **A7, A2** — pure deletions; immediately stop the product suppressing its own analysis.
3. **Bootstrap fix** — changes what every subsequent claim level means.
4. **A5** — so experiments can run while the rest is built.
5. **A6**.
6. **A1 last, deliberately** — needs the decision ledger, claim ladder and track-record surface to
   exist first. But it is the amendment the others are for. **Every day A1 is not shipped is a day the
   ledger does not accrue, and the ledger is the only road to `decision_supported`.**
