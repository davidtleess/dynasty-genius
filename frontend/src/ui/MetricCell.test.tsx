// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("MetricCell", () => {
  it("right-aligns tabular values and exposes a receipt hook", async () => {
    const { MetricCell } = await import("./MetricCell");

    render(
      <MetricCell
        label="value over a replacement starter"
        value="+12.4"
        receipt={{
          label: "xVAR",
          source: "engine_b",
          capturedAt: "2026-07-05T10:15:00-04:00",
        }}
      />,
    );

    const value = screen.getByText("+12.4");
    expect(value.className).toContain("dg-ui-metric__value");
    expect(value.getAttribute("data-align")).toBe("right");
    expect(value.getAttribute("data-numeric")).toBe("tabular");
    expect(
      screen.getByRole("button", {
        name: /provenance for value over a replacement starter/i,
      }),
    ).toBeTruthy();
  });
});
