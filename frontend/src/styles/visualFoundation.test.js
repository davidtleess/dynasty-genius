/*
 * DG-115 — the visual foundation contract (DG-091 phase 2B, wave 1).
 *
 * Waves 2 and 3 build the morning read, the five-item nav and the phone shell
 * on top of these tokens, so the structure they need is pinned here rather
 * than left to whoever edits tokens.css next:
 *
 *   - a display type scale ABOVE --dg-text-lg (the morning-read hierarchy
 *     cannot be built on three steps topping out at 18px), with weight and
 *     line-height tokens;
 *   - spacing steps 5-6 for section rhythm, and three radius tokens;
 *   - a NEUTRAL chrome family, so the shell stops painting itself in the data
 *     lanes. The two-lane law means exactly what it says: blue = the model
 *     computed this, amber = the market says this, and nothing else. Nav,
 *     the inspector toggle and the trust strip are chrome, not data;
 *   - direction color (David's 2026-08-30 panel: "Green up / red down");
 *   - flat elevation, declared rather than assumed;
 *   - and no token may sit in the file with nobody consuming it.
 *
 * The verdict-hue ban itself is NOT here — it stays in tokens.test.js and
 * tokensI1.test.js where it has always lived, re-pointed by DG-115 at genuine
 * buy/sell verdict styling. Read the amended rule in tokens.test.js.
 */
import { readdirSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const stylesDir = dirname(fileURLToPath(import.meta.url));
const srcDir = resolve(stylesDir, "..");
const frontendRoot = resolve(srcDir, "..");
const tokensPath = resolve(stylesDir, "tokens.css");

/** Shell chrome: the frame around the product, never a reading of the data. */
const CHROME_FILES = [
  "shell/AppShell.css",
  "shell/TrustStrip.css",
  "command/CommandPalette.css",
];

const TYPE_SCALE = [
  "--dg-text-sm",
  "--dg-text-base",
  "--dg-text-lg",
  "--dg-text-xl",
  "--dg-text-2xl",
  "--dg-text-3xl",
  "--dg-text-4xl",
];

const WEIGHT_TOKENS = [
  "--dg-weight-medium",
  "--dg-weight-semibold",
  "--dg-weight-bold",
];
const LEADING_TOKENS = [
  "--dg-leading-tight",
  "--dg-leading-snug",
  "--dg-leading-normal",
];
const SPACING_SCALE = [
  "--dg-space-1",
  "--dg-space-2",
  "--dg-space-3",
  "--dg-space-4",
  "--dg-space-5",
  "--dg-space-6",
];
const RADIUS_TOKENS = ["--dg-radius-control", "--dg-radius-card", "--dg-radius-round"];
const CHROME_TOKENS = ["--dg-chrome", "--dg-chrome-strong", "--dg-chrome-surface"];
const DIRECTION_TOKENS = ["--dg-up", "--dg-down"];

function readTokensCss() {
  return readFileSync(tokensPath, "utf8");
}

function stripComments(cssText) {
  return cssText.replace(/\/\*[\s\S]*?\*\//g, "");
}

function parseScope(cssText, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = stripComments(cssText).match(
    new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\n\\}`, "m"),
  );
  expect(match, `${selector} block must exist in tokens.css`).not.toBeNull();
  return Object.fromEntries(
    [...match[1].matchAll(/(--dg-[a-z0-9-]+)\s*:\s*([^;]+);/g)].map(
      ([, name, value]) => [name, value.trim()],
    ),
  );
}

function remToPx(value) {
  const match = value.match(/^([\d.]+)rem$/);
  expect(match, `${value} must be declared in rem`).not.toBeNull();
  return Number(match[1]) * 16;
}

function parseOklch(value) {
  const match = value.match(
    /oklch\(\s*([\d.]+)%?\s+([\d.]+)%?\s+(-?[\d.]+)(?:deg)?(?:\s|\/|\))/i,
  );
  expect(match, `${value} must be an OKLCH color`).not.toBeNull();
  return {
    lightness: Number(match[1]),
    chroma: Number(match[2]),
    hue: ((Number(match[3]) % 360) + 360) % 360,
  };
}

function sourceFiles() {
  const files = [resolve(frontendRoot, "index.html")];
  const stack = [srcDir];
  while (stack.length > 0) {
    const dir = stack.pop();
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const fullPath = resolve(dir, entry.name);
      if (entry.isDirectory()) {
        stack.push(fullPath);
      } else if (
        entry.isFile() &&
        /\.(css|tsx?|jsx?|html)$/.test(fullPath) &&
        !/\.test\.[tj]sx?$/.test(fullPath) &&
        fullPath !== tokensPath
      ) {
        files.push(fullPath);
      }
    }
  }
  return files;
}

function cssFiles() {
  return sourceFiles().filter((filePath) => filePath.endsWith(".css"));
}

function readChromeCss() {
  return CHROME_FILES.map((relativePath) => ({
    path: relativePath,
    css: readFileSync(resolve(srcDir, relativePath), "utf8"),
  }));
}

describe("DG-115 visual foundation", () => {
  it("carries a display type scale above the 18px ceiling, with weight and line-height tokens", () => {
    const root = parseScope(readTokensCss(), ":root");

    for (const token of [...TYPE_SCALE, ...WEIGHT_TOKENS, ...LEADING_TOKENS]) {
      expect(root, `missing type token ${token}`).toHaveProperty(token);
    }

    const sizes = TYPE_SCALE.map((token) => remToPx(root[token]));
    for (let index = 1; index < sizes.length; index += 1) {
      expect(
        sizes[index],
        `${TYPE_SCALE[index]} must be larger than ${TYPE_SCALE[index - 1]}`,
      ).toBeGreaterThan(sizes[index - 1]);
    }

    // The spec's body floor: 15px reads, 13px is annotation only.
    expect(
      remToPx(root["--dg-text-base"]),
      "body floor is 15px",
    ).toBeGreaterThanOrEqual(15);
    // Four display steps above 18px is what the morning read needs: hero
    // verdict, page title, key number, masthead.
    expect(sizes.filter((size) => size > 18).length).toBeGreaterThanOrEqual(4);

    const weights = WEIGHT_TOKENS.map((token) => Number(root[token]));
    expect(weights).toEqual([...weights].sort((a, b) => a - b));
    expect(new Set(weights).size, "weights must be distinct").toBe(weights.length);

    const leadings = LEADING_TOKENS.map((token) => Number(root[token]));
    expect(leadings).toEqual([...leadings].sort((a, b) => a - b));
    expect(leadings.at(-1), "body leading is 1.5").toBeGreaterThanOrEqual(1.5);
  });

  it("carries section-rhythm spacing steps 5-6 and three radius tokens", () => {
    const root = parseScope(readTokensCss(), ":root");

    for (const token of [...SPACING_SCALE, ...RADIUS_TOKENS]) {
      expect(root, `missing token ${token}`).toHaveProperty(token);
    }

    const steps = SPACING_SCALE.map((token) => remToPx(root[token]));
    for (let index = 1; index < steps.length; index += 1) {
      expect(
        steps[index],
        `${SPACING_SCALE[index]} must be larger than ${SPACING_SCALE[index - 1]}`,
      ).toBeGreaterThan(steps[index - 1]);
    }
  });

  it("keeps the chrome family neutral in both scopes so nothing reads as a data lane", () => {
    const cssText = readTokensCss();
    const root = parseScope(cssText, ":root");
    const dark = parseScope(cssText, '[data-theme="dark"]');

    for (const token of CHROME_TOKENS) {
      expect(root, `missing root ${token}`).toHaveProperty(token);
      expect(dark, `missing dark-scope ${token}`).toHaveProperty(token);

      for (const [scope, value] of [
        ["root", root[token]],
        ["dark", dark[token]],
      ]) {
        // Chrome is the frame, not a signal: near-achromatic by contract, so
        // it can never drift into the model-blue or market-amber families.
        expect(
          parseOklch(value).chroma,
          `${token} (${scope}) must stay near-achromatic — chrome is never a lane`,
        ).toBeLessThanOrEqual(0.03);
      }
    }
  });

  it("stops the shell borrowing the model and market lanes", () => {
    const offenders = [];

    for (const { path, css } of readChromeCss()) {
      for (const match of stripComments(css).matchAll(
        /var\((--dg-(?:model|market)[a-z-]*)\)/g,
      )) {
        offenders.push(`${path} paints chrome with ${match[1]}`);
      }
    }

    expect(
      offenders,
      "blue means the model computed it and amber means the market said it — the shell means neither",
    ).toEqual([]);
  });

  it("declares direction color and spends it on movement", () => {
    const cssText = readTokensCss();
    const root = parseScope(cssText, ":root");
    const dark = parseScope(cssText, '[data-theme="dark"]');

    for (const token of DIRECTION_TOKENS) {
      expect(root, `missing root ${token}`).toHaveProperty(token);
      expect(dark, `missing dark-scope ${token}`).toHaveProperty(token);
    }

    // David's 2026-08-30 panel, verbatim option label: "Green up / red down".
    for (const scope of [root, dark]) {
      const up = parseOklch(scope["--dg-up"]).hue;
      const down = parseOklch(scope["--dg-down"]).hue;
      expect(up, "--dg-up must sit in the up-hue arc").toBeGreaterThanOrEqual(120);
      expect(up, "--dg-up must sit in the up-hue arc").toBeLessThanOrEqual(160);
      expect(down <= 30 || down >= 350, "--dg-down must sit in the down-hue arc").toBe(
        true,
      );
    }

    // Direction color is spent on a direction, and the direction comes off a
    // data attribute the surface sets from the signed value — never off a
    // hand-typed class that could mean anything.
    const deltaCss = readFileSync(
      resolve(srcDir, "what-changed", "DailyWhatChanged.css"),
      "utf8",
    );
    expect(deltaCss).toMatch(/\[data-direction="up"\][^{]*\{[^}]*var\(--dg-up\)/);
    expect(deltaCss).toMatch(/\[data-direction="down"\][^{]*\{[^}]*var\(--dg-down\)/);
  });

  it("declares the depth system as flat and keeps it that way", () => {
    const cssText = readTokensCss();

    // The dark surface ladder plus borders IS the depth system. Saying so in
    // the tokens file is what stops the next hand reaching for a shadow.
    expect(cssText).toMatch(/Elevation/i);
    expect(cssText).toMatch(/--dg-bg[\s\S]*--dg-surface[\s\S]*--dg-surface-raised/);

    const shadowed = cssFiles()
      .filter((filePath) =>
        /box-shadow\s*:\s*(?!none)/.test(readFileSync(filePath, "utf8")),
      )
      .map((filePath) => relative(srcDir, filePath));

    expect(shadowed, "the ladder and borders carry depth — no shadows").toEqual([]);
  });

  it("leaves no token in the file with nobody consuming it", () => {
    const root = parseScope(readTokensCss(), ":root");
    const consumers = sourceFiles()
      .map((filePath) => readFileSync(filePath, "utf8"))
      .join("\n");

    const orphans = Object.keys(root).filter(
      (token) => !new RegExp(`var\\(${token}[,)]`).test(consumers),
    );

    expect(
      orphans,
      "a token nobody consumes is dead weight: adopt it or delete it",
    ).toEqual([]);
  });
});
