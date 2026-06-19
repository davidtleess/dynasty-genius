// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { zRosterAuditResponse } from "../lib/api/zod.gen";
import { activeAudit, degradedAudit, emptyAudit, realPvoAudit } from "./fixtures";

describe("roster audit fixtures", () => {
  it("every fixture validates against the generated Zod schema", () => {
    for (const fx of [activeAudit(), degradedAudit(), realPvoAudit(), emptyAudit()]) {
      expect(() => zRosterAuditResponse.parse(fx)).not.toThrow();
    }
  });

  it("realPvoAudit carries free-text caveats and no market fields (Inc1 shape)", () => {
    const p = realPvoAudit().players[0];
    expect(p.caveats.some((c) => c.includes(" "))).toBe(true); // free-text sentence
    expect(p.caveats).toContain("no_market_overlay");
    expect(JSON.stringify(p)).not.toContain('"market_overlay"');
    expect(JSON.stringify(p)).not.toContain('"market_value"');
  });
});
