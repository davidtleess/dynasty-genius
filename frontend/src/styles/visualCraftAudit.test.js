import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const srcDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const baselinePath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "visualCraftAuditBaseline.json",
);

const BLAST_RADIUS_FILES = [
  "command/CommandPalette.css",
  "shell/AppShell.css",
  "shell/TrustStrip.css",
  "system-health/SystemHealthCard.css",
  "what-changed/DailyWhatChanged.css",
];

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

function countMatches(text, pattern) {
  return [...text.matchAll(pattern)].length;
}

function auditFile(path) {
  const css = readFileSync(path, "utf8");
  return {
    path: relative(srcDir, path).replaceAll("\\", "/"),
    focus_visible_selectors: countMatches(css, /:focus-visible\b/g),
    focus_token_consumers: countMatches(css, /var\(--dg-focus(?:\)|,)/g),
    hover_selectors: countMatches(css, /:hover\b/g),
    elevation_consumers: countMatches(css, /box-shadow|var\(--dg-shadow(?:\)|,)/g),
    row_treatment_selectors: countMatches(
      css,
      /[.{][a-z0-9_-]*(?:row|table|list)[a-z0-9_-]*/gi,
    ),
    card_treatment_selectors: countMatches(css, /[.{][a-z0-9_-]*card[a-z0-9_-]*/gi),
  };
}

function currentReport() {
  const files = cssFiles().map(auditFile);
  return {
    schema_version: "h2_visual_craft_audit.v1",
    generated_for: "H2 reset Task 3 visual craft audit",
    blast_radius_files: BLAST_RADIUS_FILES,
    files,
    totals: files.reduce(
      (totals, row) => ({
        focus_visible_selectors:
          totals.focus_visible_selectors + row.focus_visible_selectors,
        focus_token_consumers: totals.focus_token_consumers + row.focus_token_consumers,
        hover_selectors: totals.hover_selectors + row.hover_selectors,
        elevation_consumers: totals.elevation_consumers + row.elevation_consumers,
        row_treatment_selectors:
          totals.row_treatment_selectors + row.row_treatment_selectors,
        card_treatment_selectors:
          totals.card_treatment_selectors + row.card_treatment_selectors,
      }),
      {
        focus_visible_selectors: 0,
        focus_token_consumers: 0,
        hover_selectors: 0,
        elevation_consumers: 0,
        row_treatment_selectors: 0,
        card_treatment_selectors: 0,
      },
    ),
  };
}

function readBaseline() {
  expect(
    existsSync(baselinePath),
    "Task 3 is report-first: commit frontend/src/styles/visualCraftAuditBaseline.json before broad CSS migration",
  ).toBe(true);
  return JSON.parse(readFileSync(baselinePath, "utf8"));
}

describe("H2 Task 3 visual craft audit", () => {
  it("commits a current focus, hover, elevation, and row-treatment census", () => {
    expect(readBaseline()).toEqual(currentReport());
  });

  it("keeps the Task 2 primitive library on the governed focus grammar", () => {
    const report = currentReport();
    const uiCss = report.files.find((row) => row.path === "ui/ui.css");

    expect(uiCss).toBeTruthy();
    expect(uiCss.focus_visible_selectors).toBeGreaterThan(0);
    expect(uiCss.focus_token_consumers).toBeGreaterThan(0);
  });

  it("tracks every visual-flip blast-radius surface in the census", () => {
    const paths = new Set(currentReport().files.map((row) => row.path));

    for (const path of BLAST_RADIUS_FILES) {
      expect(paths.has(path), `missing blast-radius CSS audit row for ${path}`).toBe(
        true,
      );
    }
  });
});
