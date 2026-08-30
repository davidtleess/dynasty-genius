// Runs the fixture-rot lock in the three-second unit suite. See the long note
// at the top of `liveFixtureSchemas.ts` for why this exists at all: a rotted
// fixture does not fail the browser gate on a secondary read, it silently
// changes what a surface says while every assertion stays green.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { LIVE_FIXTURE_SCHEMAS, parseLiveFixture } from "./liveFixtureSchemas";

const FIXTURE_DIR = new URL(".", import.meta.url).pathname;
const FIXTURE_FILES = readdirSync(FIXTURE_DIR)
  .filter((name) => name.endsWith(".live.json"))
  .sort();

describe("live fixtures still satisfy the contracts they were captured against", () => {
  it("finds the captured fixtures at all", () => {
    // A path that stopped resolving would make every assertion below vacuous —
    // an empty loop passes. This is the same false receipt in miniature.
    expect(FIXTURE_FILES.length).toBeGreaterThanOrEqual(12);
  });

  it("pins every captured fixture to a schema", () => {
    const unpinned = FIXTURE_FILES.filter(
      (name) => LIVE_FIXTURE_SCHEMAS[name] === undefined,
    );
    expect(
      unpinned,
      "these fixtures can rot without anything noticing — add them to LIVE_FIXTURE_SCHEMAS:",
    ).toEqual([]);
  });

  it("does not pin a schema to a fixture that no longer exists", () => {
    const present = new Set(FIXTURE_FILES);
    const orphaned = Object.keys(LIVE_FIXTURE_SCHEMAS).filter(
      (name) => !present.has(name),
    );
    expect(orphaned, "these schema entries name files that are gone:").toEqual([]);
  });

  for (const name of FIXTURE_FILES) {
    it(`${name} parses against its endpoint's generated schema`, () => {
      const raw = JSON.parse(readFileSync(join(FIXTURE_DIR, name), "utf8"));
      expect(() => parseLiveFixture(name, raw)).not.toThrow();
    });
  }
});
