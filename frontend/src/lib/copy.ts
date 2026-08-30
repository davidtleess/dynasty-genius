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
// 4 · The receipt layer — where a raw key is allowed to live, always labelled.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * The consolidated `title={`field=${value}`}` convention. A receipt names the
 * field in words and then shows the raw value, so hovering a number tells you
 * what produced it instead of showing a bare column name.
 */
export function receiptDetail(field: string, value: string | number | null): string {
  const shown = value === null || value === "" ? "not recorded" : String(value);
  return `${fieldLabel(field)} — ${shown} (from ${field})`;
}

/** A labelled receipt line for a raw identifier that has no prose form. */
export function receiptLine(label: string, raw: string | number | null): string {
  return `${label}: ${raw === null || raw === "" ? "not recorded" : String(raw)}`;
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
