import { describe, expect, it } from "vitest";

import type { Coverage, RealizedOutcomeScorecardResponse } from "../lib/api/index";
import { zRealizedOutcomeScorecardResponse } from "../lib/api/zod.gen";

describe("generated realized-outcome Coverage contract", () => {
  it("retains honest grading denominators through the generated Zod boundary", () => {
    const coverage: Coverage = {
      declared_count: 501,
      eligible_count: 476,
      resolved_count: 450,
      outcome_present_count: 421,
      graded_count: 405,
      rank_eligible_count: 318,
      identity_excluded_counts: { not_found: 26 },
      prediction_excluded_counts: { invalid_position: 25 },
    };
    const payload: RealizedOutcomeScorecardResponse = {
      status: "ok",
      settlement_status: "unsettled",
      coverage,
      decision_supported: false,
    };

    const parsed = zRealizedOutcomeScorecardResponse.parse(payload);

    expect(parsed.coverage).toEqual(coverage);
  });

  it.each([
    {},
    {
      declared_count: 1,
      eligible_count: 1,
      resolved_count: 1,
      outcome_present_count: 1,
      graded_count: -1,
      rank_eligible_count: 0,
      identity_excluded_counts: {},
      prediction_excluded_counts: {},
    },
    {
      declared_count: "1",
      eligible_count: 1,
      resolved_count: 1,
      outcome_present_count: 1,
      graded_count: 1,
      rank_eligible_count: 1,
      identity_excluded_counts: {},
      prediction_excluded_counts: {},
    },
  ])("rejects incomplete, negative, or coercive Coverage %#", (coverage) => {
    expect(() =>
      zRealizedOutcomeScorecardResponse.parse({
        status: "ok",
        settlement_status: "unsettled",
        coverage,
        decision_supported: false,
      }),
    ).toThrow();
  });
});
