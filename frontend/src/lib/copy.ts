// THE COPY DICTIONARY — one module between the pipeline and the screen.
//
// David's ruling, 2026-08-29, verbatim: "I really don't care for the caveats and
// the hard wording governance. I prefer to use prose and layman's language with
// respect to making this a world-class fantasy football dynasty front end. Not a
// data science, data engineering visualization." The Studio spec turns that into
// one engineering requirement (DG091-STUDIO-SPEC.md §1): a dictionary maps every
// backend token, caveat key and status enum to a human string, and **no string
// containing an underscore or an ALL_CAPS token may reach the DOM.**
// `renderRule.ts` holds the rule; this module holds the strings. DG-109
// consolidated four drifting partial maps into it — `describeStatusToken`,
// SystemHealthCard's three display-name maps, the trade lanes' `humanizeToken` /
// `SIGNAL_DISPLAY`, and the ad-hoc `title={`field=${value}`}` convention.
//
// THE LAW THIS MODULE IS UNDER: the furniture goes, the FACTS STAY. A translation
// carries the same fact its token carried — stale still says stale, unscored
// still says unscored, and a caveat never softens into permission. Deleting a
// fact instead of rewording it is a defect, not a simplification. The one thing
// that DOES disappear is absence: "No risk flags available" asserts nothing, so
// it renders nothing (spec §6 rule 6).
//
// TWO FALLBACKS, DELIBERATELY DIFFERENT
//   fieldLabel()   an unknown LABEL humanizes in place. "median_age" → "Median
//                  age" is still an honest label; no meaning is invented.
//   lookupToken()  an unknown SENTENCE token is returned `mapped: false`. Callers
//                  render those in the receipt layer only (see `TokenNotes`),
//                  because a humanized caveat reads as broken English and can be
//                  misread as a claim ("Te review period." — the DG-043 bug).
// Both warn on the console so the crew adds the mapping.

import { findRawCopy } from "./renderRule";

/**
 * Last-resort formatting for a key the dictionary has no entry for. It only
 * reshapes the producer's OWN words — underscores to spaces, a shout to normal
 * case — and never adds or drops one. Short all-caps runs are left alone,
 * because those are the acronyms a manager reads as English (QB, RB, WR, TE,
 * NFL, PPG), not machinery.
 */
