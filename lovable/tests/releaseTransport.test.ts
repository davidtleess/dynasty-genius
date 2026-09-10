// DG-213 — the fetch path itself.
//
// Everything else about hosted delivery is pure and cheap to test. This file exists because the byte
// and hash checks are worth nothing if they were only ever proved on paper: the questions here are
// whether a wrong object is actually refused, and whether it is refused BEFORE it is parsed.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";

import { pinLocal } from "./helpers/releaseConfig.ts";

// THIS FILE IS THE LOCAL-MODE FILE, and it says so before it loads anything.
//
// It previously relied on `release.config.ts` happening to hold `null`. That is production
// configuration, not a fixture: the moment root fills in a hosted destination, the "local mode
// refuses" test below stopped asserting a refusal and instead made a REAL NETWORK REQUEST to the
// published base URL, then failed with a TypeError that says nothing about its subject. Demonstrated
// before this fix, in the run directory beside this ticket.
//
// The SUT is imported dynamically, AFTER the pin. A static import is hoisted above it and would
// resolve the real config first, filling the module cache before the hook could ever be consulted.
pinLocal();
const { readVerified, release, readAsset } = await import("../src/lib/dg/releaseSource.ts");
const { ReleaseError } = await import("../src/lib/dg/release.ts");

const body = JSON.stringify({ schema_version: "dg.delivery-assets.v1", rows: [1, 2, 3] });
const bytes = Buffer.byteLength(body);
const hash = createHash("sha256").update(body).digest("hex");

/** Serve one fixed response for the next fetch, whatever the url. */
function serve(text: string, init: { status?: number } = {}) {
  const original = globalThis.fetch;
  globalThis.fetch = (async () =>
    new Response(text, { status: init.status ?? 200 })) as typeof fetch;
  return () => {
    globalThis.fetch = original;
  };
}

test("an object matching both its declared numbers is read", async () => {
  const restore = serve(body);
  try {
    const value = await readVerified("https://x/y.json", hash, "the test object", bytes);
    assert.deepEqual((value as { rows: number[] }).rows, [1, 2, 3]);
  } finally {
    restore();
  }
});

test("a byte length that disagrees with the manifest is refused", async () => {
  const restore = serve(body);
  try {
    await assert.rejects(
      () => readVerified("https://x/y.json", hash, "the test object", bytes + 1),
      (error: unknown) =>
        error instanceof ReleaseError && /bytes where this release declares/.test(error.message),
    );
  } finally {
    restore();
  }
});

test("a hash that disagrees with the manifest is refused even when the length matches", async () => {
  // The length check cannot catch this one: same size, different content. This is the substitution
  // the hash exists for, and the reason the byte check is not a second integrity proof.
  const swapped = body.replace("[1,2,3]", "[9,9,9]");
  assert.equal(Buffer.byteLength(swapped), bytes);
  const restore = serve(swapped);
  try {
    await assert.rejects(
      () => readVerified("https://x/y.json", hash, "the test object", bytes),
      (error: unknown) =>
        error instanceof ReleaseError && /is not the file this release names/.test(error.message),
    );
  } finally {
    restore();
  }
});

test("a response that is not ok is refused by status, never parsed as data", async () => {
  const restore = serve("<html>404</html>", { status: 404 });
  try {
    await assert.rejects(
      () => readVerified("https://x/y.json", hash, "the test object", bytes),
      (error: unknown) => error instanceof ReleaseError && /404/.test(error.message),
    );
  } finally {
    restore();
  }
});

test("a failing object is refused BEFORE it is parsed", async () => {
  // An error page served with 200 is the case that matters: if the hash were checked after parsing,
  // this would surface as a JSON syntax error, which reads as a bug in the app rather than as a
  // release that does not match what it claims to be.
  const restore = serve("this is not json at all");
  try {
    await assert.rejects(
      () => readVerified("https://x/y.json", hash, "the test object"),
      (error: unknown) => error instanceof ReleaseError && !(error instanceof SyntaxError),
    );
  } finally {
    restore();
  }
});

// --- the two modes do not reach each other ---------------------------------------------------------

test("in local mode the hosted transport refuses rather than inventing a base url", async () => {
  // Local mode is PINNED for this file, so this asserts the behaviour rather than the committed
  // config. If these ever resolved, a local build would be quietly fetching from somewhere, which is
  // the failure this whole module is shaped to prevent.
  await assert.rejects(() => release(), ReleaseError);
  await assert.rejects(() => readAsset("dg-bundle.json"), ReleaseError);
});

test("no local-mode test can reach the network, whatever the committed config says", async () => {
  // The guard for the defect itself rather than for its symptom. Any fetch at all from a local-mode
  // build is the bug; asserting the refusal type alone would still pass if a request went out first.
  const previous = globalThis.fetch;
  const reached: string[] = [];
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    reached.push(String(input));
    throw new Error("a local-mode test attempted a real request");
  }) as typeof fetch;
  try {
    await assert.rejects(() => release(), ReleaseError);
    await assert.rejects(() => readAsset("track-record.json"), ReleaseError);
  } finally {
    globalThis.fetch = previous;
  }
  assert.deepEqual(reached, [], `local mode requested ${reached.join(", ")}`);
});
