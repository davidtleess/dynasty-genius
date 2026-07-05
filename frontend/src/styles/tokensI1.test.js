import { readdirSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const srcDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const tokensPath = resolve(srcDir, "styles", "tokens.css");

const SEMANTIC_TOKENS = [
  "--dg-bg",
  "--dg-surface",
  "--dg-surface-raised",
  "--dg-border",
  "--dg-text",
  "--dg-text-muted",
  "--dg-focus",
  "--dg-caveat",
];

const GUARDED_COLOR_TOKENS = [
  "--dg-bg",
  "--dg-surface",
  "--dg-surface-raised",
  "--dg-border",
  "--dg-text",
  "--dg-text-muted",
  "--dg-focus",
  "--dg-caveat",
  "--dg-model",
  "--dg-model-emphasis",
  "--dg-model-muted",
  "--dg-market",
  "--dg-market-emphasis",
  "--dg-market-muted",
  "--dg-cliff",
];

function readTokensCss() {
  return readFileSync(tokensPath, "utf8");
}

function parseDeclarationsForSelector(cssText, selector) {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = cssText.match(new RegExp(`${escapedSelector}\\s*\\{([^}]+)\\}`, "m"));
  expect(match, `${selector} block must exist`).not.toBeNull();
  return Object.fromEntries(
    [...match[1].matchAll(/(--dg-[a-z0-9-]+)\s*:\s*([^;]+);/g)].map(
      ([, name, value]) => [name, value.trim()],
    ),
  );
}

function parseAllCustomProperties(cssText) {
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
  if (!match) return null;
  const hue = Number(match[1]);
  return ((hue % 360) + 360) % 360;
}

function isRedHue(hue) {
  return hue <= 30 || hue >= 350;
}

function isGreenHue(hue) {
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

  return files;
}

function varFallbacks(cssText, tokenName) {
  const fallbacks = [];
  let cursor = 0;

  while (cursor < cssText.length) {
    const start = cssText.indexOf("var(", cursor);
    if (start === -1) break;

    let depth = 0;
    let end = start;
    for (; end < cssText.length; end += 1) {
      const char = cssText[end];
      if (char === "(") depth += 1;
      if (char === ")") {
        depth -= 1;
        if (depth === 0) break;
      }
    }

    const body = cssText.slice(start + "var(".length, end);
    const comma = body.indexOf(",");
    if (comma !== -1 && body.slice(0, comma).trim() === tokenName) {
      fallbacks.push(body.slice(comma + 1).trim());
    }

    cursor = end + 1;
  }

  return fallbacks;
}

describe("H2 I1 token foundation", () => {
  it("declares the semantic aliases in root and inert dark scopes", () => {
    const cssText = readTokensCss();
    const rootTokens = parseDeclarationsForSelector(cssText, ":root");
    const darkTokens = parseDeclarationsForSelector(cssText, '[data-theme="dark"]');

    for (const tokenName of SEMANTIC_TOKENS) {
      expect(rootTokens, `missing root ${tokenName}`).toHaveProperty(tokenName);
      expect(darkTokens, `missing inert dark-scope ${tokenName}`).toHaveProperty(
        tokenName,
      );
    }
  });

  it("guards both token scopes against verdict hues while preserving model and market families", () => {
    const cssText = readTokensCss();
    const allTokens = parseAllCustomProperties(cssText);

    expect(cssText).not.toMatch(/\b(red|green)\b/i);

    for (const tokenName of GUARDED_COLOR_TOKENS) {
      expect(allTokens, `missing guarded token ${tokenName}`).toHaveProperty(tokenName);
      const hue = parseOklchHue(allTokens[tokenName]);
      expect(
        hue,
        `${tokenName} must be an OKLCH color with explicit hue`,
      ).not.toBeNull();
      expect(isRedHue(hue), `${tokenName} uses banned red hue ${hue}`).toBe(false);
      expect(isGreenHue(hue), `${tokenName} uses banned green hue ${hue}`).toBe(false);
    }

    for (const tokenName of ["--dg-model", "--dg-model-emphasis", "--dg-model-muted"]) {
      const hue = parseOklchHue(allTokens[tokenName]);
      expect(hue, `${tokenName} must stay model-blue`).toBeGreaterThanOrEqual(220);
      expect(hue, `${tokenName} must stay model-blue`).toBeLessThanOrEqual(285);
    }

    for (const tokenName of [
      "--dg-market",
      "--dg-market-emphasis",
      "--dg-market-muted",
    ]) {
      const hue = parseOklchHue(allTokens[tokenName]);
      expect(hue, `${tokenName} must stay market-amber`).toBeGreaterThanOrEqual(55);
      expect(hue, `${tokenName} must stay market-amber`).toBeLessThanOrEqual(95);
    }
  });

  it("does not silently change pixels by activating aliases over mismatched legacy fallbacks", () => {
    const rootTokens = parseDeclarationsForSelector(readTokensCss(), ":root");
    const mismatches = [];

    for (const filePath of cssFiles()) {
      const text = readFileSync(filePath, "utf8");
      for (const tokenName of SEMANTIC_TOKENS) {
        for (const fallback of varFallbacks(text, tokenName)) {
          if (rootTokens[tokenName] !== fallback) {
            mismatches.push(
              `${relative(srcDir, filePath)} ${tokenName}: fallback ${fallback} != root ${rootTokens[tokenName]}`,
            );
          }
        }
      }
    }

    expect(mismatches, "I1 aliases must be pixel-identical on activation").toEqual([]);
  });

  it("ships no theme toggle or dark-scope activation in I1", () => {
    const filesWithThemeActivation = cssFiles()
      .concat([resolve(srcDir, "main.tsx")])
      .filter((filePath) => filePath !== tokensPath)
      .filter((filePath) => readFileSync(filePath, "utf8").includes("data-theme"));

    expect(filesWithThemeActivation).toEqual([]);
  });
});
