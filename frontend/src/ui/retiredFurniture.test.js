// DG-111 — the stamped honesty furniture is retired from every product surface.
//
// David's ruling, 2026-08-29, verbatim: "I really don't care for the caveats and
// the hard wording governance. I prefer to use prose and layman's language with
// respect to making this a world-class fantasy football dynasty front end." and
// "I don't care to persist the governance of language and caveats and lack of
// overall recommendation from the back end into the front end."
//
// That ruling IS the sign-off that releases the exact-string lock on
// DISCLOSURE_LINE (was lib/copy.ts:73) and on the two byte-locked mitigation
// paragraphs. The replacement copy is recorded verbatim in the ticket,
// ~/dg-build/tickets/DG-111-retire-the-caveat-furniture-say-it-once-in-prose.md.
//
// This is a SOURCE scan, not a render scan, because the stamps were rendered from
// a dozen different components: the only way to prove "zero stamped disclosure
// lines" across the product is to prove no authored surface still carries the
// string. Comments are stripped first — a comment recording WHY a stamp was
// retired is history, not a rendered stamp. Generated clients (src/lib/api) carry
// backend docstrings and are excluded; tests are excluded so a test may still
// name the retired string in order to forbid it.
//
// The FACTS these stamps stood on do not disappear here — they are reworded into
// prose where they apply and are proven by the render tests that reference this
// file (DailyWhatChanged "DG-111" describe, PlayerDetailPage "DG-111" describe).
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const SRC_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

// Every register David repealed, exactly as it reached his screen.
const RETIRED_STAMPS = [
  "Descriptive only — not decision-grade.",
  "Experimental — not decision-grade.",
  "Experimental — not validated",
  "Decision support only",
  "decision_supported = false",
];

const SKIP_DIRS = new Set(["node_modules", "dist", "generated", "api"]);

function stripComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
}

function authoredSourceFiles(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!SKIP_DIRS.has(entry.name)) out.push(...authoredSourceFiles(full));
      continue;
    }
    if (!statSync(full).isFile()) continue;
    if (/\.(test|spec)\.[jt]sx?$/.test(entry.name)) continue;
    if (![".ts", ".tsx", ".jsx", ".js"].includes(extname(entry.name))) continue;
    out.push(full);
  }
  return out;
}

describe("DG-111 retired furniture", () => {
  it("renders zero stamped disclosure lines anywhere in the authored product", () => {
    const offenders = [];
    for (const file of authoredSourceFiles(SRC_ROOT)) {
      const body = stripComments(readFileSync(file, "utf8"));
      for (const stamp of RETIRED_STAMPS) {
        if (body.includes(stamp)) {
          offenders.push(`${relative(SRC_ROOT, file)} still stamps "${stamp}"`);
        }
      }
    }
    expect(offenders.sort()).toEqual([]);
  });

  it("keeps no DisclosureLine primitive for a surface to reach for", () => {
    const files = authoredSourceFiles(SRC_ROOT).map((f) => relative(SRC_ROOT, f));
    expect(files).not.toContain("ui/DisclosureLine.tsx");
  });
});
