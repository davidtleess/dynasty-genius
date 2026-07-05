// @vitest-environment jsdom
import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { leaguePulseResponse } from "./fixtures";
import { LeaguePulse } from "./LeaguePulse";

function mockFetch(status, body) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status === 200,
    status,
    json: async () => body,
  });
}

afterEach(() => vi.restoreAllMocks());

describe("LeaguePulse container", () => {
  it("fetches the frozen Inc1 endpoint and renders a ready surface for a valid payload", async () => {
    mockFetch(200, leaguePulseResponse());

    render(<LeaguePulse />);

    expect(screen.getByText(/loading league pulse/i)).toBeTruthy();
    await waitFor(() =>
      expect(screen.getByRole("region", { name: /league pulse/i })).toBeTruthy(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/league/pulse");
  });

  it("keeps degraded artifact-state responses in the ready view", async () => {
    mockFetch(200, leaguePulseResponse({ status: "degraded" }));

    render(<LeaguePulse />);

    const surface = await screen.findByTestId("league-pulse-ready");
    expect(surface.dataset.status).toBe("degraded");
    expect(screen.queryByText(/league pulse unavailable/i)).toBeNull();
  });

  it("renders the honesty header inside the ready region", async () => {
    mockFetch(200, leaguePulseResponse());

    render(<LeaguePulse />);

    const surface = await screen.findByTestId("league-pulse-ready");
    expect(
      within(surface).getByRole("banner", { name: /league pulse status/i }),
    ).toBeTruthy();
    expect(within(surface).getByText(/not decision-grade/i)).toBeTruthy();
    const capturedAt = within(surface).getByText("as of Jun 22, 2026, 2:00 PM EDT");
    expect(capturedAt).toBeTruthy();
    expect(capturedAt.getAttribute("title")).toBe("2026-06-22T18:00:00Z");
  });

  it("renders partner rankings inside the ready region", async () => {
    mockFetch(200, leaguePulseResponse());

    render(<LeaguePulse />);

    const surface = await screen.findByTestId("league-pulse-ready");
    expect(
      within(surface).getByRole("region", { name: /partner rankings/i }),
    ).toBeTruthy();
    expect(within(surface).getByText(/market-influenced context/i)).toBeTruthy();
  });

  it("renders team postures and values inside the ready region", async () => {
    mockFetch(200, leaguePulseResponse());

    render(<LeaguePulse />);

    const surface = await screen.findByTestId("league-pulse-ready");
    expect(
      within(surface).getByRole("region", { name: /team postures/i }),
    ).toBeTruthy();
    expect(
      within(surface).getByRole("region", { name: /team value overview/i }),
    ).toBeTruthy();
  });

  it("renders opportunity cards inside the ready region", async () => {
    mockFetch(200, leaguePulseResponse());

    render(<LeaguePulse />);

    const surface = await screen.findByTestId("league-pulse-ready");
    expect(
      within(surface).getByRole("region", {
        name: /model-native opportunity cards/i,
      }),
    ).toBeTruthy();
    expect(
      within(surface).getByRole("region", {
        name: /market overlay opportunity cards/i,
      }),
    ).toBeTruthy();
  });

  it("renders unavailable for every non-OK status, including 422", async () => {
    mockFetch(422, { detail: { error: "not_a_league_pulse_route_state" } });

    render(<LeaguePulse />);

    await waitFor(() =>
      expect(screen.getByText(/league pulse unavailable/i)).toBeTruthy(),
    );
    expect(screen.queryByText(/not configured/i)).toBeNull();
  });

  it("renders parse-error when JSON parsing fails", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new Error("bad json");
      },
    });

    render(<LeaguePulse />);

    await waitFor(() =>
      expect(screen.getByText(/could not read league pulse/i)).toBeTruthy(),
    );
  });

  it("renders parse-error when the body violates the LeaguePulseResponse contract", async () => {
    mockFetch(200, { bogus: true });

    render(<LeaguePulse />);

    await waitFor(() =>
      expect(screen.getByText(/could not read league pulse/i)).toBeTruthy(),
    );
  });
});
