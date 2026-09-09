import assert from "node:assert/strict";
import { test } from "node:test";
import {
  closePlayerSearch,
  selectPlayerSearch,
  clearComparisonSearch,
  savedDate,
} from "../src/lib/dg/polish.ts";

test("player navigation preserves pinned history and board filters", () => {
  const previous = { snapshot: "frozen-reading", position: "QB", player: "1", compare: "2" };
  assert.deepEqual(closePlayerSearch(previous), { snapshot: "frozen-reading", position: "QB" });
  assert.deepEqual(selectPlayerSearch(previous, "3"), {
    snapshot: "frozen-reading",
    position: "QB",
    player: "3",
  });
  assert.deepEqual(clearComparisonSearch(previous), {
    snapshot: "frozen-reading",
    position: "QB",
    player: "1",
  });
  assert.equal(previous.compare, "2");
});
test("saved calendar dates never shift to the previous day", () => {
  assert.equal(savedDate("2026-09-06"), "Sep 6, 2026");
  assert.equal(savedDate("invalid"), "Date unavailable");
});
