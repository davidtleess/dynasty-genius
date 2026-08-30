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

  // DG-117. On David's live roster this table was 23 of 27 rows of "Not scored
  // yet / n/a / —", with two adjacent columns saying nothing at all.
  //
  // `model_status_applies` is `engine_used == "engine_b"`
  // (roster_audit_models.py:264) — it was FALSE on all 27 rows, so the column
  // was 27 identical "n/a"s. Worse, it was misleading where it did vary: the
  // four players who ARE scored are scored by the rookie model, and the column
  // told him "n/a" about them too. The fact it carried — which model scored
  // him — is what the neighbouring Model status cell already says in words, so
  // the column goes and nothing goes with it.
  it("does not render a column whose only value is that it does not apply", () => {
    const { container } = render(<RosterAuditTable players={realPvoAudit().players} />);
    const headers = [...container.querySelectorAll("thead th")].map(
      (th) => th.textContent,
    );

    expect(headers).not.toContain("Model status applies");
    expect(within(screen.getByRole("table")).queryByText("n/a")).toBeNull();
    expect(headers).not.toContain("Model grade");

    // The fact survives, in the dictionary's own name for the field — the same
    // name the player card gives it, so one field has one name in both places.
    expect(headers).toContain("Model status");
    const row = within(screen.getByRole("table")).getAllByRole("row")[1];
    expect(within(row).getByText("Not scored yet")).toBeTruthy();
    // And the raw grade still rides the row for CSS and tests.
    expect(row.getAttribute("data-grade")).toBe("PRE_MODEL");
  });

  it("says why the blank value cells are blank, once, under the table", () => {
    render(<RosterAuditTable players={realPvoAudit().players} />);

    // Named by the column's own name, not a sixth synonym for the same field.
    const note = screen.getByText(/no dynasty value yet/i);
    expect(note.textContent).toMatch(/1 of these 1 players/i);
    // The honest half: a blank is a refusal to guess, and the reason is one
    // press away on the row itself.
    expect(note.textContent).toMatch(/blank rather than guessed/i);
    expect(note.textContent).toMatch(/details/i);
  });

  it("says nothing about unscored players when every player is scored", () => {
    render(<RosterAuditTable players={activeAudit().players} />);
    expect(screen.queryByText(/no dynasty value yet/i)).toBeNull();
  });

  // DG-117 defect 1: at 390 this table is 559px inside a 358px column and it
  // took the whole PAGE sideways with it — 185px of horizontal scroll, every
  // other element on the surface squeezed. A wide table scrolls inside its own
  // container or it does not scroll at all.
  it("scrolls inside its own container instead of taking the page sideways", () => {
    const { container } = render(<RosterAuditTable players={activeAudit().players} />);
    const table = container.querySelector("table");
    const scroller = table.closest(".dg-table-scroll");

    expect(scroller).toBeTruthy();
    // Reachable by keyboard: a scroll region a mouse can drag and a keyboard
    // cannot is a surface a keyboard user cannot read. A NAMED <section> is a
    // region by element, so the reader who tabs in is told what they landed in.
    expect(scroller.tagName).toBe("SECTION");
    expect(scroller.getAttribute("tabindex")).toBe("0");
    expect(scroller.getAttribute("aria-label")).toBeTruthy();
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
