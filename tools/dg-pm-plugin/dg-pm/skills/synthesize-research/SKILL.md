---
name: synthesize-research
description: Synthesize Dynasty Genius research lanes into an evidence-graded brief. Use when pulling together multi-agent research (Claude/Codex/Gemini lanes), a UI-research corpus, edge-pattern investigations, or external sources into structured findings with evidence grades, falsification seeds, and a recommended cockpit next action.
argument-hint: "<research topic or question>"
---

# Synthesize research

> Sources are DG's research corpus and lanes — see [SOURCES.md](../../SOURCES.md). DG research is adversarial by design: independent lanes, cross-review, and evidence grading before anything becomes a plan.

Turn a pile of research — multi-agent lane outputs, `docs/strategies/` briefs, the UI-research corpus, edge-pattern probes, external reading — into a structured, evidence-graded synthesis that can seed a spec. The output is not a decision; it's the honest map a decision is made against.

## The DG research pattern

DG runs research in **independent lanes** (a Claude lane, a Codex lane, a Gemini product-edge lane) and then **cross-reviews** them adversarially before synthesizing. Preserve that structure:
- Keep lanes' findings attributed and separable — don't blend a Gemini product claim into a Codex technical finding.
- Surface where lanes **disagree**; disagreement is signal, not noise to smooth over.
- Gemini is **advisory/non-binding**: route its framing early, but its repo-state claims are void until verified, and Claude owns scope.

## Workflow

1. **Frame the question** — what decision will this synthesis inform? Name it so the synthesis stays scoped.
2. **Gather the lanes/sources** — read the actual lane docs / briefs / corpus. Note each source's date and nature (empirical probe, external article, opinion, model output).
3. **Extract themes** — cluster findings by theme. For each, note frequency (how many independent lanes/sources support it) and whether it's empirically grounded or asserted.
4. **Grade the evidence** — this is the core DG move:
   - **Validated** — reproduced/empirically supported in-repo.
   - **Provisional** — plausible, single-source or unreproduced.
   - **Hypothesis** — an idea worth testing, no support yet.
   The ladder (Hypothesis → Provisional → Validated) **never flips `decision_supported`**. A validated *research* finding is still not a running-software verdict.
5. **Falsify** — for each load-bearing finding, state what would refute it and the cheapest probe to test the riskiest one. A finding that can't be falsified isn't a finding yet.
6. **Verify repo-state claims** — any claim that "the code does X" or "PRODUCT.md says Y" gets checked against the actual file before it enters the synthesis. Cite as-of-fetch.

## Evidence rules (non-negotiable)

- **Cite as-of-fetch.** External data (market values, rankings, articles) is stamped with when it was pulled — it drifts.
- **Verify before relying.** Recalled memory and Gemini claims reflect what was true when written; confirm against the file/route/flag now.
- **Separate qualitative from quantitative**, then reconcile (DG's 65/35 quant-qual discipline). Neither silently overrides the other.
- **No overclaim.** Destination/vision language is legitimate; flag it the moment it claims the *current* model has arrived. Divergence/margin stays a hypothesis.

## Output

A synthesis brief:
- **Question** and scope.
- **Themes**, each with supporting lanes/sources and an evidence grade.
- **Disagreements** across lanes, unresolved.
- **Falsification seeds** — what would refute the key findings; the cheapest next probe.
- **Recommended next cockpit action** — usually "spec increment X" (`dg-pm:write-spec`) or "run probe Y," David-sequenced. Not a build authorization.

Write to `docs/strategies/YYYY-MM-DD-<slug>.md` when it's a keeper. Committing it is a David-authorized action.

## Tips

- The most valuable output is often a disagreement or an unverified claim you flagged — not the consensus.
- If every lane agrees frictionlessly, be suspicious: independent lanes rarely converge that cleanly without a shared blind spot.
- End at "here's the evidence-graded map and the cheapest next probe," not "here's what we should build." The build decision is David's, through the cockpit.
