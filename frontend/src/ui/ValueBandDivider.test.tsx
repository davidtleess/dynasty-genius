// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("ValueBandDivider", () => {
  it("uses disclosed numeric value bands, never subjective fantasy tiers", async () => {
    const { ValueBandDivider } = await import("./ValueBandDivider");

    render(<ValueBandDivider label="Band 1" basis="model value 90-100" />);

    expect(screen.getByRole("separator", { name: /band 1/i })).toBeTruthy();
    expect(screen.getByText(/model value 90-100/i)).toBeTruthy();
    expect(screen.queryByText(/elite|bust|must-start|league winner/i)).toBeNull();
  });
});
