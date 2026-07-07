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

    for (const primitive of [
      "CaveatBlock",
      "ChartFrame",
      "DisclosureLine",
      "MetricCell",
      "PlayerIdentity",
      "SeriesSlot",
      "ValueHero",
    ]) {
      expect(
        source,
        `Daily What-Changed must import and consume the ${primitive} primitive instead of rebuilding it locally`,
      ).toContain(`../ui/${primitive}`);
    }
  });

  it("restarts the layout around one title, a desk-header tape, a feed, and a right rail", () => {
    const source = stripComments(readSurface());

    expect(source).toContain('className="dg-wc__desk-header"');
    expect(source).toContain('className="dg-wc__layout"');
    expect(source).toContain('className="dg-wc__feed"');
    expect(source).toContain('className="dg-wc__rail"');
    expect(source).toContain('className="dg-wc__diagnostics"');
    expect(source).toContain('className="dg-wc__receipts"');

    expect((source.match(/<h2\b/g) ?? []).length).toBe(1);
    expect(source).not.toContain("dg-wc__status");
    expect(source).not.toContain("dg-wc__generated");
  });

  it("renders player rows with identity, signed metric cells, and honest pending series slots", () => {
    const source = stripComments(readSurface());

    expect(source).toContain("<PlayerIdentity");
    expect(source).toContain('imageStatus={sleeperId ? "available" : "missing"}');
    expect(source).toContain(
      'imageSrc={sleeperId ? `/assets/headshots/${sleeperId}.jpg` : undefined}',
    );
    expect(source).not.toContain('imageStatus="missing"');
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

    expect(source).toContain("Current roster context");
    expect(source).toContain("today's movement");
  });

  it("keeps the Task-5 blast radius token-clean and removes local primitive shims", () => {
    const css = readCss();

    expect(css).toContain(".dg-wc__layout");
    expect(css).toContain(".dg-wc__feed");
    expect(css).toContain(".dg-wc__rail");
    expect(css).toContain(".dg-motion-daily-open");

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
