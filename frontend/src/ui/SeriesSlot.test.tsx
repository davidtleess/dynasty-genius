// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("SeriesSlot", () => {
  it("does not draw a path without real series data", async () => {
    const { SeriesSlot } = await import("./SeriesSlot");

    const { container } = render(
      <SeriesSlot status="pending" label="Value trend" summary="Series pending" />,
    );

    expect(screen.getByText("Series pending")).toBeTruthy();
    expect(container.querySelector("path")).toBeNull();
  });

  it("renders gaps and terminates the line at the hard right edge", async () => {
    const { SeriesSlot } = await import("./SeriesSlot");

    const { container } = render(
      <SeriesSlot
        status="ready"
        label="Value trend"
        points={[
          { capturedAt: "2026-07-01", value: 10 },
          { capturedAt: "2026-07-03", value: null },
          { capturedAt: "2026-07-05", value: 12 },
        ]}
      />,
    );

    expect(
      screen.getByRole("img", { name: /value trend.*hard right edge/i }),
    ).toBeTruthy();
    expect(container.querySelector("[data-series-gap='true']")).toBeTruthy();
    expect(container.querySelector("[data-hard-right-edge='true']")).toBeTruthy();
  });
});
