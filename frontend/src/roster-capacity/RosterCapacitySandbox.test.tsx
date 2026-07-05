// @vitest-environment jsdom

import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { RosterCapacityResponse } from "../lib/api/types.gen";
import { zRosterCapacityResponse } from "../lib/api/zod.gen";
import { RosterCapacitySandbox } from "./RosterCapacitySandbox";

function capacityResponse(
  overrides: Partial<RosterCapacityResponse> = {},
): RosterCapacityResponse {
  return zRosterCapacityResponse.parse({
    artifact_status: "ok",
    status: "ok",
    capacity_health: {
      total_players: 29,
      total_capacity: 28,
      total_capacity_cuts_required: 1,
      active_slot_overflow: 2,
      by_slot_class: { active: 22, reserve: 4, taxi: 3 },
      reserve_unrestricted: false,
    },
    candidates: [
      {
        sleeper_player_id: "cut-1",
        full_name: "Boundary Player",
        position: "WR",
        cut_priority: 1,
        candidate_source: "capacity_ordered",
        raw_xvar: 1.5,
        dvs: 44.2,
        xvar_pct: 12.0,
        median_projection_2y: 5.1,
        value_field_status: {
          xvar: "ok",
          dvs: "ok",
          projection_2y: "ok",
          position: "ok",
          model: "ok",
        },
      },
      {
        sleeper_player_id: "cut-2",
        full_name: "Forced Review Player",
        position: "RB",
        cut_priority: 0,
        candidate_source: "forced_review",
        raw_xvar: null,
        dvs: null,
        xvar_pct: null,
        median_projection_2y: null,
        value_field_status: {
          xvar: "unavailable",
          dvs: "unavailable",
          projection_2y: "unavailable",
          position: "ok",
          model: "pre_model",
        },
      },
    ],
    scenarios: [
      {
        cut_set: ["cut-1"],
        cumulative_value_at_risk: [-27.83, -12.5],
        marginal_next_candidate_cost: [0.0, -27.83],
        per_position_depth_impact: { WR: { cuts: 1, pool_size: 4 } },
        pool_deficits: { WR: 0 },
        caveats: ["zero_crossing_range_preserved"],
      },
    ],
    unrostered_pool_range: {
      WR: {
        status: "ok",
        low: -4.25,
        high: 3.5,
        top_k_values: [3.5, 0.0, -4.25],
        pool_size: 3,
        caveats: [],
      },
      RB: {
        status: "waiver_range_unavailable",
        low: null,
        high: null,
        top_k_values: [],
        pool_size: null,
        caveats: ["waiver_range_unavailable:stale_snapshot"],
      },
    },
    excluded_counts: { unresolved_identity: 0 },
    caveats: [],
    created_at: "2026-06-30T12:00:00+00:00",
    sleeper_snapshot_captured_at: "2026-06-30T11:00:00+00:00",
    decision_supported: false,
    ...overrides,
  }) as RosterCapacityResponse;
}

function mockFetch(status: number, body: unknown) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status === 200,
    status,
    json: async () => body,
  });
}

afterEach(() => vi.restoreAllMocks());

