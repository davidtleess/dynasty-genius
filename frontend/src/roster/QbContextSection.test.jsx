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

  // DG-117. David's five quarterbacks all came back with
  // identity_coverage "NONE", which means the producer never fetched their
  // passing telemetry at all (roster_auditor.py:596-604), so the section
  // rendered fifteen em dashes and ten repeats of the same two caveats.
  // A dash wall is an empty column dressed up. Say why, once.
  describe("when no quarterback has any numbers", () => {
    const bare = (id, name) => ({
      player_id: id,
      full_name: name,
      identity_coverage: "NONE",
      context_role: "context_signal",
      epa_per_dropback: null,
      cpoe: null,
      dakota: null,
      qb_context_annotations: [],
      qb_context_caveats: ["missing_qb_college_context", "p2s_context_unavailable"],
      source_qb_context_annotations: "cfbd_qb_context_annotations",
      decision_supported: false,
    });

    it("explains the empty state instead of rendering a wall of dashes", () => {
      const { container } = render(
        <QbContextSection cards={[bare("1", "Jaxson Dart"), bare("2", "Mac Jones")]} />,
      );

      // The reason, from identity_coverage — not a guess about the data.
      expect(screen.getByText(/have not matched/i)).toBeTruthy();
      // The players stay reachable: their cards are still one press away.
      expect(screen.getByText("Jaxson Dart")).toBeTruthy();
      expect(screen.getByText("Mac Jones")).toBeTruthy();
      // The dashes go — the em dash left in the section lede is prose
      // punctuation, so the assertion is on the player rows themselves.
      for (const item of container.querySelectorAll(".dg-roster__qb-card")) {
        expect(item.textContent).not.toContain("—");
      }
      expect(container.textContent).not.toMatch(/completion percentage over expected/i);
      expect(container.textContent).not.toMatch(/dakota/i);
    });

    it("says a caveat every card carries once, not once per card", () => {
      render(
        <QbContextSection cards={[bare("1", "Jaxson Dart"), bare("2", "Mac Jones")]} />,
      );
      expect(screen.getAllByText(/no college context numbers/i).length).toBe(1);
      expect(screen.getByText(/true of every quarterback here/i)).toBeTruthy();
    });
  });

  it("keeps the numbers, and each card's own caveat, when there is data", () => {
    const cards = [
      ...activeAudit().qb_context_cards,
      {
        player_id: "p3",
        full_name: "QB Two",
        identity_coverage: "NONE",
        context_role: "context_signal",
        epa_per_dropback: null,
        cpoe: null,
        dakota: null,
        qb_context_annotations: [],
        qb_context_caveats: ["missing_qb_college_context"],
        source_qb_context_annotations: "cfbd_qb_context_annotations",
        decision_supported: false,
      },
    ];
    render(<QbContextSection cards={cards} />);

    // The card that has numbers still shows them, labelled.
    expect(screen.getByText(/0\.12/)).toBeTruthy();
    // The card that has none says so, in its own row, with its own reason.
    expect(screen.getByText(/no passing numbers/i)).toBeTruthy();
    // Nothing shared between these two cards, so nothing is hoisted.
    expect(screen.queryByText(/true of every quarterback here/i)).toBeNull();
  });
});
