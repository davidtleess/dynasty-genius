// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { activeAudit } from "./fixtures";
import { QbContextSection } from "./QbContextSection";

describe("QbContextSection", () => {
  it("renders QB cards framed as context, without the retired stamp", () => {
    render(<QbContextSection cards={activeAudit().qb_context_cards} />);
    expect(screen.getByText("QB One")).toBeTruthy();
    // DG-111: "Context signal — not decision-grade." is retired here as it is on
    // the rest of Roster Audit. The FACT it carried — these readings are context
    // and nothing here grades the player — is said in a sentence instead.
    expect(screen.queryByText(/not decision-grade/i)).toBeNull();
    expect(screen.getByText(/not a grade on him/i)).toBeTruthy();
    // DG-109: the annotation still reaches the screen — it just says what it
    // means instead of printing the producer's key.
    expect(
      screen.getByText(/comparatively few touchdowns for his interceptions/i),
    ).toBeTruthy();
  });
  it("renders nothing when there are no cards", () => {
    const { container } = render(<QbContextSection cards={[]} />);
    expect(container.querySelector(".dg-roster__qb")).toBeNull();
  });
});
