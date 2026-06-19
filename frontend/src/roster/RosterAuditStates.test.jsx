// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  ConfigErrorState,
  EmptyState,
  LoadingState,
  ParseErrorState,
  UnavailableState,
} from "./RosterAuditStates";

describe("RosterAuditStates", () => {
  it("renders each honest state with no blank output", () => {
    render(<LoadingState />);
    expect(screen.getByText(/loading roster audit/i)).toBeTruthy();
    render(<ConfigErrorState />);
    expect(screen.getByText(/roster not configured/i)).toBeTruthy();
    render(<UnavailableState />);
    expect(screen.getByText(/roster data unavailable/i)).toBeTruthy();
    render(<ParseErrorState />);
    expect(screen.getByText(/could not read roster audit/i)).toBeTruthy();
    render(<EmptyState />);
    expect(screen.getByText(/no rostered skill players/i)).toBeTruthy();
  });
});
