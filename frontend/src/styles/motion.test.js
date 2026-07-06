import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const stylesDir = dirname(fileURLToPath(import.meta.url));
const srcDir = resolve(stylesDir, "..");
const frontendRoot = resolve(srcDir, "..");
const motionPath = resolve(stylesDir, "motion.css");
const packagePath = resolve(frontendRoot, "package.json");

const REQUIRED_TOKENS = [
  "--dg-duration-fast-01: 70ms",
  "--dg-duration-fast-02: 110ms",
  "--dg-duration-moderate-01: 150ms",
  "--dg-duration-moderate-02: 240ms",
  "--dg-duration-slow-01: 400ms",
  "--dg-duration-slow-02: 700ms",
  "--dg-duration-chart-stage: 1000ms",
  "--dg-ease-productive-standard: cubic-bezier(0.2, 0, 0.38, 0.9)",
  "--dg-ease-productive-entrance: cubic-bezier(0, 0, 0.38, 0.9)",
  "--dg-ease-productive-exit: cubic-bezier(0.2, 0, 1, 0.9)",
];

const FORBIDDEN_MOTION_DEPENDENCIES = [
  "framer-motion",
  "motion",
  "@motionone/react",
  "@motionone/dom",
  "gsap",
  "react-spring",
  "@react-spring/web",
  "animejs",
];

function readMotionCss() {
  expect(
    existsSync(motionPath),
    "Task 4 requires frontend/src/styles/motion.css before motion classes ship",
  ).toBe(true);
  return readFileSync(motionPath, "utf8");
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

function stripComments(text) {
  return text.replace(/\/\*[\s\S]*?\*\//g, "");
}

function classBlocks(cssText) {
  return [...cssText.matchAll(/(\.dg-motion-[a-z0-9_-]+)\s*\{([^}]+)\}/gi)].map(
    ([, selector, body]) => ({ selector, body }),
  );
}

function reducedMotionBlock(cssText) {
  const match = cssText.match(
    /@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)\s*\{([\s\S]+)\}\s*$/i,
  );
  return match?.[1] ?? "";
}

describe("H2 Task 4 motion system", () => {
  it("defines the Carbon-derived plain-CSS motion tokens", () => {
    const motionCss = readMotionCss();

    for (const token of REQUIRED_TOKENS) {
      expect(motionCss).toContain(token);
    }
  });

  it("keeps motion as plain CSS with no runtime dependency", () => {
    const packageJson = JSON.parse(readFileSync(packagePath, "utf8"));
    const dependencyNames = new Set([
      ...Object.keys(packageJson.dependencies ?? {}),
      ...Object.keys(packageJson.devDependencies ?? {}),
    ]);

    for (const dependency of FORBIDDEN_MOTION_DEPENDENCIES) {
      expect(dependencyNames.has(dependency)).toBe(false);
    }
  });

  it("requires every dg-motion class to use tokenized durations and easings", () => {
    const css = readMotionCss();
    const blocks = classBlocks(css);

    expect(blocks.length).toBeGreaterThan(0);
    for (const { selector, body } of blocks) {
      if (/transition|animation/.test(body)) {
        expect(
          /var\(--dg-duration-(?:fast|moderate|slow|chart-stage)/.test(body),
          `${selector} must use a --dg-duration-* token`,
        ).toBe(true);
        expect(
          /var\(--dg-ease-productive-/.test(body),
          `${selector} must use a --dg-ease-productive-* token`,
        ).toBe(true);
      }
    }
  });

  it("provides reduced-motion overrides for all motion classes", () => {
    const css = readMotionCss();
    const reduced = reducedMotionBlock(css);

    expect(css).toMatch(/@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)/i);
    expect(reduced).toMatch(/animation:\s*none|transition:\s*none/i);
    for (const { selector } of classBlocks(css)) {
      expect(
        reduced.includes(selector),
        `${selector} needs an explicit reduced-motion override`,
      ).toBe(true);
    }
  });

  it("forbids decorative or decision-implying motion patterns", () => {
    const forbiddenHits = [];
    for (const path of cssFiles()) {
      const css = stripComments(readFileSync(path, "utf8"));
      const forbiddenMotionPatterns = [
        /\.dg-motion-[^{]*(?:pulse|shimmer|urgent|bounce|stretch|recommend|opportunity)/i,
        /animation(?:-name)?:\s*[^;]*(?:pulse|shimmer|urgent|bounce|stretch|recommend|opportunity)/i,
        /transition(?:-property)?:\s*[^;]*(?:confidence|recommend|opportunity)/i,
        /@keyframes\s+(?:pulse|shimmer|urgent|bounce|stretch|recommend|opportunity)/i,
      ];
      for (const pattern of forbiddenMotionPatterns) {
        const match = css.match(pattern);
        if (match) {
          forbiddenHits.push(`${relative(srcDir, path)}:${match[0]}`);
        }
      }
    }

    expect(forbiddenHits).toEqual([]);
  });

  it("keeps chart motion stage-bounded and hard-right-edge aware", () => {
    const css = readMotionCss();

    expect(css).toContain(".dg-motion-chart-stage");
    expect(css).toMatch(
      /\.dg-motion-chart-stage\s*\{[^}]*var\(--dg-duration-chart-stage\)/s,
    );
    expect(css).toContain("data-hard-right-edge");
    expect(css).not.toMatch(/extrapolat|draw-past-right-edge/i);
  });
});
