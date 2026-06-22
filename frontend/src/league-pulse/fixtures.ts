import type { LeaguePulseResponse } from "../lib/api";

export function leaguePulseResponse(
  overrides: Partial<LeaguePulseResponse> = {},
): LeaguePulseResponse {
  return {
    captured_at: "2026-06-22T18:00:00Z",
    caveats: ["league_pulse_artifact_state_2026-06-22"],
    decision_supported: false,
    dropped: {
      market_overlay_cards: 0,
      model_native_cards: 0,
      partner_rankings: 0,
      recommended_drops: 0,
      team_postures: 0,
      team_values: 0,
      decision_supported: false,
    },
    market_overlay_cards: [
      {
        card_id: "market-1",
        card_type: "DIVERGENCE_MODEL_HIGH",
        caveats: ["market_overlay_unvalidated_divergence"],
        decision_supported: false,
        evidence: {
          signal: "MODEL_HIGH_MARKET_LOW",
          market_percentile: 42,
          model_minus_market_delta: 0.18,
        },
        opportunity_score: 0.52,
        rationale_primary: "opportunity_signal",
        rationale_secondary: ["market_overlay_context_only"],
        recommended_drop: {
          sleeper_player_id: "drop-1",
          full_name: "Depth WR",
          position: "WR",
          cut_priority: 2,
          ir_compliance_status: "not_ir_eligible",
          cut_rationale: ["opportunity_signal"],
          decision_supported: false,
        },
        score_components: {
          fit_score: 0.4,
          divergence_score: 0.7,
          feasibility_score: 0.5,
        },
      },
    ],
    model_native_cards: [
      {
        card_id: "model-1",
        card_type: "ROSTER_SURPLUS_DEFICIT_MATCH",
        caveats: [],
        decision_supported: false,
        evidence: {
          position: "RB",
          perspective_position_z: -0.7,
          counterparty_position_z: 0.9,
          perspective_surplus_label: "deficit",
          counterparty_surplus_label: "surplus",
        },
        opportunity_score: 0.61,
        rationale_primary: "opportunity_signal",
        rationale_secondary: ["counterparty_fit"],
        score_components: {
          fit_score: 0.8,
          feasibility_score: 0.6,
        },
      },
    ],
    partner_rankings: [
      {
        counterparty_roster_id: 2,
        counterparty_team_name: "Team Two",
        caveats: ["partner_score_market_influenced"],
        decision_supported: false,
        evidence: {
          perspective_posture: "CONTENDER",
          counterparty_posture: "REBUILDING",
          divergence_row_count: 3,
          position_scores: {
            QB: 0.1,
            RB: 0.8,
            WR: 0.3,
            TE: 0.2,
          },
        },
        market_influenced: true,
        matched_positions: ["RB"],
        partner_score: 0.74,
        score_components: {
          complementarity_score: 0.8,
          divergence_density_score: 0.5,
          activity_recency_score: 0.2,
          posture_alignment_score: 0.6,
        },
      },
    ],
    perspective_roster_id: 1,
    source_artifacts: {
      decision_supported: false,
      league_opportunity: { schema_version: "league_opportunity.v1" },
      team_posture: { schema_version: "team_posture.v1" },
      team_value_matrix: { schema_version: "team_value_matrix.v1" },
    },
    status: "degraded",
    team_postures: [
      {
        roster_id: 1,
        team_name: "David",
        posture_label: "CONTENDER",
        score: 0.7,
        components: {
          starter_weighted_xvar_z: 1.1,
          age_window_score: 0.4,
          early_pick_balance_score: 0.2,
          development_stash_score: 0.1,
        },
        caveats: [],
        decision_supported: false,
      },
    ],
    team_values: [
      {
        roster_id: 1,
        team_name: "David",
        age_profile: {
          value_weighted_age: 25.4,
          median_age: 25,
          pct_value_over_28: 0.22,
        },
        decision_supported: false,
        future_picks: {
          owned_count: 7,
          outgoing_count: 1,
          pick_value_status: "unvalued",
        },
        positional_summary: {
          QB: { z_score: 0.4, surplus_label: "balanced" },
          RB: { z_score: -0.3, surplus_label: "deficit" },
          WR: { z_score: 0.8, surplus_label: "surplus" },
          TE: { z_score: 0.1, surplus_label: "balanced" },
        },
        value_views: {
          starter_weighted_xvar: 8.4,
          lineup_xvar: 7.9,
          depth_credit_xvar: 1.2,
          total_xvar_capped: 9.1,
          top_n_xvar: 8.6,
          decision_supported: false,
        },
      },
    ],
    ...overrides,
  };
}
