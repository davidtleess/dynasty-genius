# Frontier & Edge Brainstorm — capture doc
Session: David + Claude, 2026-07-17 (late night). Status: DELIVERED — David worded distribution 2026-07-19; deliver as disposition-read at next cockpit boot with the morning brief.

## DISPOSITION INSTRUCTIONS (crew — read first)
- This is a READ + DISPOSITION task, not an execution order. Return: a synthesis + proposed sequencing converting H1-H5 into named tickets, dependency-ordered against the live board (QB-1 slices 3+, wire-health fix, pre-commit ticket). David gates each ticket onto the priority board; nothing here is self-assigning.
- Sequencing note: H3 (Examiner) is a Gemini re-role — it rides the parked amendment train (spokesperson v3 -> 02 v1.4.x) and effectively IS the ~07-24 Gemini review, which now carries one positive ops datapoint (07-18 telemetry, clean and on-role). H3/H4 scheduling depends on wire trust — sequence behind the profile-registry fix landing.
- Studio exclusion: this document is governance-saturated and must NOT reach Studio (contamination wall). When H5 work opens, Studio receives clean paraphrased design briefs only.
- Transparency: delivered to all three crew panes unredacted, including the Gemini lane audit (v1.3.0 precedent — roles are re-mapped on evidence, in the open). The audit's conclusion is a seat re-fit, not a cut.
Framing: four value types under exploration, one deep dive each — (1) League edge, (2) Decorrelation & resilience, (3) Frontier comparative advantage, (4) Product & experience. Trigger question was "is Gemini providing value?" but scope is now the whole operation: map where value lives, then staff each source with whichever frontier fits. Gemini need not own any of it.

## HARDENED — crew candidates (David-endorsed)

### H1. The Behavioral Book — league-microstructure edge (Dive 1, Source 3) — David: "100% a great edge"
Model the 11 opponents, not the players. Global market prices (FantasyCalc) cannot see league-local behavior — unpriced by definition. Raw material already integrated: Sleeper public API (read-only, no auth; `previous_league_id` chain reaches prior seasons).
Per-manager features derivable from transaction/matchup/draft history:
- trade frequency + partner graph; trades-after-losses (tilt signature)
- FAAB curves (panic-spend vs hoard); add/drop churn (panic index)
- lineup efficiency: points left on bench weekly (attention/skill proxy)
- pick hoarding vs spending (timeline temperament); positional biases
- activity timestamps → when each manager is online (offer-timing signal)
League chat/DMs: documented API has NO chat/DM endpoints (verified 2026-07-17 vs docs.sleeper.com). Routes: (a) manual export of high-signal threads (David is in every DM that matters — preferred), (b) forward-capture: log negotiations as they happen, (c) unofficial authenticated GraphQL — ToS-gray, fragile, PARKED not adopted.

### H2. Source-6 candidates from historical analysis (Dive 1) — David-suggested, analysis will confirm
- Lineup-inefficiency edge: if specific managers systematically bench points, weekly matchup optimization is free wins against them.
- Disengagement detection: activity cliff in a manager's timestamps = trade-target window before the league notices.
First exploratory task (pre-spec): pull full league history via public API, produce a factual behavioral read as evidence for the H1 spec.