function humanize(token: string): string {
  const words = token
    .replaceAll("_", " ")
    .replaceAll(":", " — ")
    .trim()
    .split(" ")
    .map((word) =>
      word.length > 3 && word === word.toUpperCase() && /[A-Z]/.test(word)
        ? word.toLowerCase()
        : word,
    )
    .join(" ");
  return `${words.charAt(0).toUpperCase()}${words.slice(1)}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// 1 · Field labels — what a column, stat or definition-list term is called.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * DG-117 — ONE name for one quantity.
 *
 * `xvar` is how much more a player is worth than a freely available
 * waiver-wire replacement at his position. On 2026-08-30 it had FOUR names on
 * screen at once — "Value above replacement (xVAR)" on the player card and the
 * roster filter, "xVAR bracket" in the roster group-by, bare "xVAR" on Roster
 * Capacity and the trade model lane, and "Above replacement" on the front
 * page — beside "Value over replacement" from this dictionary on League Pulse.
 * A manager reading four names has no way to know they are one number.
 *
 * The spec's name (DG091-STUDIO-SPEC.md §6 rule 5) is the one that stands.
 * Every render site now spells it from here, and `renderRule.ts`'s jargon list
 * fails the build if the acronym comes back.
 */
export const VALUE_OVER_REPLACEMENT = "Value over replacement";

const FIELD_LABELS: Record<string, string> = {
  // Team posture components (src/dynasty_genius/team_posture.py:145-150).
  starter_weighted_xvar_z: "Starter strength vs. the league",
  age_window_score: "Age window",
  early_pick_balance_score: "Early-pick balance",
  development_stash_score: "Taxi and development stash",

  // Team value views.
  starter_weighted_xvar: "Starter-weighted value",
  lineup_xvar: "Starting lineup value",
  depth_credit_xvar: "Credit for depth",
  total_xvar_capped: "Whole roster, capped",
  top_n_xvar: "Top-asset core",
  value_weighted_age: "Age, weighted by value",
  median_age: "Median age",
  pct_value_over_28: "Share of value on players over 28",
  owned_count: "Picks owned",
  outgoing_count: "Picks traded away",
  pick_value_status: "How picks are priced",
  z_score: "vs. the league average",

  // Partner rankings.
  counterparty_roster_id: "Their roster number",
  partner_score: "Trade-fit score",
  complementarity_score: "How well the rosters fit",
  divergence_density_score: "How often we disagree on price",
  activity_recency_score: "How recently they've traded",
  posture_alignment_score: "Whether you're pointed opposite ways",
  perspective_posture: "Where you are",
  counterparty_posture: "Where they are",
  divergence_row_count: "Players we price differently",

  // Opportunity-card evidence.
  position: "Position",
  perspective_position_z: "Your strength here",
  counterparty_position_z: "Their strength here",
  perspective_surplus_label: "Your depth here",
  counterparty_surplus_label: "Their depth here",
  positional_z_differential: "Gap between you",
  fit_score: "Fit",
  feasibility_score: "How doable",
  signal: "What we're seeing",
  evidence_status: "Evidence behind it",
  model_minus_market_delta: "Our price minus the market's",
  market_percentile: "Market percentile",
  model_percentile: "Our percentile",
  asset_xvar: VALUE_OVER_REPLACEMENT,
  divergence_score: "Size of the price gap",
  lineup_role: "Lineup role",

  // Player card / two-lane valuation.
  engine_path: "Which model scored him",
  model_grade: "Model status",
  dynasty_value_score: "Dynasty value",
  xvar: VALUE_OVER_REPLACEMENT,
  xvar_percentile_position: "Position percentile",
  projection_1y: "1-year projection",
  projection_2y: "2-year projection",
  projection_3y: "3-year projection",

  // Opportunity-card sort keys. A sort key names two different things: as a
  // FIELD it is the metric a section is sorted on (here); as a VALUE it is the
  // category the card falls under (VALUE_WORDS below). Both are true, so both
  // shelves carry the key.
  positional_z_differential_desc: "the gap between your rosters",
  absolute_model_market_delta_desc: "how far our price sits from the market's",
  taxi_long_term_value_desc: "long-term value on the taxi squad",

  // Daily-tape receipts.
  consecutive_days: "Days captured in a row",
  last_capture_at: "Last capture",
  registry_version: "Model registry version",
  model_vintage: "Model vintage",
};

/** The human name for a pipeline field. Unknown keys humanize in place + warn. */
export function fieldLabel(key: string): string {
  const known = FIELD_LABELS[key];
  if (known !== undefined) return known;
  console.warn("Copy dictionary: no label for field", key);
  return humanize(key);
}

// ─────────────────────────────────────────────────────────────────────────────
// 2 · Value words — the enum a field holds, said the way a manager would say it.
// ─────────────────────────────────────────────────────────────────────────────

const VALUE_WORDS: Record<string, string> = {
  // Team posture labels (team_posture.py). Heuristics over roster signals —
  // the caveat that says so travels with them, it is not folded in here.
  CONTENDER: "Contending",
  REBUILDING: "Rebuilding",
  ASCENDING: "Rising",
  BALANCED: "Middle of the pack",
  UNCLASSIFIED: "Not enough signal to place them",

  // Positional surplus labels.
  surplus: "Deep",
  deficit: "Thin",
  balanced: "Even",

  // Market-divergence signal (universe_market_divergence).
  INSIDE_BAND: "Our price and the market's agree",
  MODEL_HIGH_MARKET_LOW: "We price him higher than the market does",
  MODEL_LOW_MARKET_HIGH: "The market prices him higher than we do",
  model_higher_than_market: "We price him higher than the market does",
  model_lower_than_market: "The market prices him higher than we do",
  inside_band: "Our price and the market's agree",

  // Evidence status (league_opportunity_map.py:82-84). `evidence_gated` covers
  // TWO producers: a divergence row whose gates genuinely failed
  // (universe_market_divergence.py:265) and a roster-fit card where
  // `gates_blocked` is hardcoded structurally because there is no divergence
  // gate to run (league_opportunity_map.py:292). The sentence has to be true of
  // both, so it states the gate state and nothing more — in particular it does
  // NOT say evidence is withheld, because OpportunityCards.tsx renders the
  // card's full allowlisted evidence either way.
  evidence_complete: "Every input we wanted was there",
  evidence_gated: "This one has not cleared our evidence check",
  inputs_unavailable: "The inputs for this were not available",

  // Which model scored a player (universe_pvo_batch.py:9-20).
  ENGINE_A: "Rookie model — draft capital and age",
  ENGINE_B: "Active-player model",
  BLEND_AB: "A blend of the rookie and active-player models",
  MARKET_ONLY: "Market price only — no projection of ours",
  CONTEXT_ONLY: "Context only — no projection",
  INACTIVE: "Not active",
  UNRESOLVED_IDENTITY: "We could not match him to our records",

  // Model grade (pvo_assembler.py:344-385, scoring/engine_a.py:52-56). The
  // letter IS the model's validation grade; it is kept, not smoothed away.
  PRE_MODEL: "Not scored yet",
  pre_model: "Not scored yet",
  ACTIVE_B: "Scored by the active-player model",
  EXPERIMENTAL: "Scored by an experimental build of the active-player model",
  PROSPECT_C: "Scored by the rookie model — accuracy grade C",
  PROSPECT_D: "Scored by the rookie model — accuracy grade D, its weakest",

  // Opportunity-card types.
  ROSTER_SURPLUS_DEFICIT_MATCH: "Your surplus meets their need",
  UNROSTERED_MODEL_MARKET_DIVERGENCE: "A free agent we price unlike the market",
  DIVERGENCE_MARKET_HIGH: "The market pays more than we do",
  DIVERGENCE_MODEL_HIGH: "We value him more than the market does",
  TAXI_LONG_TERM_VALUE_PRESENT: "Long-term value sitting on the taxi squad",
  UNKNOWN: "Not categorised",

  // Card sort keys — the grouping a card falls under.
  positional_z_differential_desc: "Where your rosters are lopsided",
  absolute_model_market_delta_desc: "Where we and the market disagree",
  taxi_long_term_value_desc: "Taxi squad",

  // Pick pricing.
  active_v1_historical: "Priced from what picks of this round have been worth",
  unvalued: "No price",
  round_tier: "Priced by round, not by slot",

  // Lineup role.
  taxi: "Taxi squad",
  starter_slot: "Starting lineup",
  bench: "Bench",

  // Which market the model was benchmarked against
  // (eval/backtest_harness.py:70-78). The survivor-bias warning is part of the
  // fact and travels with the name.
  fantasycalc_native: "FantasyCalc, captured the same day",
  dynastyprocess_ecr_2qb: "DynastyProcess expert consensus (superflex/2QB)",
  ktc_community_csv: "KeepTradeCut community rankings",
  fantasycalc_history_api_survivor_biased:
    "FantasyCalc history — survivor-biased, it only sees players still ranked today",

  // Plain health words. `degraded` is NOT lateness — the rollup raises it for a
  // stale, unreadable, missing, failed or degraded-input feed alike
  // (system_health_models.py:360-362), and what-changed raises it for an
  // ambiguous comparison. "Running behind" named only one of those and read as
  // the mildest, so the word says that attention is due and leaves the specific
  // state to the rows that carry it.
  ok: "Running normally",
  degraded: "Something needs attention",
  unavailable: "Unavailable",

  // Roster-audit envelope status (roster_audit_models.py:197).
  active: "Running normally",

  // Realized-outcome settlement (realized_outcome_scorecard.py:74-96). Unsettled
  // is the honest pre-season state, not a failure.
  unsettled: "Not enough finished weeks for this to settle",
  settled: "Settled",

  // Roster-audit age signal (roster_auditor.py:475-490). The cliff age is per
  // position (RB 26, WR 28, TE 30, QB 33) and rides the row beside this word.
  past_cliff: "Past the usual decline age",
  at_cliff: "At the usual decline age",
  approaching_cliff: "Within two years of the usual decline age",
  no_age_signal: "No age signal",

  // Age-and-value display context (roster_auditor.py:255-279). Display-only
  // annotation over age proximity + the active-player projection.
  past_cliff_depreciation_risk: "Past the decline age — value can fall from here",
  approaching_cliff_high_projection:
    "Near the decline age, but still projecting above average for his position",
  approaching_cliff_low_projection:
    "Near the decline age and projecting below average for his position",
  prime_window_high_projection:
    "In his prime window and projecting above average for his position",
  stable_age_low_projection:
    "Age is not the issue — he simply projects below average for his position",
};

/**
 * The human word for an enum value. A value that is already plain English is
 * passed through untouched (the render rule is the test); anything still
 * carrying machinery humanizes in place and warns so the crew adds a word.
 */
export function valueWord(value: string): string {
  const known = VALUE_WORDS[value];
  if (known !== undefined) return known;
  if (findRawCopy(value).length === 0) return value;
  console.warn("Copy dictionary: no word for value", value);
  return humanize(value);
}

/**
 * DG-119 — the four posture labels the producer can actually PLACE a team into,
 * for use mid-sentence ("you're rebuilding and they're contending").
 *
 * DERIVED from VALUE_WORDS rather than written out again, so the in-sentence
 * form can never drift into a second name for the same enum — the DG-117
 * defect, where one quantity acquired four names on screen at once. The only
 * change is the leading capital, which is typesetting, not vocabulary.
 *
 * `UNCLASSIFIED` IS DELIBERATELY ABSENT and returns null. team_posture.py emits
 * it when a roster has too little signal to place, and there is no grammatical
 * form of "not enough signal to place them" that can sit inside "you're X and
 * they're Y" without reading as a posture we assigned. A caller that gets null
 * must say the signal is missing in its own words; it must never fall through
 * to a clause that implies we placed the team.
 */
const PLACEABLE_POSTURES: ReadonlySet<string> = new Set([
  "CONTENDER",
  "REBUILDING",
  "ASCENDING",
  "BALANCED",
]);

export function postureClause(value: string): string | null {
  if (!PLACEABLE_POSTURES.has(value)) return null;
  const word = VALUE_WORDS[value];
  if (word === undefined) return null;
  return `${word.charAt(0).toLowerCase()}${word.slice(1)}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// 3 · Token sentences — a caveat or status key, said as a sentence that carries
//     exactly the fact the key carried.
// ─────────────────────────────────────────────────────────────────────────────

const TOKEN_SENTENCES: Record<string, string> = {
  // ── Player evidence ──────────────────────────────────────────────────────
  age_not_near_position_cliff:
    "Age is on his side — he is years away from the usual decline at his position.",
  age_within_two_years_of_position_cliff:
    "Age is a live risk — he is within about two years of the usual decline at his position.",
  age_curve_only:
    "His projection rests on the age curve alone; there is no usage data behind it.",
  no_usage_signal: "We have no snap or usage data for him.",
  // SCOPE, NOT A MARKET FACT. `ROSTER_CAVEATS`/`_PVO_CAVEATS` are CONSTANTS
  // (roster_auditor.py:59, :81) applied to every row unconditionally; the
  // producer's own words for them are "Market overlay is excluded" (:77-80) and
  // "market signals are currently excluded" (:71-73). An earlier draft read
  // "Nobody is quoting a market price for him right now" — a claim about the
  // market that the token never made and that the same card disproves, since
  // ValuationTwoLane prints "Market value 5082 · 30th overall" a few lines above
  // it (playerDetail.live.json: market.status "available" beside this caveat).
  no_market_overlay:
    "Market prices are deliberately left out of this read — it rests on our own numbers.",
  // ALSO SCOPE. The only emitter is roster_auditor.py:493-494, which appends
  // this when `biological_debt_score()` returns None — i.e. when EITHER the
  // age-decline risk or the internal value it weights by was missing from the
  // roster record (:281-292, :247). It does NOT mean we have no value score:
  // the same payload carries `dynasty_value_score: 77.5`, which the card prints
  // as "Dynasty value 77.5" right beside this line.
  no_internal_value_signal:
    "We could not work out his age-weighted value risk — one of the two inputs it needs was missing from this record.",
  engine_b_not_decision_grade:
    "Our active-player model is a sharp second opinion, not a proven market-beater — weigh it accordingly.",
  no_engine_b_projection:
    "The active-player model has not produced a projection for him.",
  current_draft_rookie_engine_a_value_preserved:
    "He is a rookie in the current draft class, so we kept the rookie model's value for him.",
  roster_audit_reconciled_from_universe_pvo:
    "His numbers were reconciled against the league-wide valuation run.",
  engine_a_rookie_forecast_only:
    "The rookie model forecasts rookies only; it does not score veteran careers.",
  veteran_scoring_requires_engine_b:
    "Scoring a veteran takes the active-player model, not this one.",
  no_usage_efficiency_signal: "No usage or efficiency data went into this.",
  // Risk flags (pvo_assembler.py:118, roster_auditor.py:62-63). The amber
  // treatment keys off the RAW token, so these sentences say "decline" freely.
  age_past_position_cliff:
    "He is past the age where production usually starts falling at his position.",
  age_at_position_cliff:
    "He is at the age where production usually starts falling at his position.",
  snap_share_below_40pct: "He was on the field for under 40% of his team's snaps.",
  identity_conflict_requires_manual_review:
    "Two different player records look like him — someone has to untangle that by hand.",
  identity_unverified: "We have not confirmed this is the right player record.",
  engine_b_experimental_v1_fallback:
    "His score came from an experimental build of the active-player model, not the released one.",
  // Absence, not suppression: no counter-argument was produced for him. Callers
  // that follow the absence rule render nothing for it.
  counter_argument_unavailable: "No counter-argument was written for him.",

  // ── Roster-audit trust envelope (roster_audit_models.py:42-77, :86) ───────
  trust_status_unavailable:
    "We could not read the model's own validation record for this position, so it is treated as unproven.",
  trust_status_stale:
    "The model's validation record is for a different build than the one scoring today, so it is treated as unproven.",
  negative_r2_lower_bound:
    "In testing, the model's accuracy band reached below no-better-than-average.",
  low_sample_holdout: "The accuracy test for this position ran on few players.",
  player_row_dropped_corrupt:
    "A roster row could not be read and was left out of this table.",
  qb_context_card_dropped_corrupt:
    "A quarterback context card could not be read and was left out.",

  // ── Quarterback college context (roster_auditor.py:530-560) ──────────────
  // Context signal only — never a model input, and never a verdict on a player.
  low_td_int_ratio_bust_context:
    "In college he threw comparatively few touchdowns for his interceptions.",
  all_purpose_yards_mobility_context:
    "He piled up all-purpose yards in college — a sign he moves as well as he throws.",
  missing_qb_college_context: "We have no college context numbers for him.",
  p2s_context_unavailable:
    "How often pressure turned into a sack is not carried in this lane.",

  // ── Market overlay ───────────────────────────────────────────────────────
  fantasycalc_overlay: "FantasyCalc prices, laid over our own numbers.",
  market_overlay_context_only: "Market prices here are context, not a call.",
  market_overlay_unvalidated_divergence:
    "The price gap is descriptive — we have not proven it is an edge.",

  // ── What changed overnight (what_changed/daily_diff.py:225-307) ──────────
  // NOT a universal negative. `_model_score_deltas` (daily_diff.py:334-379)
  // compares only `set(prior) & set(latest)` — players present in BOTH captures
  // — and the DG-084 guard forces the delta to 0.0 whenever either side is None
  // (115 of today's joinable rows are unscored). An empty delta list therefore
  // means nothing moved AMONG THE PLAYERS WE COULD COMPARE, which is what the
  // sentence now says.
  vintage_changed_no_score_delta:
    "Our projections were rebuilt on a newer model run, and none of the players we could compare moved.",
  // daily_diff.py:255-271 — a compared date carried more than one model vintage,
  // so both the window and the per-player deltas would be ambiguous. The producer
  // refuses to emit a comparison rather than fabricate one; say exactly that.
  model_multi_vintage_ambiguous:
    "Two different model runs landed on the same day, so we will not claim what moved overnight.",
  baseline_holding:
    "Our projections are the same run as yesterday, so there is nothing to compare.",
  insufficient_history: "Not enough days captured yet to compare one to the next.",
  current_not_delta: "This is where things stand right now, not what changed.",
  // Which two clocks a section's age was measured between. Both readings stay
  // on screen at the call site; only the field name goes.
  captured_at_vs_report_generated_at:
    "Age measured from when this data was captured to when the report was written.",
  captured_at_vs_weekly_producer_cadence:
    "Age measured against this section's weekly refresh schedule.",
  freshness_unverifiable: "We could not confirm when this was captured.",
  pre_capture_window: "This is from before we started capturing.",
  // The two producer aborts the front page can actually hit. daily_diff.py:100-107
  // gives up on the market section when the Sleeper roster snapshot is missing —
  // without it there is no roster to price. report.py:490-497 gives up on a
  // structural section when its artifact is absent. Both refuse to emit numbers
  // rather than guess, so both sentences say the comparison did not happen.
  missing_sleeper_snapshot:
    "We could not read your Sleeper roster, so there is nothing to compare your prices against.",
  missing_structural_artifact:
    "The file this section is built from was not there, so this part did not run.",

  // ── League Pulse ─────────────────────────────────────────────────────────
  phase18_heuristic_posture:
    "Posture labels are a formula over roster signals — not a read on what that manager actually intends.",
  future_pick_values_deferred: "Future draft picks are not priced into this yet.",
  posture_unclassified: "One of these teams does not have enough signal for a posture.",
  partner_score_market_influenced:
    "The trade-fit score is partly market-derived, so it is context rather than a proven edge.",
  waiver_status_from_sleeper_snapshot:
    "Waiver status comes from the last Sleeper snapshot.",
  taxi_activation_cost_requires_manual_review:
    "Activating him off the taxi squad costs a roster spot you will have to weigh yourself.",
  evidence_suppressed_banned_term: "Some producer notes were withheld from this card.",
  phase17_non_decision_grade: "Descriptive context, not a decision-grade call.",
  opportunity_signal: "Something here is worth a look.",
  market_divergence_context: "We and the market price this player differently.",
  taxi_long_term_value_present: "There is long-term value sitting on the taxi squad.",
  activation_cost_represented: "The cost of activating him is included.",

  // ── Roster capacity / waiver pool ────────────────────────────────────────
  waiver_range_unavailable:
    "No replacement-value range is available for this position.",
  // Pairs with the market lane's uncertain-pool state: the range on screen is
  // the widest one the data allows, not a tightened estimate.
  market_replacement_pool_stale:
    "Market replacement data is stale, so this range is the widest one possible.",
  density_baseline_insufficient:
    "Too few free agents carry a price right now, so replacement-cost ranges cannot be checked.",
  thin_unrostered_pool_below_min_4:
    "The free-agent pool at this position is thin — fewer than four priced players.",
  valuation_coverage_below_floor:
    "Too few players here carry a price for a dependable replacement range.",

  // ── Draft-pick pricing ───────────────────────────────────────────────────
  pick_value_historical_expected:
    "Picks are priced at what that round has historically been worth.",
  pick_value_floored_at_replacement:
    "A pick is never priced below a replacement-level player.",
  pick_value_thin_sample: "Few past picks back this price, so treat it loosely.",
  generic_future_pick_round_only:
    "We know the round but not the slot, so this is a round-level price.",
  decision_supported_false: "Context to weigh, not a call to act on.",

  // ── Trade Lab market lane (trade_lab/market_reconciler.py:21-27, :326) ────
  // The lane prints these beside its own numbers, so each sentence keeps the
  // scope limit its token carries rather than softening it.
  market_overlay_display_only: "Market values here are shown for context only.",
  fantasycalc_raw_scale_not_xvar:
    "These are FantasyCalc's own numbers on their own scale — not our value over replacement.",
  market_values_not_model_inputs: "Market values never feed our model.",
  fantasycalc_uncovered: "FantasyCalc does not carry a price for this asset.",
  fantasycalc_pick_unavailable: "FantasyCalc does not carry a price for this pick.",

  // ── Accuracy Tracker (realized_outcome_scorecard.py:74-96) ───────────────
  awaiting_first_finalized_week:
    "No week has finished yet, so nothing has been graded.",
};

// Real-shape tokens the producers build at runtime — a prefix or a pattern
// rather than a fixed string. Each keeps the suffix verbatim so no precision is
// lost; only the vocabulary around it changes.
const TOKEN_PATTERNS: {
  match: (token: string) => RegExpExecArray | boolean | null;
  build: (token: string) => string;
}[] = [
  {
    match: (t) => t.startsWith("league_pulse_artifact_state_"),
    build: (t) =>
      `This league snapshot was built from data captured ${t.slice("league_pulse_artifact_state_".length).trim()}.`,
  },
  {
    match: (t) => t.startsWith("waiver_range_unavailable:"),
    build: (t) =>
      `No replacement-value range for this position — ${humanize(t.slice("waiver_range_unavailable:".length).trim()).toLowerCase()}.`,
  },
  {
    match: (t) => t.startsWith("capacity_audit_blocked:"),
    build: (t) =>
      `The roster-capacity check could not run — ${humanize(t.slice("capacity_audit_blocked:".length).trim()).toLowerCase()}.`,
  },
  {
    // e.g. WR_waiver_range_unavailable_recovery_unverifiable
    match: (t) => /^([A-Z]{1,3})_waiver_range_unavailable_(.+)$/.exec(t),
    build: (t) => {
      const m = /^([A-Z]{1,3})_waiver_range_unavailable_(.+)$/.exec(t);
      const position = m?.[1] ?? "";
      const reason = humanize(m?.[2] ?? "").toLowerCase();
      return `No replacement-value range at ${position} — ${reason}.`;
    },
  },
  {
    // "Signal completeness 83% — missing: ppg_t_minus_1, ppg_t_minus_2, …"
    // The producer already writes this as a sentence; only the input names are
    // machinery. The percentage and the full list of what is missing survive.
    match: (t) => /^Signal completeness (\d+)% — missing: (.+)$/.exec(t),
    build: (t) => {
      const m = /^Signal completeness (\d+)% — missing: (.+)$/.exec(t);
      const pct = m?.[1] ?? "";
      const missing = (m?.[2] ?? "")
        .split(",")
        .map((name) => inputName(name.trim()))
        .filter((name, index, all) => all.indexOf(name) === index);
      return `We have ${pct}% of the inputs we want for him. Missing: ${listSentence(missing)} — so this projection leans harder on what is left.`;
    },
  },
  {
    // "dynasty_value_score unavailable: Engine B (active player) not yet
    // validated; model_grade is PRE_MODEL"
    match: (t) => t.startsWith("dynasty_value_score unavailable:"),
    build: () =>
      "No dynasty value for him yet — the active-player model has not been validated for his position, so he is unscored.",
  },
];

/** Model input names, said in football rather than in column names. */
const INPUT_NAMES: Record<string, string> = {
  ppg_t: "this season's points per game",
  ppg_t_minus_1: "last season's points per game",
  ppg_t_minus_2: "the season before's points per game",
  ppg_t_minus_1_available: "last season's points per game",
  ppg_t_minus_2_available: "the season before's points per game",
  snap_share: "snap share",
  snap_share_t_minus_1: "last season's snap share",
  snap_share_t_minus_1_available: "last season's snap share",
  games_t: "games played this season",
  aging_curve_value: "his place on the age curve",
  weighted_opportunity: "weighted opportunity",
  tprr: "targets per route run",
  yprr: "yards per route run",
  cpoe: "completion percentage over expected",
  dakota: "the Dakota passing metric",
  epa_per_dropback: "expected points added per dropback",
  is_dual_threat: "whether he runs as well as throws",
  full_name: "his name",
  player_id: "his player record",
};

/** The football name for one model input. Exported for the QB context cards. */
export function inputName(key: string): string {
  const known = INPUT_NAMES[key];
  if (known !== undefined) return known;
  console.warn("Copy dictionary: no name for model input", key);
  return humanize(key).toLowerCase();
}

function listSentence(items: string[]): string {
  if (items.length === 0) return "nothing";
  if (items.length === 1) return items[0] as string;
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

export type TokenNote = {
  /** The token exactly as the backend sent it — kept for the receipt layer. */
  raw: string;
  /** What the screen should say. */
  text: string;
  /** False when the dictionary has no entry: render in a receipt, never in body copy. */
  mapped: boolean;
};

/**
 * Translate one backend token. `mapped: false` means the dictionary has no entry
 * yet — the caller must put that note in the receipt layer, because a humanized
 * caveat reads as broken English and can be mistaken for a claim.
 */
export function lookupToken(token: string): TokenNote {
  const exact = TOKEN_SENTENCES[token];
  if (exact !== undefined) return { raw: token, text: exact, mapped: true };
  for (const rule of TOKEN_PATTERNS) {
    if (rule.match(token)) return { raw: token, text: rule.build(token), mapped: true };
  }
  // A status enum that is also a value word ("ok", "degraded") is one shelf of
  // the same dictionary, not an unmapped token.
  const word = VALUE_WORDS[token];
  if (word !== undefined) return { raw: token, text: word, mapped: true };
  // Some producers already write plain sentences ("FantasyCalc snapshot is
  // static"). Those need no translation, and the render rule is the test: a
  // string carrying no raw key is passed through untouched rather than
  // paraphrased. The dictionary exists to remove machinery, not to rewrite
  // English that is already fine.
  if (findRawCopy(token).length === 0) {
    return { raw: token, text: token, mapped: true };
  }
  console.warn("Copy dictionary: no sentence for token", token);
  return { raw: token, text: humanize(token), mapped: false };
}

/**
 * The sentence for a token the caller knows it must render inline (a status
 * line, a single caveat). Unmapped tokens still humanize so the render rule
 * holds; the console warning is how the crew learns to add the mapping.
 */
export function describeToken(token: string): string {
  return lookupToken(token).text;
}

// ─────────────────────────────────────────────────────────────────────────────
// 4 · The receipt layer — where a raw IDENTIFIER is allowed to live, labelled.
// ─────────────────────────────────────────────────────────────────────────────
//
// DG-120 narrowed this section's remit and it is worth saying why. The header
// used to read "where a raw key is allowed to live", and a MESSAGE is a key too,
// so unreadable status strings lived here by the letter of it. Only an ADDRESS
// belongs in the raw layer now; the messages moved to section 9.

/**
 * The consolidated `title={`field=${value}`}` convention. A receipt names the
 * field in words and then shows the raw value, so hovering a number tells you
 * what produced it instead of showing a bare column name.
 */
export function receiptDetail(field: string, value: string | number | null): string {
  const shown = value === null || value === "" ? "not recorded" : String(value);
  return `${fieldLabel(field)} — ${shown} (from ${field})`;
}

// `receiptLine(label, raw)` used to live here, returning `"label: raw"` as ONE
// string. It is gone, and its going is the point of DG-120: a single string
// cannot declare which half of itself is an address, so the render rule could
// only take the whole line or leave it — and it left it. `ui/Receipt.tsx`
// renders the same line as two nodes, the label ours and the value declared
// `data-identifier`, which reads identically and can be audited. Every call
// site moved (League Pulse, Trade partners, the player card).

/**
 * DG-119 — `receiptDetail` without the leading label, for the one shape where
 * the label is ALREADY on screen: a definition list whose `<dt>` names the
 * field and whose `<dd>` carries the value. Printing the full form there gives
 * "How well the rosters fit" twice in eight lines, which reads as a bug.
 *
 * The receipt still names the producer field, because that is what makes it a
 * receipt. Only the duplicated half goes.
 */
export function receiptValue(field: string, value: string | number | null): string {
  const shown = value === null || value === "" ? "not recorded" : String(value);
  return `${shown} (from ${field})`;
}

// ─────────────────────────────────────────────────────────────────────────────
// 5 · Health surfaces — the names and states of the daily feeds.
// ─────────────────────────────────────────────────────────────────────────────

const TIER_NAMES: Record<string, string> = {
  core_substrate: "core data",
  daily_diagnostics: "daily updates",
  auxiliary: "secondary data",
};

export function tierName(tier: string): string {
  const known = TIER_NAMES[tier];
  if (known !== undefined) return known;
  console.warn("Copy dictionary: no name for tier", tier);
  return humanize(tier).toLowerCase();
}

const ARTIFACT_NAMES: Record<string, string> = {
  pvo_refresh: "Model valuations",
  feature_refresh: "Model inputs",
  // Matches the "Daily What-Changed" navigation surface the manager knows.
  what_changed: "Daily what-changed",
  roster_capacity: "Roster capacity",
  roster_capacity_status: "Roster capacity check",
  league_opportunity: "League opportunity",
  league_capture: "League snapshot",
  realized_outcome: "Realized outcomes",
  market_divergence: "Divergence margins",
};

export function artifactName(artifactId: string): string {
  const known = ARTIFACT_NAMES[artifactId];
  if (known !== undefined) return known;
  console.warn("Copy dictionary: no name for artifact", artifactId);
  return humanize(artifactId);
}

const SUBSYSTEM_NAMES: Record<string, string> = {
  model_provenance: "Model provenance",
  capture_health: "Capture health",
  tier_readiness: "Tier readiness",
};

export function subsystemName(subsystemId: string): string {
  const known = SUBSYSTEM_NAMES[subsystemId];
  if (known !== undefined) return known;
  console.warn("Copy dictionary: no name for subsystem", subsystemId);
  return humanize(subsystemId);
}

/**
 * A report's freshness state. Every value in the contract has an entry —
 * `inputs_degraded` included, which used to fall through to the raw enum and
 * was silently dropped from the summary counts.
 */
const REPORT_STATE_LABELS: Record<string, string> = {
  fresh: "Fresh",
  freshness_overdue: "Pending — within grace",
  stale: "Stale",
  corrupt_or_empty: "Unreadable",
  dormant: "Dormant — off-season expected",
  missing: "No data recorded",
  inputs_degraded: "Ran, but on degraded inputs",
  producer_failed: "Last run failed. Earlier values may still be in use.",
};

export function reportStateLabel(status: string): string {
  const known = REPORT_STATE_LABELS[status];
  if (known !== undefined) return known;
  console.warn("Copy dictionary: no label for report status", status);
  return humanize(status);
}

/**
 * The countable phrase for a freshness state — the summary renders
 * `${count} ${label}`, so every entry has to read correctly at any n.
 */
const REPORT_COUNT_LABELS: Record<string, string> = {
  fresh: "fresh",
  freshness_overdue: "pending",
  stale: "stale",
  corrupt_or_empty: "unreadable",
  dormant: "dormant",
  missing: "no data",
  inputs_degraded: "on degraded inputs",
  producer_failed: "failed",
};

export function reportCountLabel(status: string): string {
  const known = REPORT_COUNT_LABELS[status];
  if (known !== undefined) return known;
  console.warn("Copy dictionary: no count label for report status", status);
  return humanize(status).toLowerCase();
}

const SUBSYSTEM_STATE_LABELS: Record<string, string> = {
  ok: "All good",
  // Same correction as the value word: `degraded` is not a claim about lateness.
  degraded: "Something needs attention",
  unavailable: "Unavailable",
};

export function subsystemStateLabel(status: string): string {
  const known = SUBSYSTEM_STATE_LABELS[status];
  if (known !== undefined) return known;
  console.warn("Copy dictionary: no label for subsystem status", status);
  return humanize(status);
}

// ─────────────────────────────────────────────────────────────────────────────
// 6 · Market-lane caveats that need the lane's own source name in the sentence,
//     so a future non-FantasyCalc source is named correctly rather than
//     mislabelled inside a truth-bearing caveat.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * The trust surface's own grade ladder (eval/backtest_artifact.py:122-125,
 * assigned at backtest_harness.py:335-348). It is a SEPARATE vocabulary from a
 * player's `model_grade` — `EXPERIMENTAL` means "this build is experimental"
 * there and "the gates have not been cleared" here — so it gets its own shelf
 * rather than colliding inside the shared value words.
 */
const TRUST_GRADE_WORDS: Record<string, string> = {
  PRE_MODEL: "Not modelled yet",
  EXPERIMENTAL: "Experimental — the checks are not passing",
  // backtest_harness.py:335-347 assigns ACTIVE_B in THREE different cases: the
  // rank-correlation or stability check failed (`not g1_pass or not g2_pass`),
  // the market test was deferred for under-coverage, or the model lost to the
  // market. "In use, edge unproven" named only the last two and turned a failed
  // accuracy check into a milder "we just haven't proven it". The one thing true
  // of all three is that the ladder is not clear, so that is what it says.
  ACTIVE_B: "In use — it has not cleared every check we run",
  ACTIVE_B_VALIDATED: "In use, ranks well in testing",
  DECISION_GRADE: "Cleared every check we run",
};

/**
 * The roster audit's per-position Engine-B trust chip
 * (roster_audit_models.py:42-77). A THIRD vocabulary again: `EXPERIMENTAL` here
 * means the position's validation record is missing or stale, which is not what
 * it means on a player's `model_grade` or on the trust console's ladder — so it
 * gets its own shelf rather than colliding inside either.
 *
 * DG-117: these read "checked out in testing" / "provisional" / "experimental —
 * not validated". That is how a QA engineer signs off a build, not how a manager
 * reads a football product, and it was on David's screen one click into the
 * rail. The STATES are unchanged — the words are.
 *
 * What each one actually means, from the gate that assigns it
 * (eval/composite_gate.py:86-146, read through
 * roster_audit_models.py:41-77):
 *   VALIDATED    every backtest season cleared the ranking and confidence-band
 *                checks (a first cold-start season may be excused), the most
 *                recent season cleared both, and the safety floors held.
 *   PROVISIONAL  the safety floors held — no leakage, enough coverage, enough
 *                seasons — but a season the gate cannot excuse missed one of
 *                those two checks. WHICH check it missed is not knowable here:
 *                the loader hands the front end the bare status and nothing
 *                else (roster_audit_models.py:42-77 returns `model_status`
 *                only), so this word must not name one.
 *   EXPERIMENTAL either a safety floor failed, or the roster-audit loader could
 *                not read or could not date this position's validation record
 *                and failed closed. Both mean the same thing to a reader:
 *                nothing here is proven. WHICH of them it was rides the
 *                envelope caveats beside the chips
 *                (`trust_status_unavailable` / `trust_status_stale`), so this
 *                word must not claim to know.
 */
/*
 * DG-117 REVIEW-PANEL FIX — PROVISIONAL said "missed an accuracy one", and on
 * David's screen that is false. The gate runs TWO per-season checks and names
 * them separately: `fold_rank_pass` is the accuracy one (Spearman >= threshold
 * AND R² > floor, composite_gate.py:29-37) and `fold_ci_adequate` is a SAMPLE
 * adequacy one (the 95% CI on that Spearman is narrow enough to trust the
 * estimate, composite_gate.py:39-42). QB is PROVISIONAL today on the second,
 * not the first: backtest_result_QB.json records `failed_rank_folds: []` with
 * `validity_spearman_pass: true` and `validity_r2_pass: true`, and the single
 * unexcused failure is fold 3's `failed_ci_folds`. So the chip told a manager
 * his quarterback model was not accurate enough, when the producer says every
 * accuracy check passed and one backtest season was simply too thin to confirm
 * the result from.
 *
 * The word now says the union of the two, because the union is all the front
 * end can know — it receives the bare status string. It still refuses to soften:
 * a season did fail a check, and that is stated.
 */
const POSITION_TRUST_WORDS: Record<string, string> = {
  VALIDATED: "passed its accuracy checks",
  PROVISIONAL: "passed the safety checks, but not every season we tested confirmed it",
  EXPERIMENTAL: "not proven",
};

/**
 * What the per-position chips are chips OF. Rendered once above the row: the
 * chips named a state without ever naming its subject, so "RB · provisional"
 * told a manager nothing about what was provisional.
 */
export const POSITION_TRUST_LEDE =
  "How far our active-player model has been checked, position by position:";

export function positionTrustWord(status: string): string {
  const known = POSITION_TRUST_WORDS[status];
  if (known !== undefined) return known;
  if (findRawCopy(status).length === 0) return status;
  console.warn("Copy dictionary: no word for position trust status", status);
  return humanize(status);
}

/**
 * Roster-audit liquidity risk (`roster_auditor.py` `liquidity_risk`) — how many
 * second-round picks are on hand to patch depth with. Its own shelf because the
 * bare value `LOW` is far too generic to sit in the shared value words.
 */
const LIQUIDITY_WORDS: Record<string, string> = {
  HIGH_NO_SECOND_ROUND_ESCAPE_HATCH: "no second-round picks to patch depth with",
  MEDIUM_LIMITED_ESCAPE_HATCH: "one second-round pick to patch depth with",
  LOW: "second-round picks in hand to patch depth with",
};

export function liquidityWord(risk: string): string {
  const known = LIQUIDITY_WORDS[risk];
  if (known !== undefined) return known;
  if (findRawCopy(risk).length === 0) return risk;
  console.warn("Copy dictionary: no word for liquidity risk", risk);
  return humanize(risk);
}

export function trustGradeWord(grade: string): string {
  const known = TRUST_GRADE_WORDS[grade];
  if (known !== undefined) return known;
  if (findRawCopy(grade).length === 0) return grade;
  console.warn("Copy dictionary: no word for trust grade", grade);
  return humanize(grade);
}

const SOURCED_CAVEATS: Record<string, (sourceLabel: string) => string> = {
  market_overlay_static_caveat: (source) =>
    source === ""
      ? "Market values come from a saved snapshot, not a live feed."
      : `Market values come from a saved ${source} snapshot, not a live feed.`,
  source_timestamp_is_fetch_time_not_publish_time: () =>
    "The capture date above is when we pulled these prices, not when the source published them.",
  // Emitted for every TE by universe_market_divergence.py:291.
  te_review_period: () =>
    "Tight end values are under review, so treat this one as a work in progress.",
};

/** A market caveat, with the lane's own source named inside the sentence. */
export function sourcedCaveat(token: string, sourceLabel: string): TokenNote {
  const build = SOURCED_CAVEATS[token];
  if (build !== undefined) {
    return { raw: token, text: build(sourceLabel), mapped: true };
  }
  return lookupToken(token);
}

// ─────────────────────────────────────────────────────────────────────────────
// 7 · Timestamps.
// ─────────────────────────────────────────────────────────────────────────────

// Deterministic regardless of host locale/timezone (CI-stable): fixed en-US +
// America/New_York. The exact ISO string belongs in a title attribute at the
// call site; null/undefined → "—"; unparseable input renders unchanged.
const CAPTURE_TIME_FORMAT = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZoneName: "short",
});

