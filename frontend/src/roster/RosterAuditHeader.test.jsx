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
    expect(screen.getByText(/degraded/i)).toBeTruthy();
    expect(screen.getByText("WR")).toBeTruthy();
    expect(screen.getByText("EXPERIMENTAL")).toBeTruthy();
    expect(screen.getByText(/1 .*dropped/i)).toBeTruthy();
    expect(screen.getByText(/experimental — not decision-grade/i)).toBeTruthy();
    expect(screen.getByText(/no_market_overlay/)).toBeTruthy();
  });
});