### H3. The Independent Examiner (Dive 2) — David's design, jointly hardened
An isolated agent (Gemini is the natural first occupant: different training corpus + first-party Google Search grounding) engaged for blind independent research. CHARTER LAW: produces evidence and arguments, NEVER verdicts — the crew and David judge; if its output is ever treated as a ruling, the role has failed. ("Judge" was the working name; examiner is the correct function.)
Operating rules (all David-originated, refined):
1. Neutral-tasking template + mechanical lint (reuses the No-Verdict linter muscle): no requester identity/lean, no prior conclusions, symmetric verbs (assess, never confirm), no outcome-signaling adjectives. Codex builds the checker; failing taskings don't send.
2. Typed brief, not free-form paper: required sections — findings; evidence (every claim cites a source or flags an assumption); per-finding confidence; "what would change my conclusion"; "strongest honest case against" (dissent absorbed here — see below). Shape-fail = mechanical rejection before human reading.
3. One-way membrane: examiner writes into an exam folder the crew reads (proposals/-pattern, proven); examiner mechanically denied read access to crew deliberations/verdicts/ledgers (Studio contamination-wall precedent). David never pointed at the folder — summaries only (push-not-pull law).
Measurement: track unique-contribution yield (findings that survived crew curation and weren't already held). If yield ~0 over N engagements, the occupant (not necessarily the role) is swapped.
Default engagement mode — SCHEDULED WEEKLY BRIEF (David's idea, hardened): standing tasking written once, neutral-linted once, hash-frozen; no per-run prompting = no per-run framing leak (strictly better than ad-hoc). Cadence-bias controls: (a) null-result license as charter law — "nothing met the bar" is a successful brief; (b) dedupe-without-anchoring — examiner receives only the list of previously reported claims (titles/one-liners), never past reasoning; (c) standing prompt is versioned with a monthly review gate, changes David-worded + re-linted + re-frozen. Ad-hoc engagements are the exception (major pending decisions) since ad-hoc tasking is where bias lives.
WEEKLY BRIEF CONTENT (David-approved): (1) CORE — the Assumption Register: crew maintains a registered list of the system's load-bearing beliefs (aging curves, YPRR weight, rookie-pick valuation, Superflex QB premium, 2yr-fwd PPG target, ...); examiner stress-tests ONE per week in mechanical rotation (topic choice is mechanical = unbiased) against current external evidence. Division of labor: Codex falsifies the code; the examiner falsifies the worldview. (2) STANDING — market anomalies only: price moves with no discoverable public cause, and public developments with no price move yet (discrepancies, not news streams); roster+watchlist scoped; null-licensed. (3) LIGHT/monthly — frontier watch: new data sources, APIs, models, methods relevant to the operation (feeds the living frontier map, Dive 3). EXCLUDED: player takes, rankings, trade recs (verdict-shaped), roster news summaries (David-rejected). Scheduling mechanics exist twice: native `agy schedule --cron` (Antigravity CLI, verified 2026-07-17) or cockpit-standard launchd + `agy -p`; crew picks by verifiable fire-log quality.

### Decorrelation protocol (Dive 2) — crew-process amendment candidate
- Enumerate wide, judge narrow: generative/coverage work (falsification seeds, spec cold-reads, edge-case enumeration) may fan out to weaker-but-different minds; discriminative verdicts stay with frontier pair (Claude/Codex).
- Blindness non-negotiable for any contribution claimed as independent; convergence across lanes counts as evidence only if independence was enforced (audit the WR-synthesis claim against this).
- Standalone dissent desk: NOT adopted (cycle cost, per David); folded into H3's mandatory case-against section. Routine-gate dissent remains Codex's charter.

### H4. The Role-Scout loop — scheduled persona self-improvement (Dive 3.5, David's idea, jointly designed)
Biased-by-design weekly research task: one persona per week in rotation (each role scouted ~monthly), hunting ecosystem developments (skills, plugins, connectors, MCP servers, model capabilities, techniques) that improve ITS role. Bias is correct here: examiner's product is truth (needs neutrality); scout's product is options (needs targeting).
Core law — research only counts as a DIFF TO A LOADED ARTIFACT (charter, skill, hook, script, config): "files are the only memory that survives resets." Output = upgrade proposals, each naming (a) exact artifact to change, (b) role duty improved, (c) cost/risk, (d) falsifiable success signal. No proposal, no adoption.
Pipeline: proposals batch via spokesperson to David in a monthly upgrade board (push-not-pull) → David gates → lands as governed change WITH review date + success signal in the ledger (accretion control — the Tower-role-drift lesson, industrialized-drift prevention).
Hard gates: third-party code (plugins/MCP) requires sandbox trial + Codex source review before adoption (supply-chain). Scope discipline: proposals may change HOW a role executes, never WHAT it owns; scope findings escalate to David separately (research-driven role drift prevention). Product opportunities discovered en route (new data sources/APIs) route to the roadmap, never self-adopted into persona config.
Precedent: the 2026-07-16/17 session itself (permission hooks + ghost-check + charter amendment) was one manual cycle of exactly this loop.

### H5. Last-mile product surfaces (Dive 4) — David-endorsed
The product's thinnest layer is the last mile between system and human: dashboards exist, consumption rituals don't. Three adopted ideas, all last-mile:
1. **Morning Tape as audio** — the weekly in-season brief generated as a ~5-minute listenable artifact (what changed, what's pending, the one decision that matters) from the same data the dashboard renders. Rationale: changes WHETHER intelligence is consumed, not how it looks; Tuesday-morning attention is the product's real bottleneck. Gemini/Google-shaped work (mature generated-audio stack). Target: before NFL Week 1 (~Sept).
2. **Trade Desk negotiation surface** — H1's product form: at offer-construction time, show the counterpart manager's revealed-preference profile (archetype overpays, activity windows, tilt state, timeline posture) beside asset values. Sharpens H1's spec output: queryable per-manager profiles, not a report. Sequenced after H1 produces profiles.
3. **League recap social layer** (lower priority, real theory of value) — weekly generated league recap (Omni video / audio) David posts to league chat. Mechanism: the league's fun-hub gets DEAL FLOW — more inbound trade talk, first calls from shoppers; trades you never hear about are trades you can't win. Behind the Tape in priority.
NOT adopted: realtime voice interface (weekly-rhythm product doesn't need conversational latency; competes with BUILD-1/QB-1 cycles); generated-video analysis for David's own consumption (he reads faster than he watches).
Dive-3 corollary now complete: Google's currency in this operation is perception in, presentation out — ears and voice, never the judgment between.

## CONSIDERED, NOT ADOPTED (reasoning trail for the crew)
- Gemini film-charting / 8-class college tape backfill: killed on source availability (YouTube = highlight reels = uncorrectable selection bias; all-22 paywalled/ToS-hostile), unproven charting accuracy, and CFBD precedent (enrichment failed baseline).
- News/pod event stream + sentiment tracking + RP-Spearman kill test: survived red-team in narrow form but David rates value low; not adopted. May revisit in-season.
- Cutting the Gemini lane outright: rejected as premature framing — this brainstorm replaces the binary.

## DIVE LOG
- Dive 1 (League edge): DONE. Edge decomposition: (1) information timing/depth — small; (2) valuation vs consensus — hard, staffed, BUILD-1-gated; (3) league microstructure — largest unexploited, → H1; (4) portfolio/timeline — medium, extends existing + links to H1 (opponent timelines); (5) execution discipline — already captured by governance, protect.
- Dive 2 (Decorrelation): DONE → H3 + decorrelation protocol.
- Dive 3 (Frontier comparative advantage): DONE. Currency map — Anthropic sells obedience-over-time (builder/Tower/Studio seats correct); OpenAI sells skepticism-per-verdict (falsifier seat correct, local record confirms); Google sells perception-per-dollar (examiner seat = the map's assignment; ops/telemetry seat should be scripts, not any model). Map decays — maintained via the weekly brief's frontier-watch section; staffing reviews become re-mapping exercises.
- Dive 3.5 (Role-Scout): DONE → H4.
- Dive 4 (Product & experience): DONE → H5.