export function formatCaptureTimestamp(iso: string | null | undefined): string {
  if (iso === null || iso === undefined) {
    return "—";
  }
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) {
    return iso;
  }
  return CAPTURE_TIME_FORMAT.format(new Date(parsed));
}

// DG-111 — what replaced the stamp.
//
// `DISCLOSURE_LINE` ("Descriptive only — not decision-grade.") used to render on
// every region of every surface — seven times on the front page alone. David
// repealed that register on 2026-08-29: "I don't care to persist the governance
// of language and caveats and lack of overall recommendation from the back end
// into the front end. I'd rather use layman's terms and call a spade a spade."
// That ruling IS the sign-off that released the exact-string lock; the constant
// and the `ui/DisclosureLine.tsx` primitive are both gone, and
// `ui/retiredFurniture.test.js` fails if either comes back.
//
// The API field `decision_supported=false` is UNCHANGED and the honest reading
// of it survives — but as ONE sentence, in plain words, on the two surfaces
// where it actually changes how you read a number: the player card (whose
// projection came from this model) and the Model Trust console (whose subject
// IS this model's standing). One constant, so the two can never drift apart.
export const MODEL_STANDING_SENTENCE =
  "Our model is a sharp second opinion, not a proven market-beater — weigh it accordingly.";

// ─────────────────────────────────────────────────────────────────────────────
// 8 · DG-113 — the morning read's own vocabulary.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * The three daily capture stores, in words.
 *
 * Names taken from `app/config/capture_cadence.json` (config version 3), which
 * is what the health endpoint reports on: each entry there is one table, on one
 * daily schedule, with its own `capture_start_date`. The names say what the
 * feed carries rather than which table it lands in — `fc_forward_capture` reads
 * `fc_forward_capture_raw` filtered to `fc_native`, i.e. FantasyCalc's daily
 * prices; `model_forward_capture` snapshots our own scores on the 09:45 chain
 * step; `market_divergence_history` is the day-by-day record of where the two
 * disagree.
 */
