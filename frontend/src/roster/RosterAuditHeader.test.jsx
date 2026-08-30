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
    // each one now also has to say itself in words. DG-111 says the envelope
    // state as a sentence instead of a "Status:" chip; the data attribute the
    // CSS and this test key off is untouched on the branch that carries it.
    expect(document.querySelector('[data-status="degraded"]')).toBeTruthy();
    expect(screen.getByText("WR")).toBeTruthy();
    expect(
      document.querySelector('.dg-roster__chip[data-status="EXPERIMENTAL"]'),
    ).toBeTruthy();
    expect(screen.getByText(/not proven/i)).toBeTruthy();
    expect(screen.getByText(/1 .*dropped/i)).toBeTruthy();
    // DG-111: the "Experimental — not decision-grade." stamp is retired from
    // this surface (it rendered twice: header and filter bar). A degraded
    // roster read still says so in a sentence.
    expect(screen.queryByText(/experimental — not decision-grade/i)).toBeNull();
    expect(screen.getByText(/this roster read came back degraded/i)).toBeTruthy();
    // The market-scope caveat still reaches the screen; it just says what it is
    // rather than printing `no_market_overlay`.
    expect(screen.getByText(/market prices are deliberately left out/i)).toBeTruthy();
  });

  // DG-117. The chips read "RB checked out in testing" on a surface David
  // opens in one click — crew vocabulary for a state a manager has never been
  // told the subject of. Two things had to change and neither is the state
  // itself: the words become plain English, and the row acquires a subject so
  // the chips are about something.
  it("says what the chips are about, in the manager's language, not QA's", () => {
    render(
      <RosterAuditHeader
        status="active"
        modelStatusByPosition={{
          QB: "PROVISIONAL",
          RB: "VALIDATED",
          TE: "EXPERIMENTAL",
        }}
        caveats={[]}
        droppedPlayerCount={0}
      />,
    );

    // The subject: without it the chips name a state of nothing.
    expect(screen.getByText(/our active-player model/i)).toBeTruthy();

    // The three states, each still distinguishable and still carried on the
    // data attribute the CSS and the tests key off.
    expect(screen.getByText(/passed its accuracy checks/i)).toBeTruthy();
    expect(screen.getByText(/missed an accuracy one/i)).toBeTruthy();
    expect(screen.getByText(/not proven/i)).toBeTruthy();
    expect(document.querySelector('[data-status="VALIDATED"]')).toBeTruthy();
    expect(document.querySelector('[data-status="PROVISIONAL"]')).toBeTruthy();
    expect(document.querySelector('[data-status="EXPERIMENTAL"]')).toBeTruthy();

    // The QA register, gone.
    expect(screen.queryByText(/checked out in testing/i)).toBeNull();
    expect(screen.queryByText(/^provisional$/i)).toBeNull();
  });
});
