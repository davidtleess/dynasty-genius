import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const surfacePath = resolve(here, "DailyWhatChanged.tsx");
const cssPath = resolve(here, "DailyWhatChanged.css");

function readSurface() {
  return readFileSync(surfacePath, "utf8");
}

function readCss() {
  return readFileSync(cssPath, "utf8");
}

function stripComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
}

describe("H2 reset Task 5 Daily What-Changed restart", () => {
  it("builds the daily-open surface from the governed primitive library", () => {
    const source = readSurface();

    // DG-111: CaveatBlock, ChartFrame and DisclosureLine left this surface with
    // the furniture they drew — the stacked caveat blocks, the "Movement
    // history / Series pending" panel, and the seven stamped disclosure lines.
    // DG-113 retires ValueHero with it: the masthead's "Your roster moved · 3"
    // figure was a COUNT where the morning needs a verdict, and the count now
    // lives inside a sentence that says what it means. The row primitives still
    // carry the surface.
    for (const primitive of ["MetricCell", "PlayerIdentity", "SeriesSlot"]) {
      expect(
        source,
        `Daily What-Changed must import and consume the ${primitive} primitive instead of rebuilding it locally`,
      ).toContain(`../ui/${primitive}`);
    }
  });

  it("stacks the morning read: header, verdict, worth a look, then the feed", () => {
    const source = stripComments(readSurface());

    expect(source).toContain('className="dg-wc__desk-header"');
    expect(source).toContain('className="dg-wc__feed"');
    // DG-113 §2.6: the right-hand rail leaves the page. It carried the
    // "Partial Market Sync" monospace tape, FEED DIAGNOSTICS and RECEIPTS —
    // three panels of plumbing occupying a fifth of the first viewport every
    // morning. Every fact is in the health sheet behind the freshness line.
    expect(source).not.toContain('className="dg-wc__layout"');
    expect(source).not.toContain('className="dg-wc__rail"');
    expect(source).not.toContain('className="dg-wc__diagnostics"');
    expect(source).not.toContain('className="dg-wc__receipts"');
    expect(source).not.toContain("<UiDailyTape");
    // …and the sheet keeps the receipt id, so the raw producer tokens still
    // have exactly one home on this surface and it is still declared.
    expect(source).toContain('data-testid="wc-health-sheet"');
    expect(source).toContain('data-testid="wc-provenance"');

    // The three questions, in order, each addressable.
    expect(source).toContain('data-testid="wc-verdict"');
    expect(source).toContain('data-testid="wc-worth-a-look"');
    expect(source).toContain('data-testid="wc-your-roster"');
    expect(source).toContain('data-testid="wc-around-the-league"');
    expect(source).toContain('data-testid="wc-where-you-stand"');

    expect((source.match(/<h2\b/g) ?? []).length).toBe(1);
    expect(source).not.toContain("dg-wc__status");
    expect(source).not.toContain("dg-wc__generated");
  });

  it("renders player rows with identity, signed metric cells, and honest pending series slots", () => {
    const source = stripComments(readSurface());

    expect(source).toContain("<PlayerIdentity");
    // Fail-safe headshot contract (discipline-reset finding #3): one helper is
    // the single source of truth. A present sleeper id claims the cached image;
    // a null/blank id degrades to the PlayerIdentity fallback chain — no row
    // type may hardcode an image or build a literal `undefined.jpg` request.
    expect(source).toContain("function headshotProps(");
    // Whitespace-safe: the id is trimmed before it is trusted (a blank/space-only
    // id degrades to the fallback, never a `/assets/headshots/   .jpg` request).
    expect(source).toContain("const id = sleeperId?.trim();");
    expect(source).toContain(
      'imageStatus: "available", imageSrc: `/assets/headshots/${id}.jpg`',
    );
    expect(source).toContain('imageStatus: "missing", imageSrc: undefined');
    expect(source).toContain("{...headshotProps(");
    expect(source).not.toContain('imageStatus="missing"');
    expect(source).not.toContain('imageStatus="available"');
    expect(source).not.toContain("${e.sleeper_id}.jpg");
    expect(source).toContain("<MetricCell");
    expect(source).toContain("<SeriesSlot");
    expect(source).toContain('status="pending"');
    expect(source).not.toContain("dg-wc__series-slot");
    expect(source).not.toContain("series pending</td>");
    expect(source).not.toContain("dg-wc__value");
  });

  it("keeps quiet days and exact zero deltas honest without empty chart boxes or false motion", () => {
    const source = stripComments(readSurface());

    expect(source).toContain("No player movement on this tape");
    expect(source).toContain("formatZeroDelta");
    expect(source).toContain("neutral dash");
    expect(source).not.toContain("No market top movers.");
    expect(source).not.toContain("Model no change.");
  });

  it("uses manager prose on the surface and keeps raw backend nouns out of visible copy", () => {
    const source = stripComments(readSurface());

    for (const backendNoun of [
      "current_not_delta=true",
      "starter weighted xvar",
      "total xvar capped",
      "top n xvar",
      "semantic_output_hash",
      "registry version",
      "model vintage",
    ]) {
      expect(
        source.toLowerCase(),
        `visible Daily What-Changed copy must not expose backend noun: ${backendNoun}`,
      ).not.toContain(backendNoun);
    }

    // DG-113 kills "Current roster context" and the five count rows under it.
    // Its worst line was "Starting lineup value: 97.39" printed directly above
    // "Weekly lineup strength: 97.39" — one number under two names — beside
    // "Card count: 5" and "David roster player count: 27". Prose-ified debug
    // output is still debug output; the block is now "Where you stand", and the
    // roster-value figures live on the Roster surface that can label them.
    expect(source).not.toContain("Current roster context");
    for (const debugLine of [
      "Starting lineup value",
      "Weekly lineup strength",
      "Top-asset core value",
      "Whole-roster value, capped",
      "Card count",
      "Partner ranking count",
      "David roster player count",
      "League roster count",
      "Total capacity",
    ]) {
      expect(
        source,
        `DG-113 retired the debug dump; "${debugLine}" must not come back`,
      ).not.toContain(debugLine);
    }
    expect(source).toContain("Where you stand");
  });

  it("keeps the Task-5 blast radius token-clean and removes local primitive shims", () => {
    const css = readCss();

    expect(css).toContain(".dg-wc__feed");
    expect(css).toContain(".dg-motion-daily-open");
    // DG-113: the two-column desk becomes one column. The rail's rules go with
    // the rail — a stylesheet keeping selectors for markup that no longer
    // exists is how a dead layout gets quietly rebuilt.
    expect(css).not.toContain(".dg-wc__layout");
    expect(css).not.toContain(".dg-wc__rail");

    for (const localShim of [
      ".dg-wc__tape",
      ".dg-wc__tape-fact",
      ".dg-wc__series-slot",
      ".dg-wc__value",
    ]) {
      expect(
        css,
        `Task 5 must use the primitive library, not ${localShim}`,
      ).not.toContain(localShim);
    }
  });
});
