// The contract on the browser gate itself, run in jsdom so it fires in the
// unit suite the land gate already runs — not only when somebody remembers to
// run Playwright.
//
// DG-118: this file used to pin four screenshot filenames and three helper
// names. It could not tell you that the gate visited three surfaces out of ten,
// which is how every defect DG-116 and DG-117 fixed lived somewhere the gate
// never went. The check that matters is COVERAGE, so that is what it asserts
// now: every view of every destination in `destinations.ts` must be named in
// the e2e spec. Add a destination without gating it and this fails in a
// three-second suite instead of never.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { DESTINATIONS } from "../shell/destinations";

const VISUAL_SMOKE_SPEC = resolve(process.cwd(), "e2e", "visual-smoke.spec.ts");
const source = readFileSync(VISUAL_SMOKE_SPEC, "utf8");

// The spec's own prose is part of what this file pins — it is where the coverage
// boundary is stated — so most checks read the whole file. The "no rule was
// excluded" check must not, because the sentence PROMISING no rule is excluded
// names the three APIs and would fail itself. Comment lines are dropped for that
// one check, and it looks for a CALL (the open paren), not a mention.
const code = source
  .split("\n")
  .filter((line) => !/^\s*(\/\/|\*|\/\*)/.test(line))
  .join("\n");

describe("visual smoke evidence contract", () => {
  it("gates every view of every nav destination", () => {
    const missing = DESTINATIONS.flatMap((destination) =>
      destination.views
        .filter((view) => !source.includes(`surface: "${view.surface}"`))
        .map((view) => `${destination.label} · ${view.label} (${view.surface})`),
    );

    expect(
      missing,
      "these nav destinations are reachable by David and the browser gate never visits them:",
    ).toEqual([]);
  });

  it("visits both breakpoints, not just the desktop one", () => {
    // Roster Audit at 390 scrolled the page 185px sideways and Model Trust
    // 665px, and both looked fine at 1440. One width is not a gate.
    expect(source).toContain("width: 1440");
    expect(source).toContain("width: 390");
  });

  it("pins mid-scroll capture, overflow, and painted-shell checks into the harness", () => {
    // Screenshot names are built as `${artifacts}-${label}[-mid-scroll].png`,
    // so the parts are pinned rather than the whole filenames.
    expect(source).toContain("-mid-scroll.png");
    expect(source).toContain('artifacts: "daily-open"');
    expect(source).toContain('artifacts: "asset-primitive-capture"');

    expect(source).toContain("expectNoHorizontalOverflow");
    expect(source).toContain("document.documentElement.scrollWidth");
    expect(source).toContain("expectTrustStripPainted");
    expect(source).toContain('getByRole("banner", { name: "Trust strip" })');
    expect(source).toContain("content scroll through it");
  });

  it("keeps the guards against a clean-looking empty screen", () => {
    // A surface whose backend is unavailable renders an error card with no rows
    // and a small, clean axe count. Three independent assertions stand against
    // reading that as a pass; none of them may be quietly dropped.
    expect(source).toContain("expectContentPresent");
    expect(source).toContain("assertEveryReadFixtured");
    expect(source).toContain("minMainText");
  });

  it("gates the copy dictionary in a real browser, using the shared rule", () => {
    // "xVAR" slipped the whole DG-109 dictionary because it is four characters
    // with three capitals. The rule that sees it lives in renderRule.ts and the
    // spec must IMPORT it — a re-implementation here would drift the day the
    // jargon list grows.
    expect(source).toContain('from "../src/lib/renderRule"');
    expect(source).toContain("findRawCopy");
    expect(source).toContain("checkVisibility");
  });

  it("uses axe's composited colours and never buys green by excluding a rule", () => {
    // getComputedStyle reports 0 failures where axe's composited sweep finds
    // 21, because axe blends ancestor opacity and getComputedStyle does not.
    expect(source).toContain("contrast_readings");
    expect(source).toContain('exercisedRules.has("color-contrast")');
    expect(code).not.toMatch(/disableRules\(|withRules\(|\.exclude\(/);
  });

  it("states which motion path is gated, in the spec's own words", () => {
    // The old gate ran under reduced motion only, so the default path every
    // reader without a preference actually sees had no browser-level coverage
    // at all — and a mid-animation axe run was what made it a 3-pass/4-fail
    // coin flip in the first place.
    expect(source).toContain('reducedMotion: "reduce"');
    expect(source).toContain('reducedMotion: "no-preference"');
    expect(source).toContain("settleMotion");
    expect(source).toContain("MOTION_QUIET_MS");
  });
});
