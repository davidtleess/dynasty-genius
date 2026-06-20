// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RosterAuditControls } from "./RosterAuditControls";

const base = {
  sortKey: "none",
  groupBy: "none",
  positions: [],
  prospect: "all",
  allPositions: ["QB", "RB", "WR", "TE"],
  filteredOutCount: 0,
  onChange: () => {},
  onReset: () => {},
};

describe("RosterAuditControls", () => {
  it("renders sort, group, prospect controls and the compact disclaimer", () => {
    render(<RosterAuditControls {...base} />);
    expect(screen.getByLabelText(/sort by/i)).toBeTruthy();
    expect(screen.getByLabelText(/group by/i)).toBeTruthy();
    expect(screen.getByLabelText(/players/i)).toBeTruthy();
    const groupOptions = Array.from(screen.getByLabelText(/group by/i).options).map(
      (option) => [option.value, option.textContent],
    );
    expect(groupOptions).toContainEqual(["xvar_bracket", "xVAR bracket"]);
    expect(screen.getByText(/experimental — not decision-grade/i)).toBeTruthy();
  });

  it("emits sort change", () => {
    const onChange = vi.fn();
    render(<RosterAuditControls {...base} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText(/sort by/i), {
      target: { value: "xvar" },
    });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ sortKey: "xvar" }));
  });

  it("shows filtered-out count + reset only when rows are filtered out", () => {
    const onReset = vi.fn();
    const { rerender } = render(<RosterAuditControls {...base} filteredOutCount={0} />);
    expect(screen.queryByRole("button", { name: /reset/i })).toBeNull();

    rerender(<RosterAuditControls {...base} filteredOutCount={3} onReset={onReset} />);

    expect(screen.getByText(/3 .*filtered out/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /reset/i }));
    expect(onReset).toHaveBeenCalled();
  });

  it("default All (positions=[]) shows every checkbox checked; toggling one off excludes only it", () => {
    const onChange = vi.fn();
    render(<RosterAuditControls {...base} positions={[]} onChange={onChange} />);

    const boxes = screen.getAllByRole("checkbox");
    expect(boxes.length).toBe(4);
    expect(boxes.every((b) => b.checked)).toBe(true);

    fireEvent.click(screen.getByLabelText("QB"));

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ positions: ["RB", "WR", "TE"] }),
    );
  });
});
