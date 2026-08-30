// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { degradedAudit } from "./fixtures";
import { RosterAuditHeader } from "./RosterAuditHeader";

describe("RosterAuditHeader", () => {
  it("shows status, per-position model_status, caveats, dropped count, disclaimer", () => {
    const a = degradedAudit();
    render(
      <RosterAuditHeader
        status={a.status}
        modelStatusByPosition={a.model_status_by_position}
        caveats={a.caveats}
        droppedPlayerCount={a.dropped_player_count}
      />,
    );
    // DG-109: the STATES are unchanged and still assert-able — they moved from
    // the visible text to the data attributes the CSS already keyed off — and
    // each one now also has to say itself in words.
    expect(screen.getByText(/something needs attention/i)).toBeTruthy();
    expect(document.querySelector('[data-status="degraded"]')).toBeTruthy();
    expect(screen.getByText("WR")).toBeTruthy();
    expect(
      document.querySelector('.dg-roster__chip[data-status="EXPERIMENTAL"]'),
    ).toBeTruthy();
    expect(screen.getByText(/experimental — not validated/i)).toBeTruthy();
    expect(screen.getByText(/1 .*dropped/i)).toBeTruthy();
    expect(screen.getByText(/experimental — not decision-grade/i)).toBeTruthy();
    // The market-scope caveat still reaches the screen; it just says what it is
    // rather than printing `no_market_overlay`.
    expect(screen.getByText(/market prices are deliberately left out/i)).toBeTruthy();
  });
});
