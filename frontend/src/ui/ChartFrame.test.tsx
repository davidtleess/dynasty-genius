// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("ChartFrame", () => {
  it("wraps charts with title, disclosure, hard-right-edge summary, and no extrapolation copy", async () => {
    const { ChartFrame } = await import("./ChartFrame");

    render(
      <ChartFrame
        title="Franchise equity trend"
        summary="Line ends at the latest verified team-matrix capture."
      >
        <svg aria-label="Franchise equity trend chart" />
      </ChartFrame>,
    );

    expect(
      screen.getByRole("figure", { name: /franchise equity trend/i }),
    ).toBeTruthy();
    expect(screen.getByText("Descriptive only — not decision-grade.")).toBeTruthy();
    expect(screen.getByText(/latest verified team-matrix capture/i)).toBeTruthy();
    expect(screen.queryByText(/projected|forecast beyond/i)).toBeNull();
  });
});
