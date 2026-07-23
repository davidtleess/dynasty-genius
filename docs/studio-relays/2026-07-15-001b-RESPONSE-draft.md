# 001b-RESPONSE — engineering disposition on the rank-first addendum

**Studio's 60-second read**

| ID | Disposition | One line |
|----|-------------|----------|
| N1 | ACCEPTED — requirement confirmed, derivation corrected | Basis is xVAR over the valued cohort, not predicted PPG over the raw scores endpoint |
| N2 | ACCEPTED (rank-first default) | Column placement stays with the client's live design reviews |
| N3 | RESOLVED — client ruled for the idiom, scoped | Green/red legal for rank-movement arrows ONLY; never value/gap/tier hues |
| N4 | ACCEPTED | Trivial |
| N5 | ACCEPTED in shape | Rank comparisons must be population-honest; named tier prose awaits calibrated definitions |
| N6 | ACCEPTED | Same server-owned population feeds it; depends on N7 |
| N7 | CONFIRMED — you were right | Ownership data is Jun-23 stale; a live rosters read exists in the app; cheap fix |
| N8 | ACCEPTED with corrections | Join is server-owned; "opportunities" must be renamed descriptive |

## N1 — the normalization challenge, answered

The requirement stands and we accept it: the model's view becomes a first-class rank-space
output, server-owned, refreshed with the model, joined where the UI reads it. Your derivation
is the right instinct with two corrections:

**Wrong basis for the overall rank.** Predicted PPG ranks players by projected production;
the model's comparable unit is **xVAR — value above replacement**, engine-aware. Within one
position the two orderings nearly coincide (xVAR is monotonic in predicted points there), so
your positional ranks were approximately right. Across positions they diverge exactly where it
matters in a Superflex league: raw PPG ignores replacement context — the thing that makes the
QB premium real rather than a market habit. xVAR is already the basis of the model-lane
percentiles the system publishes; the rank output uses the same spine.

**Wrong population.** The raw Engine-B scores endpoint is an inference partition, not the
valued universe. The valued cohort this week is **469 model-backed players — 389 active-player
engine + 80 rookie engine (players your derivation missed entirely) — and every one carries a
Sleeper ID server-side.** Your 305/398/93 join figures are prototype-era client-side numbers;
do not preserve them anywhere as a contract. The serving contract: a server-owned population
artifact joins model scores to identity with disclosed per-row states (resolved / unresolved /
ambiguous — never a guessed identity), and the rank fields extend that artifact: overall rank +
positional rank, basis-stamped, per-lane cohort denominators, explicit unavailable-reasons,
descriptive-only flags throughout.

**One comparability constraint for all rank-delta copy (feeds N5).** Any "N spots lower"
sentence — overall or positional — is only valid on equal populations. The market lane and the
model lane rank different cohorts (different sizes and memberships, overall and within each
position), so a raw subtraction across lanes is not a fact. `RB3 market · RB17 model` renders
honestly only with each lane's own denominator on the surface (`RB3 of 154 market · RB17 of 62
model`); "spots lower" phrasing requires an equal-population basis or gives way to percentile
comparison. The payload carries both lanes' denominators so the UI can always print an honest
form.

**Your secondary open** (a market-scale value equivalent, so "model value vs market value" is
one chart someday): real, harder — that is a value-scale normalization with a known top-end
compression problem, and the client has already sequenced it as later work. Rank-space doesn't
wait on it; that's precisely why rank-space first is the right call.

## N2 / N4 — accepted

Rank-first default sort and fully sortable columns: accepted, cost is minutes each. Exact
column placement (rank far-left, position rank far-right) stays where it already lives — the
client's live prototype reviews — rather than being fixed here.

## N3 — resolved: the client has ruled, scoped

Your instinct to flag rather than assume was correct, and the escalation is now answered. The
client has ruled for the idiom as a **scoped exception to the color rules: green/red is legal
for rank-movement arrows ONLY — never for value, gap, margin, or tier hues.** Build the `▲2` /
`▼3` chips as specified. The boundary is hard: the moment green/red touches anything that
reads as worth, disagreement magnitude, or quality (rather than pure positional movement), it
is outside the ruling. The color-rule update is being made on our side; nothing blocks your
costing.

## N5 — accepted in shape, two constraints

The rank-comparison-led panel is the shape the client has been asking for. Constraints:
(1) every rank comparison in the panel obeys the population rule above — the payload gives you
what you need to print honest forms; (2) **named tier prose ("Elite", "high-end WR2" as a tier
label) awaits statistically calibrated tier definitions** — until those exist, the panel's
default vocabulary is rank, percentile, and value-neighbor distance, which carry the same
story without an unearned label. Your two G2 questions get their formal answer in the 001
response; the boundary-derivation question you offered to take is exactly the open work.

Two design notes worth building for: rank alone can manufacture cliffs where values are flat —
pair rank with its percentile or a neighbor-distance cue so a 14-spot gap in a flat region
doesn't read like one in a steep region; and give the unranked/unavailable state an explicit
rendering rather than a blank.

## N6 — accepted

One filterable universe table with the KTC anatomy: accepted; it reads from the same
server-owned population + market lane. Availability filtering depends on N7.

## N7 — confirmed; you found a real one

The ownership data you consumed is stamped June 23 — three weeks stale, exactly as you said.
Two valid low-cost fixes exist: the app already makes a live rosters call for another surface,
so the tape/universe can become a second consumer of that call; or the ownership snapshot gets
a scheduled refresh/capture of its own. Which one ships is a costing decision, not a blocker.
Bo Nix: reconciliation against live roster data resolves that state, whichever fix lands.

## N8 — accepted with two corrections

(1) The join is server-owned per the N1 contract — your 93-unjoined figure is a prototype-era
client-side number. Under the serving contract every player carries a disclosed identity state
(resolved / unresolved / ambiguous — never a guessed identity), and the residual unresolved
count is measured at run time, not assumed here.
(2) The **"opportunities" column name must change**: model-market disagreement is real and
renderable at full magnitude, but it is an unvalidated signal, and naming it "opportunities"
turns a descriptive gap into an implied recommendation. Ship the same column as "disagreement"
or "gap" — the data loses nothing.

## Costing note

Engineering constraint on every slice above: a backend contract is not done until **every
direct consuming renderer** has been seen working — captured rendering the **real** payload
(not embedded copies), in the nominal state plus **every changed missing/degraded state the
contract defines**, at desktop and mobile viewports, with mid-scroll capture wherever sticky,
overlay, or scroll-container composition can affect the changed field. When the rank fields
land, your prototype qualifies as the interim consuming renderer only if it renders the real
emitted artifact rather than embedded data; otherwise the parity obligation attaches to the
first direct renderer. Plan for those captures in your cycle.

— Engineering
