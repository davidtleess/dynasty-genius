# DG-165 — notes on the common-outcome refit (prose; every statistic lives in REPORT.md / EVALUATION.md / CALIBRATION.md)

This run refits the round-2 candidate on the COMMON outcome artifact (DG-179) so that both producers label from
identical outcomes. Research candidate: not served, not promoted, not merged; nothing under `app/data` was written.

## What changed with the common artifact

Labels no longer come from a private panel. Every appearance, season total, game count and qualification is
read from Codex's common player-season artifact, which the adapter loads fail-closed: the schema version, the
declared hash of the outcomes file against its bytes, the exact-league flag which must be false, a recognised
coverage status and every identity key are checked before a single label is built, and the manifest binds those
identities. The outcome target is the championship window — regular-season weeks one to sixteen through 2020 and
one to seventeen from 2021 — scored with nflverse's default PPR preset, which is explicitly not David's exact
league scoring; the manifest carries that caveat and the artifact's qualification note that matching game
coverage and a disclosed quarantine are not proof of perfect individual stats. Seasons the artifact does not
cover stay unknown, never zero, and the cohort is restricted explicitly to draft classes from 2001, with the two
dropped classes named. Cohort players are ranked at their draft role in every season and every other player at
his weekly position, so an offensive draftee listed as a defender today is never dropped. The historical
evaluation starts in 2008 by a rule stated before the run: the inner-window selection needs at least four
training classes at its inner cutoff. Metrics from the old target are not carried as validation of these labels.

## The round-2 construction, unchanged

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

## Positions: the draft table and the roster can disagree

The model's position term is the draft table's classification; a player can be listed one way on draft day
and play another (a 2026 fifth-round tight end is a fullback on his team's roster). The scored file therefore
carries both the draft-table position and the current nflverse players-table position, the manifest lists
every 2026 rookie whose two positions differ, and the join key a consumer should use is the draft season and
pick number, which is unique within a draft, with position treated as an attribute.

## What this run does not do

- It does not model undrafted rookies; there is no defensible population table.
- It does not say what a rookie is worth; replacement, lineup policy and discount are the ranking lane's.
- It does not correct the first-round quarterback shortfall; it measures it and lets the declared policy decide.
- It does not claim a trading edge.

## Where to look

REPORT.md (rendered record) · EVALUATION.md · CALIBRATION.md · policy_comparison.json · evaluation_exploratory_plain.json
· sensitivity_unresolved_as_zero.json · cohort.csv · manifest.json (identifiers, pairing block, output hashes).
