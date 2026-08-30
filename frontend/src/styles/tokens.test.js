import { readdirSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const stylesDir = dirname(fileURLToPath(import.meta.url));
const srcDir = resolve(stylesDir, "..");
const tokensPath = resolve(stylesDir, "tokens.css");

const REQUIRED_TOKENS = [
  "--dg-model",
  "--dg-model-emphasis",
  "--dg-model-muted",
  "--dg-market",
  "--dg-market-emphasis",
  "--dg-market-muted",
  "--dg-cliff",
  "--dg-chrome",
  "--dg-chrome-strong",
  "--dg-chrome-surface",
  "--dg-up",
  "--dg-down",
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

/*
 * Every color token EXCEPT the two direction tokens. DG-115 removed the four
 * --dg-pos-* position hues and --dg-dvs-floor from the palette (five tokens,
 * zero consumers, never rendered a pixel), and with them the orthogonality
 * test that guarded the position family: it guarded colors that no longer
 * exist. visualFoundation.test.js now fails on ANY token nobody consumes, so
 * a re-added position hue would have to be painted somewhere to survive.
 */
const NON_DIRECTION_COLOR_TOKENS = [
  "--dg-model",
  "--dg-model-emphasis",
  "--dg-model-muted",
  "--dg-market",
  "--dg-market-emphasis",
  "--dg-market-muted",
  "--dg-cliff",
  "--dg-chrome",
  "--dg-chrome-strong",
  "--dg-chrome-surface",
  "--dg-dvs-ceiling",
];

const MODEL_TOKENS = ["--dg-model", "--dg-model-emphasis", "--dg-model-muted"];
const MARKET_TOKENS = ["--dg-market", "--dg-market-emphasis", "--dg-market-muted"];

/*
 * A buy/sell verdict, in any of the words this product could plausibly use for
 * one. Matched against token NAMES and against CSS SELECTORS — never against
 * prose, because the prose is now allowed to say these things out loud.
 */
const VERDICT_WORD =
  /(?:^|[^a-z])(buy|sell|verdict|recommend(?:ation|ed)?|nominate)(?:[^a-z]|$)/i;

function readTokensCss() {
  return readFileSync(tokensPath, "utf8");
}

function stripComments(cssText) {
  return cssText.replace(/\/\*[\s\S]*?\*\//g, "");
}

function parseCustomProperties(cssText) {
  // Comments first: a token NAME mentioned in prose is not a declaration.
  return Object.fromEntries(
    [...stripComments(cssText).matchAll(/(--dg-[a-z0-9-]+)\s*:\s*([^;]+);/g)].map(
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

function isDownHue(hue) {
  return hue <= 30 || hue >= 350;
}

function isUpHue(hue) {
  return hue >= 120 && hue <= 160;
}

function cssFiles() {
  const files = [];
  const stack = [srcDir];
  while (stack.length > 0) {
    const dir = stack.pop();
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const fullPath = resolve(dir, entry.name);
      if (entry.isDirectory()) {
        stack.push(fullPath);
      } else if (entry.isFile() && fullPath.endsWith(".css")) {
        files.push(fullPath);
      }
    }
  }
  return files.sort();
}

/** Every `selector { body }` rule in a stylesheet, comments already stripped. */
function cssRules(cssText) {
  return [...stripComments(cssText).matchAll(/([^{}]+)\{([^{}]*)\}/g)].map(
    ([, selector, body]) => ({ selector: selector.trim(), body }),
  );
}

describe("design tokens", () => {
  it("declares the required design-system token families", () => {
    const tokens = parseCustomProperties(readTokensCss());

    for (const tokenName of REQUIRED_TOKENS) {
      expect(tokens, `missing required token ${tokenName}`).toHaveProperty(tokenName);
    }
  });

  /*
   * ── THE VERDICT-HUE BAN, AMENDED BY DG-115 ─────────────────────────────
   *
   * What it used to say: no token anywhere may sit in the red arc (hue <= 30
   * or >= 350) or the green arc (120-160), and the word "red" or "green" may
   * not appear in tokens.css at all. It existed to stop the product implying a
   * recommendation through color at a time when the product was forbidden to
   * make one in words either.
   *
   * Why it changed: David ruled on 2026-08-30, verbatim option label,
   * "Green up / red down" — deltas get direction color. A direction is
   * arithmetic, not advice: it says a number went up, which is a fact the sign
   * in front of it already states. Deleting the ban was never the answer,
   * because the thing it actually guards is still true — the reason a hue
   * cannot carry a buy/sell call is that a hue has no room for the reasoning
   * or the receipt underneath it, and that is as true today as it was before
   * the frontend was allowed to speak plainly.
   *
   * So the ban is RE-POINTED, not relaxed. It now says:
   *   1. Red and green are legal in exactly two tokens, --dg-up and --dg-down,
   *      and those two must actually BE the direction hues — a repaint of
   *      --dg-up to amber fails here, so the direction family cannot be
   *      quietly emptied of meaning.
   *   2. Every other color token stays out of both arcs, exactly as before.
   *   3. No token may be NAMED for a buy/sell verdict, and no CSS rule whose
   *      selector names one may paint itself with a SIGNAL color — direction,
   *      lane, or warning. That is the real ban: the product may write
   *      "Sell-high window: Jaxson Dart" in a sentence, where the reason and
   *      the receipt travel with it, but it may not paint that call a color
   *      and let the color do the arguing.
   *
   * The same amendment is mirrored in tokensI1.test.js, which carries the same
   * guard over both theme scopes.
   */
  it("bans verdict color while permitting direction color", () => {
    const cssText = readTokensCss();
    const tokens = parseCustomProperties(cssText);

    // Named CSS colors, in declarations only — the amended rule has to be
    // explainable in the comments above without tripping its own check.
    expect(stripComments(cssText)).not.toMatch(/\b(red|green)\b/i);

    for (const tokenName of Object.keys(tokens)) {
      expect(
        VERDICT_WORD.test(tokenName),
        `${tokenName} is named for a buy/sell verdict — color may not carry a recommendation`,
      ).toBe(false);
    }

    for (const tokenName of NON_DIRECTION_COLOR_TOKENS) {
      const hue = parseOklchHue(tokens[tokenName]);

      expect(isDownHue(hue), `${tokenName} uses reserved down hue ${hue}`).toBe(false);
      expect(isUpHue(hue), `${tokenName} uses reserved up hue ${hue}`).toBe(false);
    }

    expect(isUpHue(parseOklchHue(tokens["--dg-up"]))).toBe(true);
    expect(isDownHue(parseOklchHue(tokens["--dg-down"]))).toBe(true);
  });

  /*
   * The half of the ban that has teeth on the SCREEN rather than in the
   * palette. A signal color is one that makes a claim: direction (up/down),
   * lane (model/market), or warning (cliff/caveat). Neutral text, chrome and
   * surface tokens make none — the Track Record's `.dg-sb__verdict` is the
   * model's own report card written in prose, sized and muted with neutral
   * tokens, and it is exactly the kind of verdict this product SHOULD state.
   * What it may never do is hand the argument to a hue.
   */
  it("keeps signal color off anything named for a verdict", () => {
    const SIGNAL_TOKEN =
      /var\(--dg-(?:up|down|model|model-emphasis|model-muted|market|market-emphasis|market-muted|cliff|caveat)[,)]/;
    const painted = [];

    for (const filePath of cssFiles()) {
      for (const { selector, body } of cssRules(readFileSync(filePath, "utf8"))) {
        if (!VERDICT_WORD.test(selector)) continue;
        if (!SIGNAL_TOKEN.test(body)) continue;
        painted.push(`${relative(srcDir, filePath)} ${selector}`);
      }
    }

    expect(
      painted,
      "a buy/sell call is a sentence with a receipt under it, never a color",
    ).toEqual([]);
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

  it("keeps the direction hues far enough from the lanes to stay distinguishable", () => {
    const tokens = parseCustomProperties(readTokensCss());
    const modelHue = parseOklchHue(tokens["--dg-model"]);
    const marketHue = parseOklchHue(tokens["--dg-market"]);

    for (const tokenName of ["--dg-up", "--dg-down"]) {
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
