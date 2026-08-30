// @vitest-environment jsdom

import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { RealizedOutcomeScorecardResponse } from "../lib/api/types.gen";
import { zRealizedOutcomeScorecardResponse } from "../lib/api/zod.gen";
import { RealizedOutcomeScorecard } from "./RealizedOutcomeScorecard";

function scorecardResponse(
  overrides: Partial<RealizedOutcomeScorecardResponse> = {},
): RealizedOutcomeScorecardResponse {
  return zRealizedOutcomeScorecardResponse.parse({
    status: "inactive",
    status_reason: "awaiting_first_finalized_week",
    as_of_week: null,
    settlement_status: "unsettled",
    maturity_pct: null,
    cohort_metrics: {},
    tracking_rows: [],
    excluded_counts: {},
    coverage: {
      declared_count: null,
      eligible_count: null,
      resolved_count: null,
      outcome_present_count: null,
      graded_count: null,
      rank_eligible_count: null,
      identity_excluded_counts: {},
      prediction_excluded_counts: {},
    },
    decision_supported: false,
    ...overrides,
  }) as RealizedOutcomeScorecardResponse;
}

function mockFetch(status: number, body: unknown) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status === 200,
    status,
    json: async () => body,
  });
}

afterEach(() => vi.restoreAllMocks());

describe("RealizedOutcomeScorecard", () => {
  it("renders the healthy inactive empty state as an educational diagnostic shell", async () => {
    mockFetch(200, scorecardResponse());

    render(<RealizedOutcomeScorecard />);

    await waitFor(() =>
      expect(
        screen.getByRole("region", { name: /diagnostic scorecard/i }),
      ).toBeTruthy(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/realized-outcome/scorecard");
    expect(screen.getByRole("heading", { name: /diagnostic scorecard/i })).toBeTruthy();
    expect(screen.getByText(/accuracy tracker/i)).toBeTruthy();
    expect(screen.getByText(/loop inactive/i)).toBeTruthy();
    expect(screen.getByText(/2026 data accrues from sept/i)).toBeTruthy();
    // DG-109: the reason and the settlement state are unchanged and still on
    // screen — this is the surface's NORMAL pre-season state, not a degraded
    // branch, so these two enums were what it said on a good day.
    expect(
      screen.getByText(/No week has finished yet, so nothing has been graded./i),
    ).toBeTruthy();
    expect(
      screen.getByText(
        /Settlement status: Not enough finished weeks for this to settle/i,
      ),
    ).toBeTruthy();
    expect(screen.getByText(/Data maturity: not yet started/i)).toBeTruthy();
    // DG-111: the stamp is retired. The Model Input Fidelity paragraph is NOT
    // a stamp — it says what the scorecard measures, and that it grades our
    // inputs rather than the players. Kept, reworded into plain speech.
    expect(screen.queryByText("Descriptive only — not decision-grade.")).toBeNull();
    expect(screen.queryByText(/decision_supported=false/i)).toBeNull();
    expect(screen.getByText(/model input fidelity/i)).toBeTruthy();
    expect(screen.getByText(/what the model assumed they would do/i)).toBeTruthy();
    expect(screen.getByText(/grades our inputs, not the players/i)).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByText(/certificate|verifier|recommender/i)).toBeNull();
    expect(screen.queryByText(/\b(buy|sell|start|sit)\b/i)).toBeNull();
  });

  it("renders unavailable on non-OK responses and parse-error on invalid 200 bodies", async () => {
    mockFetch(503, {
      detail: {
        error: "realized_outcome_scorecard_unavailable",
        message: "malformed scorecard",
        decision_supported: false,
      },
    });
    const { unmount } = render(<RealizedOutcomeScorecard />);
    await waitFor(() =>
      expect(screen.getByText(/diagnostic scorecard unavailable/i)).toBeTruthy(),
    );
    unmount();

    mockFetch(200, { bogus: true });
    render(<RealizedOutcomeScorecard />);
    await waitFor(() =>
      expect(screen.getByText(/could not read diagnostic scorecard/i)).toBeTruthy(),
    );
  });

  it("keeps produced-scorecard rendering scaffolded until real artifact validation", async () => {
    mockFetch(
      200,
      scorecardResponse({
        status: "ok",
        status_reason: null,
        as_of_week: 1,
        maturity_pct: 2.94,
        cohort_metrics: {},
        tracking_rows: [],
      }),
    );

    render(<RealizedOutcomeScorecard />);

    await waitFor(() =>
      expect(screen.getByText(/scorecard scaffold active/i)).toBeTruthy(),
    );
    expect(
      screen.getByText(/rich metric rendering waits for real artifact validation/i),
    ).toBeTruthy();
    expect(
      screen.getByText(/Data maturity: 2.94% of tracked weeks finalized/i),
    ).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });
});