const FEED_NAMES: Record<string, string> = {
  fc_forward_capture: "Daily market prices",
  model_forward_capture: "Daily model scores",
  market_divergence_history: "Model-versus-market price gaps",
};

export function feedName(storeId: string): string {
  const known = FEED_NAMES[storeId];
  if (known !== undefined) return known;
  console.warn("Copy dictionary: no name for feed", storeId);
  return humanize(storeId);
}

/**
 * A position code as the group of players it names, for prose that counts them
 * ("1 spot among quarterbacks"). Deliberately partial: a code with no entry
 * here produces NO position clause at all rather than a humanized guess, so an
 * unfamiliar code can never invent a group of players that does not exist.
 */
const POSITION_GROUPS: Record<string, string> = {
  QB: "quarterbacks",
  RB: "running backs",
  WR: "receivers",
  TE: "tight ends",
  K: "kickers",
  DEF: "defenses",
};

export function positionGroup(position: string | null | undefined): string | null {
  if (position === null || position === undefined) return null;
  return POSITION_GROUPS[position.trim().toUpperCase()] ?? null;
}

// ─────────────────────────────────────────────────────────────────────────────
// 9 · DG-120 — THE RECEIPT LAYER: identifiers stay, messages become sentences.
// ─────────────────────────────────────────────────────────────────────────────
//
// A receipt carries two kinds of string and they are not the same kind of
// thing:
//
//   an IDENTIFIER is an ADDRESS. `app/data/what_changed/…json`,
//   `scripts/run_pvo_refresh.py`, `pvo_refresh`, a run id, a git sha, a schema
//   version. It names something a person can go and look at, and rewording it
//   destroys the only thing it was for. These never pass through this
//   dictionary. They are rendered inside `data-identifier` and stay byte-exact.
//
//   a MESSAGE is a SENTENCE. A status, a reason, a condition, a count.
//   `live_precondition_not_ok:capture_health_ok=degraded` addresses nothing —
//   there is no `live_precondition_not_ok` to go and look at. It is a sentence
//   someone declined to write, and it belongs here with every other sentence in
//   the product.
//
// Everything below is the second kind. The rule is DG-109's, unchanged: the
// furniture goes, the FACTS STAY. A degraded store still says which store and
// which days; a failed precondition still says which check and what it read;
// a stale report still says stale. Nothing is dropped — the raw identifier the
// message sat beside is on screen underneath it.
//
// EVERY SENTENCE HERE IS TRACED TO THE LINE THAT PRODUCES IT. Where a comment
// names a file and line, that is the producer whose behaviour the sentence
// claims. A sentence with no producer behind it is a guess, and a guess in the
// receipt layer is worse than the raw token — the raw token at least did not
// lie.

