import type { RosterAuditResponse } from "../lib/api";

function player(
  overrides: Partial<NonNullable<RosterAuditResponse["players"]>[number]> = {},
) {
  return {
    player_id: "p1",
    full_name: "Active WR",
    position: "WR",
    nfl_team: "NYJ",
    age: 27,
    is_prospect: false,
    engine_used: "engine_b",
    model_version: "engine_b_v2",
    model_grade: "ACTIVE_B",
    model_status_applies: true,
    dynasty_value_score: 78.5,
    projection_1y: 12.3,
    projection_2y: 11.1,
    projection_3y: 9.8,
    xvar: 4.2,
    dvs_pct: 81.0,
    signal_completeness: 0.86,
    inputs_present: ["target_share"],
    inputs_missing: [],
    counter_argument: { text: "Solid floor", status: "available", caveats: [] },
    top_drivers: { items: ["target_share"], caveats: [] },
    risk_flags: { items: ["snap_share_below_40pct"], caveats: [] },
    caveats: ["no_market_overlay"],
    roster_audit: {
      cliff_age: 28,
      years_to_cliff: 1,
      age_cliff_risk: 0.4,
      biological_debt_score: 0.2,
      liquidity_risk: "LOW",
      signal: "approaching_cliff",
      signal_drivers: ["age_within_two_years_of_position_cliff"],
      age_value_context: "approaching_cliff_high_projection",
      caveats: ["no_market_overlay"],
      decision_supported: false as const,
    },
    decision_supported: false as const,
    ...overrides,
  };
}

export function activeAudit(): RosterAuditResponse {
  return {
    status: "active",
    engine: "pvo_assembler_v1",
    reason: "ok",
    model_status_by_position: { WR: "VALIDATED", QB: "PROVISIONAL" },
    caveats: ["no_market_overlay"],
    players: [
      player(),
      player({
        player_id: "p2",
        full_name: "QB One",
        position: "QB",
        model_status_applies: true,
      }),
    ],
    qb_context_cards: [
      {
        player_id: "p2",
        full_name: "QB One",
        identity_coverage: "FULL",
        context_role: "context_signal",
        epa_per_dropback: 0.12,
        cpoe: 1.4,
        dakota: 0.05,
        dropback_count: 540,
        pass_attempts: 500,
        qb_context_annotations: ["low_td_int_ratio_bust_context"],
        qb_context_caveats: ["p2s_context_unavailable"],
        source_qb_context_annotations: "cfbd_qb_context_annotations",
        decision_supported: false,
      },
    ],
    dropped_player_count: 0,
    decision_supported: false,
  };
}

export function degradedAudit(): RosterAuditResponse {
  return {
    ...activeAudit(),
    status: "degraded",
    model_status_by_position: { WR: "EXPERIMENTAL" },
    caveats: [
      "no_market_overlay",
      "trust_status_unavailable",
      "player_row_dropped_corrupt",
    ],
    dropped_player_count: 1,
  };
}

export function emptyAudit(): RosterAuditResponse {
  return {
    status: "active",
    engine: "pvo_assembler_v1",
    reason: "ok",
    model_status_by_position: {},
    caveats: ["no_market_overlay"],
    players: [],
    qb_context_cards: [],
    dropped_player_count: 0,
    decision_supported: false,
  };
}

// Shaped like a real assemble_pvo() PRE_MODEL veteran row: flat fields, free-text
// caveats, market fields already excluded by the Inc1 allowlist mapper.
export function realPvoAudit(): RosterAuditResponse {
  return {
    ...activeAudit(),
    players: [
      player({
        player_id: "vet1",
        full_name: "Vet RB",
        position: "RB",
        model_grade: "PRE_MODEL",
        model_status_applies: false,
        dynasty_value_score: null,
        projection_1y: null,
        projection_2y: null,
        projection_3y: null,
        xvar: null,
        dvs_pct: null,
        signal_completeness: 0.24,
        caveats: [
          "dynasty_value_score unavailable: Engine B (active player) not yet validated; model_grade is PRE_MODEL",
          "Fewer than 50% of required signals present — do not use for dynasty decisions until data is refreshed",
          "no_market_overlay",
        ],
      }),
    ],
    model_status_by_position: { RB: "EXPERIMENTAL" },
  };
}
