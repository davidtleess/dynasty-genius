// @vitest-environment jsdom
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { activeAudit, realPvoAudit } from "./fixtures";
import { RosterAuditTable } from "./RosterAuditTable";

describe("RosterAuditTable", () => {
  it("renders one row per player in contract order with primary columns", () => {
    render(<RosterAuditTable players={activeAudit().players} />);
    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(rows.length).toBe(2);
    expect(within(rows[0]).getByText("Active WR")).toBeTruthy();
    // DG-109: this used to assert the raw grade enum was on screen. The GRADE is
    // still on the row and still assert-able — the raw value rides `data-grade`
    // for CSS and tests, exactly as the trust strip keeps its own — and the cell
    // now says which model scored him instead of shouting `ACTIVE_B`.
    expect(rows[0].getAttribute("data-grade")).toBe("ACTIVE_B");
    expect(within(rows[0]).getByText("Scored by the active-player model")).toBeTruthy();
  });

  it("shows '—' for absent scores and de-emphasizes non-applicable rows", () => {
    render(<RosterAuditTable players={realPvoAudit().players} />);
    const row = within(screen.getByRole("table")).getAllByRole("row")[1];
    expect(within(row).getByText("—")).toBeTruthy();
    expect(row.getAttribute("data-applies")).toBe("false");
  });

  it("row-expand reveals detail (counter-argument, drivers, full caveats)", () => {
    render(<RosterAuditTable players={realPvoAudit().players} />);
    fireEvent.click(screen.getByRole("button", { name: /details for vet rb/i }));
    expect(screen.getByText(/do not use for dynasty decisions/i)).toBeTruthy();
  });

  it("uses neutral, non-verdict column labels (no verdict vocabulary)", () => {
    const { container } = render(<RosterAuditTable players={activeAudit().players} />);
    const headerText = container.querySelector("thead")?.textContent ?? "";
    expect(headerText).not.toMatch(/\b(sell|buy|hold|drop now|must|tier|win|loss)\b/i);
  });
});

const row = (id, pos) => ({
  player_id: id,
  full_name: id,
  position: pos,
  model_grade: "ACTIVE_B",
  model_status_applies: true,
  signal_completeness: 0.5,
  caveats: [],
});

describe("RosterAuditTable grouped", () => {
  it("renders a heading per group and its rows; trust cells preserved", () => {
    const groups = [
      { key: "WR", label: "WR", players: [row("wr1", "WR")] },
      { key: "QB", label: "QB", players: [row("qb1", "QB")] },
    ];
    const { container } = render(<RosterAuditTable groups={groups} />);

    const headings = container.querySelectorAll(".dg-roster__group-heading");
    expect([...headings].map((h) => h.textContent)).toEqual(["WR", "QB"]);
    expect(screen.getByText("wr1")).toBeTruthy();
    expect(screen.getAllByText("50%").length).toBeGreaterThan(0);
  });
});
