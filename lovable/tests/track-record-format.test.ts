import { test } from "node:test";
import assert from "node:assert/strict";
import { readingDay, resultNumber } from "../src/lib/dg/track-record-format.ts";

test("track record retains the declared calendar date in a western timezone", () => {
  const previous = process.env.TZ;
  try {
    process.env.TZ = "America/New_York";
    assert.equal(readingDay("2026-09-06"), "Sep 6, 2026");
  } finally {
    if (previous === undefined) delete process.env.TZ;
    else process.env.TZ = previous;
  }
});
test("correlations, returns, fractional tied ranks and small points retain distinct units", () => {
  assert.equal(resultNumber(0.2, "correlation"), "0.200");
  assert.equal(resultNumber(0.2, "fraction"), "20%");
  assert.equal(resultNumber(-1, "fraction"), "-100%");
  assert.equal(resultNumber(2.5, "places"), "2.5");
  assert.equal(resultNumber(-0.035), "-0.04");
  assert.equal(resultNumber(0), "0.0");
  assert.equal(resultNumber(null), "—");
});
