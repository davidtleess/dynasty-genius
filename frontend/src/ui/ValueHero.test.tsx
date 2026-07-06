// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("ValueHero", () => {
  it("makes value the focal number without verdict-color semantics", async () => {
    const { ValueHero } = await import("./ValueHero");

    render(
      <ValueHero label="Player value" value="10,256" basis="model value 90-100" />,
    );

    const value = screen.getByText("10,256");
    expect(value.className).toContain("dg-ui-value-hero__number");
    expect(screen.getByText(/model value 90-100/i)).toBeTruthy();
    expect(value.className).not.toContain("green");
    expect(value.className).not.toContain("red");
    expect(value.className).not.toContain("success");
  });
});
