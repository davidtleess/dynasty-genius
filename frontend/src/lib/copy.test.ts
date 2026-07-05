import { describe, expect, it, vi } from "vitest";

async function loadCopy() {
  return import("./copy");
}

describe("H1 copy helpers", () => {
  it("translates exact and real-shape status tokens without losing suffix precision", () => {
    return loadCopy().then(({ describeStatusToken }) => {
      expect(describeStatusToken("density_baseline_insufficient")).toBe(
        "Waiver-pool valuation coverage is below the reporting floor; replacement-cost ranges cannot be verified",
      );
      expect(describeStatusToken("waiver_range_unavailable")).toBe(
        "Waiver range unavailable",
      );
      expect(describeStatusToken("waiver_range_unavailable:stale_snapshot")).toBe(
        "Waiver range unavailable (stale_snapshot)",
      );
      expect(
        describeStatusToken("WR_waiver_range_unavailable_recovery_unverifiable"),
      ).toBe("WR waiver range unavailable (recovery_unverifiable)");
      expect(describeStatusToken("league_pulse_artifact_state_2026-06-22")).toBe(
        "League Pulse artifact state (2026-06-22)",
      );
    });
  });

  it("renders unmapped status tokens raw and warns without crashing", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});

    return loadCopy().then(({ describeStatusToken }) => {
      expect(describeStatusToken("some_new_backend_token")).toBe(
        "some_new_backend_token",
      );
      expect(warn).toHaveBeenCalledWith(
        "Unmapped status token",
        "some_new_backend_token",
      );
    });
  });

  it("formats capture timestamps deterministically for America/New_York", () => {
    return loadCopy().then(({ formatCaptureTimestamp }) => {
      expect(formatCaptureTimestamp("2026-07-05T13:45:00Z")).toBe(
        "Jul 5, 2026, 9:45 AM EDT",
      );
      expect(formatCaptureTimestamp(null)).toBe("—");
      expect(formatCaptureTimestamp(undefined)).toBe("—");
      expect(formatCaptureTimestamp("still-not-a-date")).toBe("still-not-a-date");
      expect(formatCaptureTimestamp("still-not-a-date")).not.toMatch(
        /NaN|Invalid Date/,
      );
    });
  });
});
