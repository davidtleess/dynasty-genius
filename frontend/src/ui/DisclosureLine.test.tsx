// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("DisclosureLine", () => {
  it("standardizes the descriptive-only disclosure", async () => {
    const { DisclosureLine } = await import("./DisclosureLine");

    render(<DisclosureLine />);

    const disclosure = screen.getByText("Descriptive only — not decision-grade.");
    expect(disclosure.className).toContain("dg-ui-disclosure");
  });
});
