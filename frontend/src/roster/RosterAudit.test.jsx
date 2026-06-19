// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { activeAudit } from "./fixtures";
import { RosterAudit } from "./RosterAudit";

function mockFetch(status, body) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status === 200,
    status,
    json: async () => body,
  });
}
afterEach(() => vi.restoreAllMocks());

describe("RosterAudit container", () => {
  it("renders header + table on 200 active", async () => {
    mockFetch(200, activeAudit());
    render(<RosterAudit />);
    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    expect(screen.getByText(/experimental — not decision-grade/i)).toBeTruthy();
  });
  it("renders config-error on 422", async () => {
    mockFetch(422, { detail: { error: "roster_config_error", message: "x" } });
    render(<RosterAudit />);
    await waitFor(() =>
      expect(screen.getByText(/roster not configured/i)).toBeTruthy(),
    );
  });
  it("renders unavailable on 503", async () => {
    mockFetch(503, {
      detail: { error: "roster_dependency_unavailable", message: "x" },
    });
    render(<RosterAudit />);
    await waitFor(() =>
      expect(screen.getByText(/roster data unavailable/i)).toBeTruthy(),
    );
  });
  it("renders parse-error when the body violates the contract", async () => {
    mockFetch(200, { bogus: true });
    render(<RosterAudit />);
    await waitFor(() =>
      expect(screen.getByText(/could not read roster audit/i)).toBeTruthy(),
    );
  });
});
