#!/usr/bin/env node
/**
 * Re-commit the CSS debt censuses after adding or removing a stylesheet.
 *
 * `rawCssAudit.test.js` and `visualCraftAudit.test.js` compare a committed baseline to a
 * freshly computed report, so adding any .css file fails them until the baseline records
 * it. That is the point: the baselines are debt ledgers, and a new file has to be entered
 * deliberately rather than silently absorbed.
 *
 * This script only INSERTS a file entry and recomputes totals by summing the file rows —
 * it never edits another file's counts, so it cannot quietly launder existing debt.
 *
 * Usage: node scripts/update-css-census.mjs <css-path-relative-to-src> [k=v ...]
 *   node scripts/update-css-census.mjs model-scoreboard/ModelScoreboard.css \
 *     raw_font_size_values=3 raw_radius_values=2 raw_spacing_values=6
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const [target, ...pairs] = process.argv.slice(2);
if (!target) {
  console.error("usage: update-css-census.mjs <path> [key=value ...]");
  process.exit(2);
}

const overrides = Object.fromEntries(
  pairs.map((pair) => {
    const [key, value] = pair.split("=");
    return [key, Number(value)];
  }),
);

for (const baseline of ["rawCssAuditBaseline.json", "visualCraftAuditBaseline.json"]) {
  const path = resolve(here, "..", "src", "styles", baseline);
  const data = JSON.parse(readFileSync(path, "utf8"));
  if (data.files.some((file) => file.path === target)) {
    console.log(`${baseline}: already recorded, untouched`);
    continue;
  }
  // Shape the new row from an existing row's keys so the census schema stays uniform;
  // every metric defaults to 0 and only the explicitly passed ones carry debt.
  const shape = Object.keys(data.files[0]);
  const row = {};
  for (const key of shape) {
    row[key] = key === "path" ? target : (overrides[key] ?? 0);
  }
  data.files.push(row);
  data.files.sort((a, b) => a.path.localeCompare(b.path));
  if (data.totals) {
    for (const key of Object.keys(data.totals)) {
      data.totals[key] = data.files.reduce((sum, file) => sum + (file[key] || 0), 0);
    }
  }
  writeFileSync(path, `${JSON.stringify(data, null, 2)}\n`);
  console.log(`${baseline}: recorded ${target}`);
}