/** One piece of a receipt message: our words, or bytes we must not touch. */
export type ReceiptSegment =
  | { kind: "prose"; text: string }
  | { kind: "identifier"; raw: string };

/** One line of a receipt: what it is about, in words, and the address it names. */
export type ReceiptDetail = {
  /** The human label — what a manager would call the thing this line is about. */
  label: string;
  /** The message, in prose, with any address inside it kept byte-exact. */
  message: ReceiptSegment[];
  /** The raw id this line is about. Rendered beneath the label, byte-exact. */
  identifier: string;
};

const prose = (text: string): ReceiptSegment => ({ kind: "prose", text });
const identifier = (raw: string): ReceiptSegment => ({ kind: "identifier", raw });

/**
 * The last resort for a message with no entry above.
 *
 * It returns the producer's OWN bytes, never a humanized paraphrase — a
 * humanized caveat reads as broken English and can be mistaken for a claim
 * (the DG-043 bug), and the receipt layer is the one place where showing the
 * raw string is honest rather than lazy. What it does NOT do is hide it: the
 * segment is prose, not an identifier, so `renderRule` sees it, the gate goes
 * red, and the crew writes the sentence. An unwritten message is a defect that
 * should be loud, and David keeps seeing the true string in the meantime.
 */
function unwrittenMessage(message: string): ReceiptSegment[] {
  // `zSubsystemHealth.basis` is a bare `z.string()` (zod.gen.ts:1329) where
  // `zSurfaceReadiness.basis` is `.min(1)`, so an empty basis is a shape the
  // boundary accepts. Absence renders nothing (spec §6 rule 6) — a "Why" label
  // standing over an empty span promises a reason and delivers none.
  if (message.trim() === "") return [];
  if (findRawCopy(message).length === 0) return [prose(message)];
  console.warn("Copy dictionary: no sentence for receipt message", message);
  return [prose(message)];
}

