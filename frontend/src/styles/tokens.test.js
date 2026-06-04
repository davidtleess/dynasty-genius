import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const stylesDir = dirname(fileURLToPath(import.meta.url));
const tokensPath = resolve(stylesDir, "tokens.css");

const REQUIRED_TOKENS = [
  "--dg-model",
  "--dg-model-emphasis",
  "--dg-model-muted",
  "--dg-market",
  "--dg-market-emphasis",
  "--dg-market-muted",
  "--dg-cliff",
  "--dg-pos-qb",
  "--dg-pos-rb",
  "--dg-pos-wr",
  "--dg-pos-te",
  "--dg-dvs-floor",
  "--dg-dvs-ceiling",
  "--dg-font-sans",
  "--dg-font-mono",
  "--dg-text-sm",
  "--dg-text-base",
  "--dg-text-lg",
  "--dg-space-1",
  "--dg-space-2",
  "--dg-space-3",
  "--dg-space-4",
];

const COLOR_TOKENS = [
  "--dg-model",
  "--dg-model-emphasis",
  "--dg-model-muted",
  "--dg-market",
  "--dg-market-emphasis",
  "--dg-market-muted",
  "--dg-cliff",
  "--dg-pos-qb",
  "--dg-pos-rb",
  "--dg-pos-wr",
  "--dg-pos-te",
  "--dg-dvs-floor",
  "--dg-dvs-ceiling",
];

const MODEL_TOKENS = ["--dg-model", "--dg-model-emphasis", "--dg-model-muted"];
const MARKET_TOKENS = ["--dg-market", "--dg-market-emphasis", "--dg-market-muted"];
const POSITION_TOKENS = ["--dg-pos-qb", "--dg-pos-rb", "--dg-pos-wr", "--dg-pos-te"];

function readTokensCss() {
  return readFileSync(tokensPath, "utf8");
}

function parseCustomProperties(cssText) {
  return Object.fromEntries(
    [...cssText.matchAll(/(--dg-[a-z0-9-]+)\s*:\s*([^;]+);/g)].map(
      ([, name, value]) => [name, value.trim()],
    ),
  );
}

function parseOklchHue(value) {
  const match = value.match(
    /oklch\(\s*[\d.]+%?\s+[\d.]+%?\s+(-?[\d.]+)(?:deg)?(?:\s|\/|\))/i,
  );

  expect(match, `${value} must be an OKLCH color with an explicit hue`).not.toBeNull();

  const hue = Number(match[1]);
  return ((hue % 360) + 360) % 360;
}

function circularDistance(a, b) {
  const distance = Math.abs(a - b) % 360;
  return Math.min(distance, 360 - distance);
}

function isRedHue(hue) {
  return hue <= 30 || hue >= 350;
}

function isGreenHue(hue) {
  return hue >= 120 && hue <= 160;
}

describe("design tokens", () => {
  it("declares the required design-system token families", () => {
    const tokens = parseCustomProperties(readTokensCss());

    for (const tokenName of REQUIRED_TOKENS) {
      expect(tokens, `missing required token ${tokenName}`).toHaveProperty(tokenName);
    }
  });

  it("uses OKLCH hues and bans verdict-like red or green color tokens", () => {
    const cssText = readTokensCss();
    const tokens = parseCustomProperties(cssText);

    expect(cssText).not.toMatch(/\b(red|green)\b/i);

    for (const tokenName of COLOR_TOKENS) {
      const hue = parseOklchHue(tokens[tokenName]);

      expect(isRedHue(hue), `${tokenName} uses banned red hue ${hue}`).toBe(false);
      expect(isGreenHue(hue), `${tokenName} uses banned green hue ${hue}`).toBe(false);
    }
  });

  it("keeps model blue, market amber, and cliff warnings amber", () => {
    const tokens = parseCustomProperties(readTokensCss());
    const modelHue = parseOklchHue(tokens["--dg-model"]);
    const marketHue = parseOklchHue(tokens["--dg-market"]);
    const cliffHue = parseOklchHue(tokens["--dg-cliff"]);

    for (const tokenName of MODEL_TOKENS) {
      const hue = parseOklchHue(tokens[tokenName]);
      expect(
        hue,
        `${tokenName} must stay in the cool-blue model family`,
      ).toBeGreaterThanOrEqual(220);
      expect(
        hue,
        `${tokenName} must stay in the cool-blue model family`,
      ).toBeLessThanOrEqual(285);
    }

    for (const tokenName of MARKET_TOKENS) {
      const hue = parseOklchHue(tokens[tokenName]);
      expect(
        hue,
        `${tokenName} must stay in the amber market family`,
      ).toBeGreaterThanOrEqual(55);
      expect(
        hue,
        `${tokenName} must stay in the amber market family`,
      ).toBeLessThanOrEqual(95);
    }

    expect(circularDistance(modelHue, marketHue)).toBeGreaterThanOrEqual(90);
    expect(circularDistance(cliffHue, marketHue)).toBeLessThanOrEqual(12);
  });

  it("keeps position hues orthogonal to the model and market axes", () => {
    const tokens = parseCustomProperties(readTokensCss());
    const modelHue = parseOklchHue(tokens["--dg-model"]);
    const marketHue = parseOklchHue(tokens["--dg-market"]);

    for (const tokenName of POSITION_TOKENS) {
      const hue = parseOklchHue(tokens[tokenName]);

      expect(
        circularDistance(hue, modelHue),
        `${tokenName} must be distinct from model blue`,
      ).toBeGreaterThanOrEqual(35);
      expect(
        circularDistance(hue, marketHue),
        `${tokenName} must be distinct from market amber`,
      ).toBeGreaterThanOrEqual(35);
    }
  });
});