describe("RosterCapacitySandbox", () => {
  it("fetches the read-only API and renders descriptive ranges without midpoint collapse or selected rows", async () => {
    mockFetch(200, capacityResponse());

    render(<RosterCapacitySandbox />);

    await waitFor(() =>
      expect(
        screen.getByRole("region", { name: /roster capacity sandbox/i }),
      ).toBeTruthy(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/roster/capacity");
    expect(screen.getByText("Descriptive only — not decision-grade.")).toBeTruthy();
    expect(screen.queryByText(/decision_supported=false/i)).toBeNull();
    expect(
      screen.getByText(/sorted by cut exposure rank as diagnostic order/i),
    ).toBeTruthy();

    const cumulative = screen.getByText("-27.83 to -12.50");
    expect(cumulative.tagName).toBe("SPAN");
    expect(cumulative.getAttribute("data-range-kind")).toBe("cumulative_value_at_risk");
    expect(screen.getByText("0.00 to -27.83").tagName).toBe("SPAN");
    expect(screen.queryByText("-20.17")).toBeNull();
    expect(screen.queryByText(/midpoint/i)).toBeNull();

    const rows = screen.getAllByRole("row");
    for (const row of rows) {
      expect(within(row).queryByRole("checkbox")).toBeNull();
      expect(row.getAttribute("aria-selected")).toBeNull();
      expect(row.className).not.toMatch(/selected|recommended|danger|success/);
    }
    expect(screen.queryByText(/optimizer|drop guide|recommender/i)).toBeNull();
    expect(screen.queryByText(/recommended|best drop|safe to cut/i)).toBeNull();
  });

  it("keeps degraded artifacts in view and surfaces stale caveats", async () => {
    mockFetch(
      200,
      capacityResponse({
        artifact_status: "degraded",
        caveats: ["freshness_unverifiable", "waiver_range_unavailable:stale_snapshot"],
        sleeper_snapshot_captured_at: null,
      }),
    );

    render(<RosterCapacitySandbox />);

    await waitFor(() =>
      expect(screen.getByText(/artifact status: degraded/i)).toBeTruthy(),
    );
    expect(screen.getByText(/Freshness unverifiable/i)).toBeTruthy();
    expect(
      screen.getByText(/Waiver range unavailable \(stale_snapshot\)/i),
    ).toBeTruthy();
    expect(screen.getByText("Descriptive only — not decision-grade.")).toBeTruthy();
  });

  it("renders blocked artifacts as blocked state without stale numbers", async () => {
    mockFetch(
      200,
      capacityResponse({
        artifact_status: "blocked",
        status: "blocked",
        capacity_health: null,
        candidates: [],
        scenarios: [],
        unrostered_pool_range: {},
        caveats: ["capacity_audit_blocked: malformed_snapshot"],
      }),
    );

    render(<RosterCapacitySandbox />);

    await waitFor(() =>
      expect(screen.getByText(/capacity audit blocked/i)).toBeTruthy(),
    );
    expect(
      screen.getByText(/Capacity audit blocked \(malformed_snapshot\)/i),
    ).toBeTruthy();
    expect(screen.queryByText("-27.83 to -12.50")).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.getByText("Descriptive only — not decision-grade.")).toBeTruthy();
  });

  it("renders unavailable on non-OK response and parse error on invalid 200", async () => {
    mockFetch(503, {
      detail: {
        error: "roster_capacity_artifact_unavailable",
        message: "missing",
        decision_supported: false,
      },
    });
    const { unmount } = render(<RosterCapacitySandbox />);
    await waitFor(() =>
      expect(screen.getByText(/roster capacity unavailable/i)).toBeTruthy(),
    );
    unmount();

    mockFetch(200, { bogus: true });
    render(<RosterCapacitySandbox />);
    await waitFor(() =>
      expect(screen.getByText(/could not read roster capacity/i)).toBeTruthy(),
    );
  });

  it("renders empty candidate and unavailable pool states without fabricating zeros", async () => {
    mockFetch(
      200,
      capacityResponse({
        candidates: [],
        scenarios: [],
        unrostered_pool_range: {
          RB: {
            status: "waiver_range_unavailable",
            low: null,
            high: null,
            top_k_values: [],
            pool_size: null,
            caveats: ["waiver_range_unavailable:coverage_floor"],
          },
        },
      }),
    );

    render(<RosterCapacitySandbox />);

    await waitFor(() =>
      expect(screen.getByText(/no capacity candidates/i)).toBeTruthy(),
    );
    expect(screen.getByText(/RB range unavailable/i)).toBeTruthy();
    expect(
      screen.getByText(/Waiver range unavailable \(coverage_floor\)/i),
    ).toBeTruthy();
    expect(screen.queryByText("0.00 to 0.00")).toBeNull();
  });

  it("handles additional edge cases without selecting rows or fabricating values", async () => {
    mockFetch(
      200,
      capacityResponse({
        candidates: [
          {
            sleeper_player_id: "cut-null-xvar",
            full_name: "Null Xvar Player",
            position: "TE",
            cut_priority: 3,
            candidate_source: "capacity_ordered",
            raw_xvar: null,
            dvs: null,
            xvar_pct: null,
            median_projection_2y: null,
            value_field_status: {
              xvar: "unavailable",
              dvs: "unavailable",
              projection_2y: "unavailable",
              position: "ok",
              model: "pre_model",
            },
          },
        ],
        scenarios: [
          {
            cut_set: ["cut-a"],
            cumulative_value_at_risk: [-0, 1.25],
            marginal_next_candidate_cost: null,
            per_position_depth_impact: {},
            pool_deficits: {},
            caveats: [],
          },
          {
            cut_set: ["cut-b"],
            cumulative_value_at_risk: [-3.5, 2.25],
            marginal_next_candidate_cost: [-1.5, 0.5],
            per_position_depth_impact: {},
            pool_deficits: {},
            caveats: [],
          },
        ],
        unrostered_pool_range: {
          TE: {
            status: "ok",
            low: null,
            high: null,
            top_k_values: [],
            pool_size: 0,
            caveats: ["waiver_range_unavailable:null_bounds"],
          },
        },
      }),
    );

    render(<RosterCapacitySandbox />);

    await waitFor(() => expect(screen.getByText("Null Xvar Player")).toBeTruthy());
    expect(screen.getAllByText("unavailable").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("-0.00 to 1.25")).toBeTruthy();
    expect(screen.getByText("-3.50 to 2.25")).toBeTruthy();
    expect(screen.getByText("-1.50 to 0.50")).toBeTruthy();
    expect(screen.getByText("TE range unavailable")).toBeTruthy();
    expect(screen.getByText(/null_bounds/i)).toBeTruthy();
    expect(screen.queryByText("0.00 to 0.00")).toBeNull();
    for (const row of screen.getAllByRole("row")) {
      expect(within(row).queryByRole("checkbox")).toBeNull();
      expect(row.getAttribute("aria-selected")).toBeNull();
    }
  });
});