/**
 * One TOKEN inside a receipt sentence, with the same law as `unwrittenMessage`.
 *
 * `describeToken` humanizes an unmapped token, and outside the receipt layer
 * that is right: DG-109 pairs it with a `TokenNotes` paragraph that prints the
 * raw key alongside, so nothing is lost. Inside a receipt there is no such
 * paragraph — the sentence IS the whole rendering — so a humanized miss would
 * replace the producer's bytes with prose nobody wrote, and `findRawCopy` would
 * see no underscores and let it through. Three refuters caught exactly that on
 * this ticket's first build, in the two branches below. Returning the raw token
 * keeps the address on screen AND keeps the render rule red, which is the whole
 * point of §9: the fallback must not be able to buy silence.
 */
function receiptToken(token: string): string {
  const note = lookupToken(token);
  return note.mapped ? note.text : note.raw;
}

/**
 * The five surfaces tier-readiness grades (`app/config/tier_readiness.json`),
 * named with the LEAF LABEL each one carries in the nav rail
 * (`shell/destinations.ts`) — the words on the tab David actually clicks.
 *
 * That is a deliberate choice over the config's own `display_name`, and the
 * two differ on three of the five: the config says "Roster Capacity", "Trade
 * Lab" and "League Pulse" where the nav says "Cut list", "Build a trade" and
 * "League". This receipt exists to tell a person WHICH PART of the product is
 * held back, and a name he cannot find in the rail does not tell him that.
 */
const SURFACE_NAMES: Record<string, string> = {
  // destinations.ts: Roster › Cut list.
  roster_capacity: "Cut list",
  // destinations.ts: Today.
  daily_what_changed: "Today",
  // destinations.ts: Track record › Model trust.
  model_trust_console: "Model trust",
  // destinations.ts: Trades › Build a trade.
  trade_lab: "Build a trade",
  // destinations.ts: League.
  league_pulse: "League",
};

export function surfaceName(surfaceId: string): string {
  const known = SURFACE_NAMES[surfaceId];
  if (known !== undefined) return known;
  console.warn("Copy dictionary: no name for surface", surfaceId);
  return humanize(surfaceId);
}

/**
 * The two live preconditions a surface can be held back by
 * (`_KNOWN_PRECONDITIONS`, system_tier_readiness_models.py:43-45). The set is
 * closed in the backend — an unknown one is config corruption there — so an
 * unknown one here is a real drift worth warning about.
 */
const PRECONDITION_NAMES: Record<string, string> = {
  model_provenance_ok: "model provenance",
  capture_health_ok: "capture health",
};

function preconditionName(key: string): string {
  const known = PRECONDITION_NAMES[key];
  if (known !== undefined) return known;
  console.warn("Copy dictionary: no name for precondition", key);
  return humanize(key).toLowerCase();
}

/**
 * A report's `basis` — the freshness evaluator's one-line account of WHY the
 * row reads the way it does (`evaluate_report_freshness`,
 * system_health_models.py:501-655). Every branch of that function is here.
 */
const REPORT_BASIS_SENTENCES: Record<string, string> = {
  // :538 — the configured path held no file at all.
  artifact_absent: "The file this report writes was not there.",
  // :620 — no embedded timestamp declared and no modification time either.
  no_observable_timestamp: "Nothing on the file said when it was written.",
  // :636 with timestamp_basis "embedded_timestamp" (:614).
  embedded_timestamp_fresh:
    "Inside its freshness window, going by the timestamp the report publishes.",
  // :636 with timestamp_basis "mtime" (:618) — no timestamp field is declared
  // for this artifact, so the file's own clock is what there is.
  mtime_fresh: "Inside its freshness window, going by when the file was last written.",
  // :638 — past the scheduled run, inside the configured grace hours after it.
  within_grace: "Past its scheduled run, still inside the grace period after it.",
  // :640 — past the scheduled run and past the grace hours too.
  past_grace: "Past its scheduled run, and past the grace period after it.",
  // :649 — the dormancy floor, applied only to a MISSING artifact off-season.
  dormant_ok_offseason: "Out of season — nothing was expected to run.",
  // :451 — the config declares an input-provenance block and none was readable.
  input_provenance_unreadable:
    "This report is supposed to record where its inputs came from, and that record could not be read.",
  // :467 — every declared input stream loaded, none fell back to an earlier season.
  inputs_live: "Every input it reads loaded live.",
};

/**
 * A report `basis` that carries a value inside it. Ordered most specific first;
 * each one names the producer branch it translates.
 */
const REPORT_BASIS_PATTERNS: {
  match: RegExp;
  build: (m: RegExpMatchArray) => ReceiptSegment[];
}[] = [
  {
    // :540-543 — `below_min_size:{observed}<{floor}`. Both numbers are facts
    // about the file, not addresses, so both are said in the sentence.
    match: /^below_min_size:(\d+)<(\d+)$/,
    build: (m) => [
      prose(
        `Too small to be a real report — ${m[1]} bytes, under the ${m[2]}-byte floor.`,
      ),
    ],
  },
  {
    // :553-556 — the artifact declares a status field and it was absent, or
    // present and not text. The field NAME is an address into the artifact.
    match: /^malformed_status:(.+)$/,
    build: (m) => [
      prose("The status field this report is supposed to publish ("),
      identifier(m[1] as string),
      prose(") was missing, or was not text."),
    ],
  },
  {
    // :606-609 — the declared timestamp field held something that is not a date.
    match: /^malformed_embedded_timestamp:(.+)$/,
    build: (m) => [
      prose("The timestamp field this report publishes ("),
      identifier(m[1] as string),
      // :600-609 covers BOTH arms — the field was absent (`raw is None`) and
      // the field was present and unparseable. The sentence names both,
      // because "could not be read" alone would imply something was there.
      prose(") was missing, or could not be read as a date."),
    ],
  },
  {
    // :631-634 — a clock-skew guard. The suffix says which clock was read.
    match: /^future_timestamp:(embedded_timestamp|mtime)$/,
    build: (m) => [
      prose(
        m[1] === "mtime"
          ? "Its timestamp is in the future — read from when the file was last written."
          : "Its timestamp is in the future — read from the timestamp the report publishes.",
      ),
    ],
  },
  {
    // :561-562 — `producer_failure:{fact.failure_reason or 'unreported'}`. The
    // reason is arbitrary producer bytes: `app/config/report_freshness.json`
    // declares a free-text `failure_reason_field` on six of nine artifacts, two
    // of them core_substrate. So it goes through the dictionary if the
    // dictionary knows it, and through UNTOUCHED if it does not — never
    // humanized, which would delete the producer's own words from the screen.
    match: /^producer_failure:(.+)$/,
    build: (m) =>
      m[1] === "unreported"
        ? [prose("The run reported that it failed, and gave no reason.")]
        : [prose(`The run reported that it failed: ${receiptToken(m[1] as string)}`)],
  },
  {
    // :467 — the healthy input-provenance line, with the streams named.
    match: /^inputs_live: (.+)$/,
    build: (m) => [
      prose("Every input it reads loaded live: "),
      ...streamSegments(m[1] as string),
      prose("."),
    ],
  },
];

