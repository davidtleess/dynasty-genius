// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("CaveatBlock", () => {
  it("renders high-contrast neutral disclosure copy without nested-card markup", async () => {
    const { CaveatBlock } = await import("./CaveatBlock");

    const { container } = render(
      <CaveatBlock
        tone="neutral"
        title="Context note"
        items={[
          "Player values are descriptive only.",
          "Market prices never feed the model.",
        ]}
      />,
    );

    const region = screen.getByRole("note", { name: /context note/i });
    expect(region.className).toContain("dg-ui-caveat");
    expect(region.getAttribute("data-tone")).toBe("neutral");
    expect(screen.getByText("Market prices never feed the model.")).toBeTruthy();
    expect(container.querySelector(".dg-card .dg-card")).toBeNull();
  });
});
