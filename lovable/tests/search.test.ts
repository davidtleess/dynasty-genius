import test from "node:test";
import assert from "node:assert/strict";
import { validatePlayerSearch } from "../src/lib/dg/search.ts";
test("both selected players survive a link round trip", () => {
  const query = new URLSearchParams({ player: "11565", compare: "96" });
  assert.deepEqual(validatePlayerSearch(Object.fromEntries(query)), {
    player: "11565",
    compare: "96",
  });
});
test("invalid, incomplete and same-player pairs cannot become a comparison", () => {
  assert.deepEqual(validatePlayerSearch({ compare: "96" }), {});
  assert.deepEqual(validatePlayerSearch({ player: "11565", compare: "11565" }), {
    player: "11565",
  });
  assert.deepEqual(validatePlayerSearch({ player: "../bad", compare: "96" }), {});
});

test("router search keeps plain numeric player IDs and reads older quoted links", async () => {
  const search = await import("../src/lib/dg/search.ts");
  assert.deepEqual(search.parsePlayerSearch("?player=11565&compare=19"), {
    player: "11565",
    compare: "19",
  });
  assert.equal(
    search.stringifyPlayerSearch({ player: "11565", compare: "19" }),
    "?player=11565&compare=19",
  );
  assert.deepEqual(search.parsePlayerSearch("?player=%2211565%22&compare=%2219%22"), {
    player: "11565",
    compare: "19",
  });
});

test("saved reading survives the global URL parser and serializer", async () => {
  const search = await import("../src/lib/dg/search.ts");
  const snapshot = "a".repeat(64);
  const state = { snapshot, player: "11565", compare: "19" };
  assert.deepEqual(search.parsePlayerSearch(search.stringifyPlayerSearch(state)), state);
  assert.deepEqual(search.parsePlayerSearch("?snapshot=invalid&player=19"), {
    player: "19",
    snapshot: "invalid",
  });
});
