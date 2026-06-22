// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LoadingState, ParseErrorState, UnavailableState } from "./LeaguePulseStates";

describe("LeaguePulseStates", () => {
  it("renders each non-ready state with neutral non-blank copy", () => {
    render(<LoadingState />);
    expect(screen.getByText(/loading league pulse/i)).toBeTruthy();

    render(<UnavailableState />);
    expect(screen.getByText(/league pulse unavailable/i)).toBeTruthy();

    render(<ParseErrorState />);
    expect(screen.getByText(/could not read league pulse/i)).toBeTruthy();
  });
});
