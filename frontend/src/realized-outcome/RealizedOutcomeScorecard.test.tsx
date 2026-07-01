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
    expect(screen.getByText(/awaiting_first_finalized_week/i)).toBeTruthy();
    expect(screen.getByText(/settlement_status: unsettled/i)).toBeTruthy();
    expect(screen.getByText(/maturity_pct: unset/i)).toBeTruthy();
    expect(screen.getByText(/decision_supported=false/i)).toBeTruthy();
    expect(screen.getByText(/model input fidelity/i)).toBeTruthy();
    expect(screen.getByText(/input\/fidelity audit/i)).toBeTruthy();
    expect(screen.getByText(/not a player verdict/i)).toBeTruthy();
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
    expect(screen.getByText(/maturity_pct: 2.94/i)).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });
});