/**
 * The stream list inside an input-provenance basis, e.g.
 * `pbp 2025 (ValueError), player_stats 2025 (ConnectionError)`.
 *
 * `_describe_stream` (system_health_models.py:383-405) builds each phrase as
 * `{stream name}[ {season}][ ({details})]`, so the FIRST word is the stream's
 * id — an address into the producer's own input block — and everything after
 * it is already the plain-language description that function exists to write.
 * The id is kept byte-exact; the description is passed through untouched,
 * because paraphrasing a count of rows would be inventing one.
 */
function streamSegments(list: string): ReceiptSegment[] {
  const segments: ReceiptSegment[] = [];
  const items = list.split(", ");
  items.forEach((item, index) => {
    if (index > 0) segments.push(prose(", "));
    const space = item.indexOf(" ");
    if (space === -1) {
      segments.push(identifier(item));
      return;
    }
    segments.push(identifier(item.slice(0, space)));
    segments.push(prose(item.slice(space)));
  });
  return segments;
}

/**
 * The degraded input-provenance basis (`summarize_input_provenance`,
 * system_health_models.py:470-480): up to three sections joined by ` | `, each
 * a shouted header and a stream list. The headers are the only machinery in
 * it, and each one is a claim the function makes explicitly:
 *
 *   EMPTY          `status != "loaded"` (:456)   — the stream did not load.
 *   EARLIER SEASON `fallback_used is True` (:460) — the season it ASKED for was
 *                  refused and an earlier one was served. DG-023: this is NOT a
 *                  cache and must never be called one.
 *   LIVE           neither (:463)                 — loaded, season as requested.
 */
const PROVENANCE_SECTION_LEDES: Record<string, string> = {
  EMPTY: "Did not load: ",
  "EARLIER SEASON": "Served an earlier season than the one asked for: ",
  LIVE: "Loaded live: ",
};

function provenanceSections(basis: string): ReceiptSegment[] | null {
  const sections = basis.split(" | ");
  const segments: ReceiptSegment[] = [];
  for (const [index, section] of sections.entries()) {
    const split = section.indexOf(": ");
    if (split === -1) return null;
    const lede = PROVENANCE_SECTION_LEDES[section.slice(0, split)];
    if (lede === undefined) return null;
    if (index > 0) segments.push(prose(" · "));
    segments.push(prose(lede));
    segments.push(...streamSegments(section.slice(split + 2)));
  }
  return segments.length > 0 ? segments : null;
}

/** A report row's `basis`, said as a sentence. Identifiers inside it survive. */
export function reportBasisMessage(basis: string): ReceiptSegment[] {
  const exact = REPORT_BASIS_SENTENCES[basis];
  if (exact !== undefined) return [prose(exact)];
  for (const rule of REPORT_BASIS_PATTERNS) {
    const match = basis.match(rule.match);
    if (match !== null) return rule.build(match);
  }
  const provenance = provenanceSections(basis);
  if (provenance !== null) return provenance;
  return unwrittenMessage(basis);
}

/**
 * A report's `disclosures` — side facts the evaluator attaches to a row. Both
 * of them change what the row's own numbers mean, so neither is decoration.
 */
const DISCLOSURE_SENTENCES: Record<string, string> = {
  // :580 and :617 — appended whenever the time on the row came from the file
  // rather than from inside the report. It is why "18 hr ago" is the file's age.
  "timestamp_source:mtime_fallback":
    "The time on this row is when the file was last written, not a timestamp inside it.",
  // :653-654 — auxiliary rows are excluded from the rollup by
  // `_TIER_SEVERITY` (:363), which has no `auxiliary` key. Saying so here is
  // what stops a failed secondary feed reading as a healthy overall status.
  auxiliary_info_only:
    "Secondary data: this row is reported for information and does not move the overall status.",
};

export function disclosureSentence(token: string): ReceiptSegment[] {
  const known = DISCLOSURE_SENTENCES[token];
  if (known !== undefined) return [prose(known)];
  return unwrittenMessage(token);
}

/**
 * One tier-readiness surface's own `basis`
 * (`evaluate_surface_readiness`, system_tier_readiness_models.py:277-375, and
 * the two overrides in system_tier_readiness.py:142 and :211).
 */
const SURFACE_BASIS_SENTENCES: Record<string, string> = {
  // :352-354 — no `ratified_date` in app/config/tier_readiness.json. This
  // branch sits AHEAD of the insufficient-data one in the same else-chain, so a
  // surface can reach it with a check that was never gradeable; the earlier
  // wording ("Its checks pass") claimed more than the branch entails.
  awaiting_david_ratification: "It has not been signed off by David yet.",
  // :357-358 — active, but a component reported `insufficient_data`.
  readiness_active_with_insufficient_data:
    "Running, with too little data behind one of its checks to grade it.",
  // :360-361 — every gate component passed.
  all_readiness_checks_passed: "Every readiness check passed.",
  // system_tier_readiness.py:155 — the happy path of the evidence probe.
  "declared evidence files present": "Its declared evidence files are all present.",
};

/**
 * The two bases the producer writes for a surface that IS graded ready.
 *
 * `_default_tier_readiness_status` (system_health.py:63-68) filters the surface
 * list on `surface.tier_status != "ok"` — and "ok" is NOT a member of
 * `TierStatus` (system_tier_readiness_models.py:25-30), whose four values are
 * diagnostic_grade_active, diagnostic_grade_active_limited,
 * preconditions_degraded and not_graduated. The comparison is therefore a
 * tautology and the basis names EVERY surface whenever the rollup is degraded,
 * ready ones included. The R8 overlay (system_tier_readiness.py:196-214)
 * downgrades ONE surface whose own producer artifact is absent, and the five
 * surfaces declare five different artifacts — so a list of one held-back
 * surface and four passing ones is a live shape, not a hypothetical.
 *
 * Reading the docstring's intent instead of the filter's behaviour is how a
 * heading saying "5 parts of the product are not graded ready" ends up printed
 * over four rows that read "Every readiness check passed."  These two bases are
 * the ones set alongside a tier_status inside `_ACTIVE_STATUSES` (:357-361), so
 * they are what lets the frontend count the held-back surfaces itself rather
 * than trusting a filter that filters nothing.
 */
const READY_SURFACE_BASES: ReadonlySet<string> = new Set([
  "all_readiness_checks_passed",
  "readiness_active_with_insufficient_data",
]);

function surfaceBasisMessage(basis: string): ReceiptSegment[] {
  const exact = SURFACE_BASIS_SENTENCES[basis];
  if (exact !== undefined) return [prose(exact)];

  // :344-349 — the integrity cascade. A precondition that is not `ok` wins
  // outright, and this is the string it writes. The observed value is the
  // precondition's OWN status word, so it goes through the same shelf of the
  // dictionary the health pill uses.
  const precondition = basis.match(/^live_precondition_not_ok:([a-z_]+)=(.+)$/);
  if (precondition !== null) {
    return [
      prose(
        `Waiting on the ${preconditionName(precondition[1] as string)} check, which is reporting: ${valueWord(
          precondition[2] as string,
        ).toLowerCase()}.`,
      ),
    ];
  }

  // system_tier_readiness.py:138-143 — one entry per missing evidence file,
  // joined by "; ". The paths are addresses and stay exactly as written.
  if (basis.startsWith("evidence_missing:")) {
    const paths = basis
      .split("; ")
      .map((part) => part.replace("evidence_missing:", ""));
    const segments: ReceiptSegment[] = [
      prose(
        paths.length === 1
          ? "A declared evidence file is missing: "
          : "Declared evidence files are missing: ",
      ),
    ];
    paths.forEach((path, index) => {
      if (index > 0) segments.push(prose(", "));
      segments.push(identifier(path));
    });
    return [...segments, prose(".")];
  }

  // system_tier_readiness_models.py:301-320 — the FOUR bases a component defect
  // actually writes onto a SURFACE. Every one of them is `{defect}:{component}`
  // with the component name suffixed, and none was written until now: the
  // entries this dictionary held for this area were `ComponentReadiness.basis`
  // values, which the health payload never carries and this function is never
  // called with. So the realistic broken morning — a gate component failing —
  // printed raw machinery while four written sentences sat unreachable.
  // The component name is an address into `_KNOWN_COMPONENTS` and stays exact.
  const component = basis.match(
    /^(component_failed|component_state_missing|unknown_component_status|required_component_not_applicable):(.+)$/,
  );
  if (component !== null) {
    const sentence: Record<string, [string, string]> = {
      // :319 — the component reported `fail`.
      component_failed: ["Its readiness check ", " did not pass."],
      // :301-303 — a declared component recorded no state at all (fail-closed).
      component_state_missing: ["Its readiness check ", " recorded no state at all."],
      // :306-309 — a status outside the four the registry allows.
      unknown_component_status: [
        "Its readiness check ",
        " reported a status this product does not recognise.",
      ],
      // :311-315 — R6: `not_applicable` is legal only on an optional component.
      required_component_not_applicable: [
        "Its readiness check ",
        " reported itself not applicable, and it is not optional.",
      ],
    };
    const [head, tail] = sentence[component[1] as string] as [string, string];
    return [prose(head), identifier(component[2] as string), prose(tail)];
  }

  // system_tier_readiness.py:205-213 — a producer artifact the surface declares
  // is not on disk. The path is an address.
  const artifact = basis.match(/^producer_artifact_missing:(.+)$/);
  if (artifact !== null) {
    return [
      prose("A file its producer is supposed to write is missing: "),
      identifier(artifact[1] as string),
      prose("."),
    ];
  }

  // system_tier_readiness.py:145-151 — the off-season probe, already a sentence
  // apart from its leading key.
  if (basis.startsWith("off_season_presence_probe_only: ")) {
    return [
      prose(
        `Out of season, so only its evidence was checked — ${basis.slice("off_season_presence_probe_only: ".length)}`,
      ),
    ];
  }

  return unwrittenMessage(basis);
}

