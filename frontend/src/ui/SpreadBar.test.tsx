// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("SpreadBar", () => {
  it("shows uncertainty only with disclosed basis and numeric sigma label", async () => {
    const { SpreadBar } = await import("./SpreadBar");

    render(<SpreadBar label="Value range" value={8.4} sigma={1.6} basis="fold CI" />);

    expect(screen.getByRole("img", { name: /value range.*fold ci/i })).toBeTruthy();
    expect(screen.getByText("σ 1.6").className).toContain("dg-ui-spread__sigma");
    expect(screen.getByText(/basis: fold ci/i)).toBeTruthy();
  });

  it("renders a position dot only when explicit percentage domain is provided", async () => {
    const { SpreadBar } = await import("./SpreadBar");

    const { container, rerender } = render(
      <SpreadBar label="Value range" value={8.4} sigma={1.6} basis="fold CI" />,
    );

    expect(container.querySelector(".dg-ui-spread__bar")).toBeTruthy();
    expect(container.querySelector(".dg-ui-spread__dot")).toBeNull();

    rerender(
      <SpreadBar
        label="Value range"
        value={8.4}
        sigma={1.6}
        basis="fold CI, percentile domain 0-100"
        pct={73}
      />,
    );

    expect(screen.getByRole("img", { name: /position 73 of 100/i })).toBeTruthy();
    const dot = container.querySelector(".dg-ui-spread__dot");
    expect(dot).toBeTruthy();
    expect(dot?.getAttribute("data-pct")).toBe("73");
    expect(dot?.getAttribute("aria-label")).toBeNull();
  });

  it("renders unavailable state instead of a false range", async () => {
    const { SpreadBar } = await import("./SpreadBar");

    const { container } = render(
      <SpreadBar label="Value range" value={null} basis="fold CI" />,
    );

    expect(screen.getByText(/range unavailable/i)).toBeTruthy();
    expect(container.querySelector(".dg-ui-spread__bar")).toBeNull();
  });
});
