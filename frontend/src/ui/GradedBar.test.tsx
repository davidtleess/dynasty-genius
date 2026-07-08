// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("GradedBar", () => {
  it("renders a neutral grade bar only when the basis is disclosed", async () => {
    const { GradedBar } = await import("./GradedBar");

    render(<GradedBar label="Route profile" value={82} basis="film-room grade" />);

    const meter = screen.getByRole("meter", { name: /route profile/i });
    expect(meter.getAttribute("aria-valuenow")).toBe("82");
    expect(screen.getByText(/basis: film-room grade/i)).toBeTruthy();
    expect(meter.getAttribute("data-palette")).toBe("neutral");
  });
});
