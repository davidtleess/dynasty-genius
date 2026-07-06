import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const srcDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const baselinePath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "rawCssAuditBaseline.json",
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

function stripVarCalls(cssText) {
  return cssText.replace(/var\(--dg-[a-z0-9-]+(?:,[^)]+)?\)/g, "");
}

function countMatches(text, pattern) {
  return [...text.matchAll(pattern)].length;
}

function auditFile(path) {
  const css = readFileSync(path, "utf8");
  const withoutVars = stripVarCalls(css);
  return {
    path: relative(srcDir, path).replaceAll("\\", "/"),
    raw_hex: countMatches(withoutVars, /#[0-9a-f]{3,8}\b/gi),
    raw_oklch: countMatches(withoutVars, /\boklch\(/gi),
    raw_rgb: countMatches(withoutVars, /\brgba?\(/gi),
    raw_spacing_values: countMatches(
      withoutVars,
      /(?:margin|padding|gap|top|right|bottom|left|width|height|min-width|min-height|max-width|max-height):\s*(?!0\b)(?:\d+(?:\.\d+)?(?:px|rem|em|ch|vh|vw|%))/gi,
    ),
    raw_radius_values: countMatches(
      withoutVars,
      /border-radius:\s*(?!0\b)(?:\d+(?:\.\d+)?(?:px|rem|em|%))/gi,
    ),
    raw_font_size_values: countMatches(
      withoutVars,
      /font-size:\s*(?:\d+(?:\.\d+)?(?:px|rem|em|%))/gi,
    ),
    non_token_font_families: countMatches(
      css,
      /font-family:(?!\s*var\(\s*--dg-font-)/gi,
    ),
  };
}

function currentReport() {
  const files = cssFiles().map(auditFile);
  return {
    schema_version: "h2_raw_css_audit.v1",
    generated_for: "H2 reset Task 3 CSS token debt audit",
    files,
    totals: files.reduce(
      (totals, row) => ({
        raw_hex: totals.raw_hex + row.raw_hex,
        raw_oklch: totals.raw_oklch + row.raw_oklch,
        raw_rgb: totals.raw_rgb + row.raw_rgb,
        raw_spacing_values: totals.raw_spacing_values + row.raw_spacing_values,
        raw_radius_values: totals.raw_radius_values + row.raw_radius_values,
        raw_font_size_values: totals.raw_font_size_values + row.raw_font_size_values,
        non_token_font_families:
          totals.non_token_font_families + row.non_token_font_families,
      }),
      {
        raw_hex: 0,
        raw_oklch: 0,
        raw_rgb: 0,
        raw_spacing_values: 0,
        raw_radius_values: 0,
        raw_font_size_values: 0,
        non_token_font_families: 0,
      },
    ),
  };
}

function readBaseline() {
  expect(
    existsSync(baselinePath),
    "Task 3 is report-first: commit frontend/src/styles/rawCssAuditBaseline.json before broad CSS migration",
  ).toBe(true);
  return JSON.parse(readFileSync(baselinePath, "utf8"));
}

describe("H2 Task 3 raw CSS debt audit", () => {
  it("commits a current raw-value census before broad CSS migration", () => {
    expect(readBaseline()).toEqual(currentReport());
  });

  it("keeps new primitive CSS token-only for colors and font families", () => {
    const report = currentReport();
    const uiRows = report.files.filter((row) => row.path.startsWith("ui/"));

    expect(uiRows.length).toBeGreaterThan(0);
    for (const row of uiRows) {
      expect(row.raw_hex).toBe(0);
      expect(row.raw_oklch).toBe(0);
      expect(row.raw_rgb).toBe(0);
      expect(row.non_token_font_families).toBe(0);
    }
  });

  it("requires the Task-5 flip blast radius to reach zero raw color values", () => {
    const rows = new Map(currentReport().files.map((row) => [row.path, row]));

    for (const path of BLAST_RADIUS_FILES) {
      const row = rows.get(path);
      expect(row, `missing blast-radius CSS audit row for ${path}`).toBeTruthy();
      expect(
        {
          path,
          raw_hex: row.raw_hex,
          raw_oklch: row.raw_oklch,
          raw_rgb: row.raw_rgb,
        },
        `${path} must migrate raw colors to semantic tokens before the Task-5 visual flip`,
      ).toEqual({ path, raw_hex: 0, raw_oklch: 0, raw_rgb: 0 });
    }
  });
});