/**
 * A capture store's own reason (`_store_reason`, system_health.py:75-105).
 *
 * That function already writes plain language for every branch it has —
 * "missing 1 of 68 days (2026-08-12)", "stale since 2026-08-12", "3 days below
 * the 60% row floor" — so this passes it through rather than paraphrasing a
 * count. The one branch that can carry machinery is the store's own caveat
 * list (:103), and those go through the token dictionary — but through
 * `receiptToken`, not `describeToken`. Class A is a closed two-token set
 * (system_capture_health_models.py:400-404) and everything else degrades by
 * default, so the caveats that can actually reach a DEGRADED store's reason are
 * the class-B set, none of which the dictionary has a sentence for yet. Under
 * `describeToken` every one of them would have reached David as invented prose
 * with the producer's token nowhere in the document and the render rule green.
 */
function storeReasonMessage(reason: string): ReceiptSegment[] {
  if (findRawCopy(reason).length === 0) return [prose(reason)];
  const parts = reason.split("; ").map((part) => receiptToken(part));
  return [prose(parts.join(" · "))];
}

/**
 * A subsystem's `basis` — one guard's account of itself.
 *
 * Three of these are compound: capture health and tier readiness both write a
 * summary followed by one entry per degraded store / not-ready surface
 * (system_health.py:139-141 and :66-69). A compound basis becomes a SUMMARY
 * sentence plus one labelled line per entry, so each entry keeps its own
 * identifier instead of all of them being buried in one string.
 */
export function subsystemBasisMessage(basis: string): {
  summary: ReceiptSegment[];
  lines: ReceiptDetail[];
} {
  // system_health.py:216 — the fallback when an adapter returns a bare status
  // and no reason at all. It restates the status the row already shows, and
  // saying so is the only honest translation of it.
  const bare = basis.match(/^adapter_status:(.+)$/);
  if (bare !== null) {
    return {
      summary: [
        prose(
          `The check returned only its status (${valueWord(bare[1] as string).toLowerCase()}), with nothing further.`,
        ),
      ],
      lines: [],
    };
  }

  // :143 and :72 — the fail-closed arms. Neither says what went wrong, because
  // neither knows; the sentence must not pretend otherwise.
  if (basis === "capture_health_uncomputable") {
    return {
      summary: [prose("Capture health could not be worked out at all.")],
      lines: [],
    };
  }
  if (basis === "tier_readiness_uncomputable") {
    return { summary: [prose("Readiness could not be worked out at all.")], lines: [] };
  }
  if (basis === "tier_readiness_route_unavailable") {
    return { summary: [prose("The readiness check could not be reached.")], lines: [] };
  }

  // :137 and :60 — the healthy arms, already written as sentences by the
  // producer ("all 3 capture stores healthy", "all 5 surfaces ready"), and :70.
  if (
    /^all \d+ capture stores healthy$/.test(basis) ||
    /^all \d+ surfaces ready$/.test(basis) ||
    basis === "no surface named a reason"
  ) {
    return {
      summary: [prose(`${basis.charAt(0).toUpperCase()}${basis.slice(1)}.`)],
      lines: [],
    };
  }

  // :139-141 — `{k} of {n} stores degraded — {store_id}: {reason}; …`.
  const stores = basis.match(/^(\d+) of (\d+) stores degraded — (.+)$/);
  if (stores !== null) {
    const entries = splitLabelledEntries(stores[3] as string);
    // The summary promises the rows that follow it. If the tail did not parse,
    // the promise would be empty — so fall through to the raw string rather
    // than print a heading over nothing.
    if (entries.length > 0) {
      // One degraded store is the live shape for model_forward_capture today,
      // and "1 of 3 … feeds are in a bad state" is the sentence David reads on
      // that morning. The verb agrees, the way the surfaces branch already did.
      const feedVerb = stores[1] === "1" ? "is" : "are";
      return {
        summary: [
          prose(
            `${stores[1]} of ${stores[2]} daily capture feeds ${feedVerb} in a bad state. Which, and why:`,
          ),
        ],
        lines: entries.map(([id, reason]) => ({
          label: feedName(id),
          message: storeReasonMessage(reason),
          identifier: id,
        })),
      };
    }
  }

  // :63-68 — `{surface_id}: {surface basis}; …`. NOT "one entry per surface
  // that is not ready", which is what the producer's variable name and its
  // docstring both say: the filter is `tier_status != "ok"` against a
  // `TierStatus` with no "ok" member, so this is EVERY surface. See
  // READY_SURFACE_BASES. The surface's own basis is the only thing on the line
  // that says where that surface actually stands, so the count comes from the
  // bases, never from the length of a list that was never filtered.
  const surfaces = splitLabelledEntries(basis);
  // One id the dictionary does not know used to send the WHOLE receipt back to
  // the raw 400-character dump. `surfaceName` already warns and humanizes an
  // unknown id, so one unknown surface now costs one row's label, not the other
  // four rows' translations.
  if (surfaces.length > 0 && surfaces.some(([id]) => id in SURFACE_NAMES)) {
    const heldBack = surfaces.filter(
      ([, surfaceBasis]) => !READY_SURFACE_BASES.has(surfaceBasis),
    );
    const rows = surfaces.map(([id, surfaceBasis]) => ({
      label: surfaceName(id),
      message: surfaceBasisMessage(surfaceBasis),
      identifier: id,
    }));

    // Every surface on the list is graded ready. The rollup is still degraded —
    // that is why this basis exists at all — but nothing here is what degraded
    // it, and a heading claiming otherwise would be contradicted by its own
    // rows. State what the list is and let each row speak.
    if (heldBack.length === 0) {
      return {
        summary: [prose("Where each part of the product stands:")],
        lines: rows,
      };
    }

    const count = heldBack.length === 1 ? "One part" : `${heldBack.length} parts`;
    const verb = heldBack.length === 1 ? "is" : "are";

    // ONE CAUSE, SAID ONCE. On 2026-08-30 all five surfaces carried the SAME
    // basis — every one of them waiting on capture health — and printing it
    // five times filled the drawer with 10 lines that said one thing. Worse, it
    // buried the fact worth having: this is not five problems, it is one. The
    // shared sentence moves into the summary and the rows keep their names and
    // their ids. It collapses only when EVERY surface on the list is held back
    // by the identical string; a ready surface in the list is a different fact
    // and keeps its own line.
    const shared = new Set(heldBack.map(([, surfaceBasis]) => surfaceBasis));
    if (heldBack.length === surfaces.length && shared.size === 1) {
      return {
        summary: [
          prose(
            `${count} of the product ${verb} not graded ready, all for the same reason. `,
          ),
          ...surfaceBasisMessage([...shared][0] as string),
        ],
        lines: rows.map((row) => ({ ...row, message: [] })),
      };
    }

    // Mixed, or several causes. The count is of the held-back surfaces; the
    // rows are ALL of them, each saying for itself whether it passed.
    return {
      summary: [
        prose(
          heldBack.length === surfaces.length
            ? `${count} of the product ${verb} not graded ready. Which, and why:`
            : `${count} of the ${surfaces.length} checked ${verb} not graded ready. Where each stands:`,
        ),
      ],
      lines: rows,
    };
  }

  return { summary: unwrittenMessage(basis), lines: [] };
}

/** What an id looks like in these payloads: lower snake_case, nothing else. */
const ENTRY_ID = /^[a-z][a-z0-9_]*$/;

/**
 * Split `id: rest; id: rest; …` into pairs.
 *
 * Two things make this less trivial than it looks, and both are live:
 *
 *   the REST contains colons — `roster_capacity:
 *   live_precondition_not_ok:capture_health_ok=degraded` — so the id is
 *   everything up to the FIRST ": " (colon-space), never the first colon.
 *
 *   the REST contains "; " — `_store_reason` (system_health.py:105) joins a
 *   store's own bits with exactly that separator, so one store can produce
 *   `market_divergence_history: missing 4 of 53 days; stale since 2026-08-12`.
 *   A part whose head is not an id is therefore a CONTINUATION of the entry
 *   before it, not a new one. Splitting naively made the second bit its own
 *   nameless row.
 *
 * Returns [] when the string is not of this shape at all, so a caller falls
 * through to the raw message rather than inventing structure that is not there.
 */
function splitLabelledEntries(text: string): [string, string][] {
  const entries: [string, string][] = [];
  for (const part of text.split("; ")) {
    const split = part.indexOf(": ");
    const head = split === -1 ? "" : part.slice(0, split);
    if (split === -1 || !ENTRY_ID.test(head)) {
      const previous = entries[entries.length - 1];
      if (previous === undefined) return [];
      previous[1] = `${previous[1]}; ${part}`;
      continue;
    }
    entries.push([head, part.slice(split + 2)]);
  }
  return entries;
}
