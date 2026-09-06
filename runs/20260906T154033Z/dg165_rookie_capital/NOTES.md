# DG-165 — notes on the round-2 candidate (prose; every statistic lives in REPORT.md / EVALUATION.md / CALIBRATION.md)

This run answers REVIEW-2026-09-06-ROUND2.md (lane 24974) item by item. Research candidate: not served, not
promoted, not merged; nothing under `app/data` was written.

## Qualification inside appearance, by arithmetic (item 2)

Round one's hazards made cumulative probabilities monotone but still let a season's qualification probability
exceed its appearance probability on a handful of historical rows at the extremes. Each season is now a step of
a three-state chain — never appeared, appeared without qualifying, qualified before — with an appearance
transition per state and a qualification transition fitted only on the appearers of that state. A qualifying
season can only occur inside an appearance, the cumulative "qualified by h" is a state whose mass can only come
from appearances, and the expected count of qualifying seasons is bounded below by the probability of at least
one. The runner counts every such bound on every historical row and refuses to write a run that violates one;
the review's counterexample rows are in the test suite as probes.

## The policy is declared, not discovered (item 1)

Round one compared two arms on the outer years and published the winner's evaluation as if the outer years
were independent evidence. The scoring policy is now declared before anything is evaluated: inside each
training window, the three most recent complete classes choose among a fixed menu (plain; a linear class-year
term; the same plus a first-round-quarterback indicator) by a rule written down in advance. The outer evaluation
of that policy is the canonical evidence and is the same procedure final scoring runs. The plain model is
evaluated beside it as an exploratory comparison, with a paired bootstrap that bounds the difference on the
same test rows, and it is labelled exploratory. Nothing chooses among arms on the outer years, and the
"five of six metrics" phrasing is gone.

## The quarterback question, assessed and not corrected (item 3)

The calibration assessment separates appearance error from conditional-points error among appearers, by
position, draft band, era and season, each with a resampled interval. The recent-era shortfall is concentrated
in first-round quarterbacks' conditional points, not in whether they appear; the interval on that cell is wide
and it rests on a few dozen players. No offset is applied anywhere. The only route by which a quarterback-specific
term can enter the forecast is the inner-window policy, whose menu now contains that variant; in the final
window it tied the plain trend on validation wins and lost the tie-break, so the scored file carries no
quarterback-specific term. That is the evidence-driven outcome, reported as such.

## Affirmative identifiers (item 4)

The manifest states the declared policy, the scoring arm identifier and every output file's hash; the
evaluation states its policy identifier and the arm identifiers it evaluated; every scored row carries the
policy, the arm identifier and the hash of the evaluation it pairs with. A pairing check runs before the
manifest is written and raises on any disagreement; its passing block is in the manifest. A consumer can now
prove the pairing from identifiers rather than infer it from prose.

## What this run does not do

- It does not model undrafted rookies; there is no defensible population table.
- It does not say what a rookie is worth; replacement, lineup policy and discount are the ranking lane's.
- It does not correct the first-round quarterback shortfall; it measures it and lets the declared policy decide.
- It does not claim a trading edge.

## Where to look

REPORT.md (rendered record) · EVALUATION.md · CALIBRATION.md · policy_comparison.json · evaluation_exploratory_plain.json
· sensitivity_unresolved_as_zero.json · cohort.csv · manifest.json (identifiers, pairing block, output hashes).
