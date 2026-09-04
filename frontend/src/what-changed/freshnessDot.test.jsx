// @vitest-environment jsdom

// DG-156 — the morning freshness dot carried its state in COLOUR ALONE.
//
// The worst of the three states was the one nobody styled: `unknown` had no
// rule at all, so it inherited the filled neutral chrome and a check that could
// not answer looked exactly like a check that answered fine. That is silence
// reading as success, on David's front page, every morning.
//
// David, 2026-09-04: "we need glyphs and symbols, not full sentences." The
// shape now carries the state in the VISUAL channel. The dot stays
// aria-hidden and the sentence beside it remains the single ACCESSIBLE
// channel — naming a decorative mark that restates the adjacent sentence would
// make a screen reader announce the same fact twice.
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(resolve(here, "DailyWhatChanged.css"), "utf8");
const surface = readFileSync(resolve(here, "DailyWhatChanged.tsx"), "utf8");

function ruleFor(selector) {
  const at = css.indexOf(selector);
  if (at === -1) return null;
  const open = css.indexOf("{", at);
  const close = css.indexOf("}", open);
  return css.slice(open + 1, close);
}

const DOT = ".dg-wc__freshness-dot";

describe("DG-156 the freshness dot's shape carries its state", () => {
  it("gives every state its own rule, including the one that had none", () => {
    for (const status of ["ok", "attention", "unknown"]) {
      expect(ruleFor(`${DOT}[data-status="${status}"]`), status).not.toBeNull();
    }
  });

  it("defaults to NO READING, so an unhandled state never reads as fine", () => {
    // The base used to be `background: var(--dg-chrome)` — a filled dot. Any
    // state without a rule therefore looked like a reading. The default is now
    // the hollow mark, so the failure direction is honest.
    const base = ruleFor(`${DOT} {`) ?? ruleFor(DOT);
    expect(base).toMatch(/background:\s*transparent/);
    expect(base).toMatch(/border:/);
  });

  it("separates the three states by SHAPE, not by hue alone", () => {
    const ok = ruleFor(`${DOT}[data-status="ok"]`);
    const attention = ruleFor(`${DOT}[data-status="attention"]`);
    const unknown = ruleFor(`${DOT}[data-status="unknown"]`);
    // filled · half · hollow — three structurally different backgrounds
    expect(ok).toMatch(/background:\s*var\(--dg-up\)/);
    expect(attention).toMatch(/linear-gradient/);
    expect(unknown).toMatch(/background:\s*transparent/);
    // and the shapes differ from each other, not merely the colours
    expect(attention).not.toEqual(ok);
    expect(unknown).not.toEqual(ok);
    expect(unknown).not.toEqual(attention);
  });

  it("keeps the mark decorative and the sentence the accessible channel", () => {
    // Greg's rule 2 (every mark gets an accessible name) was overruled on
    // 2026-09-04: the sentence beside the dot already carries the state, so
    // naming the mark would announce it twice.
    expect(surface).toMatch(/data-freshness-dot[\s\S]{0,200}aria-hidden="true"/);
  });

  it("survives the narrow width where the rail's box disappears", () => {
    // DG-114: a line that only lives on the rail's box is a line David never
    // sees on his phone. A mark he cannot see is worse than the colour dot,
    // because the colour dot at least kept its sentence.
    expect(css).not.toMatch(/\.dg-wc__masthead[^{]*\{[^}]*display:\s*none/);
    expect(css).not.toMatch(/\.dg-wc__freshness[^{]*\{[^}]*display:\s*none/);
  });
});
