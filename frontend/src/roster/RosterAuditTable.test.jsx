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
    expect(
      within(rows[0]).getByText(/VALIDATED|PROVISIONAL|EXPERIMENTAL|ACTIVE_B/),
    ).toBeTruthy();
  });

  it("shows '—' for absent scores and de-emphasizes non-applicable rows", () => {
    render(<RosterAuditTable players={realPvoAudit().players} />);
    const row = within(screen.getByRole("table")).getAllByRole("row")[1];
    expect(within(row).getByText("—")).toBeTruthy();
    expect(row.getAttribute("data-applies")).toBe("false");
  });

  it("row-expand reveals detail (counter-argument, drivers, full caveats)", () => {
    render(<RosterAuditTable players={realPvoAudit().players} />);
    fireEvent.click(screen.getByRole("button", { name: /expand vet rb/i }));
    expect(screen.getByText(/do not use for dynasty decisions/i)).toBeTruthy();
  });

  it("uses neutral, non-verdict column labels (no verdict vocabulary)", () => {
    const { container } = render(<RosterAuditTable players={activeAudit().players} />);
    const headerText = container.querySelector("thead")?.textContent ?? "";
    expect(headerText).not.toMatch(/\b(sell|buy|hold|drop now|must|tier|win|loss)\b/i);
  });
});
