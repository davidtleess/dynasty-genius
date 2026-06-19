// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { activeAudit } from "./fixtures";
import { QbContextSection } from "./QbContextSection";

describe("QbContextSection", () => {
  it("renders QB cards labeled context-signal / not decision-grade", () => {
    render(<QbContextSection cards={activeAudit().qb_context_cards} />);
    expect(screen.getByText("QB One")).toBeTruthy();
    expect(screen.getByText(/context signal — not decision-grade/i)).toBeTruthy();
    expect(screen.getByText(/low_td_int_ratio_bust_context/)).toBeTruthy();
  });
  it("renders nothing when there are no cards", () => {
    const { container } = render(<QbContextSection cards={[]} />);
    expect(container.querySelector(".dg-roster__qb")).toBeNull();
  });
});
