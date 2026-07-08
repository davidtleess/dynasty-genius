import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const VISUAL_SMOKE_SPEC = resolve(process.cwd(), "e2e", "visual-smoke.spec.ts");

describe("visual smoke evidence contract", () => {
  it("pins mid-scroll capture, overflow, and painted-shell checks into the harness", () => {
    const source = readFileSync(VISUAL_SMOKE_SPEC, "utf8");

    for (const artifact of [
      "daily-open-desktop-mid-scroll.png",
      "daily-open-mobile-mid-scroll.png",
      "asset-primitive-capture-desktop-mid-scroll.png",
      "asset-primitive-capture-mobile-mid-scroll.png",
    ]) {
      expect(source).toContain(artifact);
    }

    expect(source).toContain("expectNoHorizontalOverflow");
    expect(source).toContain("document.documentElement.scrollWidth");
    expect(source).toContain("expectTrustStripPainted");
    expect(source).toContain('getByRole("banner", { name: "Trust strip" })');
    expect(source).toContain("content scroll through it");
  });
});
