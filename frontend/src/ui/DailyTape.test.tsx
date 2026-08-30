// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("DailyTape", () => {
  it("speaks in dynasty-manager prose while preserving raw values in titles", async () => {
    const { DailyTape } = await import("./DailyTape");

    render(
      <DailyTape
        capture={{
          consecutiveDays: 32,
          lastCaptureAt: "2026-07-05T10:15:00-04:00",
          status: "ok",
        }}
        provenance={{
          registryVersion: 4,
          modelVintage: "ok",
          status: "ok",
        }}
      />,
    );

    expect(
      screen.getByText(/market sync active: 32 consecutive days tracked/i),
    ).toBeTruthy();
    expect(screen.getByText(/projection update: july 5, current/i)).toBeTruthy();
    // DG-111: the third "Status: Synced / Status: Degraded" stamp is retired.
    // A clean tape says nothing; a degraded one says what it means.
    expect(screen.queryByText(/status: synced/i)).toBeNull();
    expect(
      screen.queryByText(/registry version|model vintage|capture streak/i),
    ).toBeNull();
    // DG-109: the receipt now names the field in words AND keeps the raw field
    // name, through the one shared `receiptDetail` helper.
    const provenanceTitle = screen
      .getByText(/projection update/i)
      .getAttribute("title");
    expect(provenanceTitle).toContain("Model registry version — 4");
    expect(provenanceTitle).toContain("(from registry_version)");
  });

  it("treats date-only capture values as local calendar dates", async () => {
    const { DailyTape } = await import("./DailyTape");

    render(
      <DailyTape
        capture={{
          consecutiveDays: 12,
          lastCaptureAt: "2026-07-05",
          status: "ok",
        }}
        provenance={{
          registryVersion: 4,
          modelVintage: "ok",
          status: "ok",
        }}
      />,
    );

    expect(screen.getByText(/projection update: july 5, current/i)).toBeTruthy();
    expect(screen.queryByText(/projection update: july 4/i)).toBeNull();
  });
});
