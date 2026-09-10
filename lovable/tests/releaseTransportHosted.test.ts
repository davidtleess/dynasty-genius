// DG-213 — the hosted transport, exercised in HOSTED mode against a fixture release.
//
// Its sibling `releaseTransport.test.ts` pins local mode. This file pins hosted, because the module
// cache is per process and `node --test` gives each file its own — one delivery mode per file is the
// cheapest way to make both real.
//
// Nothing here touches the network. The base URL is `.invalid`, which RFC 2606 reserves so it can
// never resolve, and the stub refuses any URL it was not given rather than answering plausibly: a
// stub that invented an empty response for an unexpected request would let a test pass while the
// code fetched something nobody meant it to.
import { test } from "node:test";
import assert from "node:assert/strict";

import { pinHosted, stubNetwork, sha256, jsonResponse } from "./helpers/releaseConfig.ts";

const SNAPSHOT = "f".repeat(64);
const BUNDLE = JSON.stringify({ kind: "dg.read-model.bundle", rows: [1, 2, 3] });
const TRACK = JSON.stringify({ schema_version: "track_record.view.v1", rows: [] });

const bundleHash = await sha256(BUNDLE);
const trackHash = await sha256(TRACK);

const MANIFEST = JSON.stringify({
  schema_version: "dg.delivery-assets.v1",
  source_commit: "da096297afdb16d02b8691589358ccbbfd2c0c36",
  snapshot_id: SNAPSHOT,
  asset_count: 3,
  assets: [
    {
      path: "dg-bundle.json",
      bytes: Buffer.byteLength(BUNDLE),
      sha256: bundleHash,
      content_type: "application/json",
    },
    {
      path: "track-record.json",
      bytes: Buffer.byteLength(TRACK),
      sha256: trackHash,
      content_type: "application/json",
    },
    {
      path: "headshots/12527.jpg",
      bytes: 41510,
      sha256: "d".repeat(64),
      content_type: "image/jpeg",
    },
  ],
});

const config = pinHosted({ manifest_sha256: await sha256(MANIFEST) });
const BASE = config.base_url;

const { release, readAsset } = await import("../src/lib/dg/releaseSource.ts");
const { ReleaseError, headshotUrl } = await import("../src/lib/dg/release.ts");

const routes = () =>
  new Map<string, () => Response>([
    [`${BASE}asset-manifest.json`, () => jsonResponse(MANIFEST)],
    [`${BASE}dg-bundle.json`, () => jsonResponse(BUNDLE)],
    [`${BASE}track-record.json`, () => jsonResponse(TRACK)],
  ]);

test("a hosted build reads the release its config names, and reads it once", async () => {
  const net = stubNetwork(routes());
  try {
    const first = await release();
    assert.equal(first.snapshot_id, SNAPSHOT);
    assert.equal(first.assets.size, 3);
    // Concurrent callers share one manifest fetch; a second call must not re-fetch it.
    await release();
    assert.equal(
      net.requested.filter((u) => u.endsWith("asset-manifest.json")).length,
      1,
      `the manifest was fetched more than once: ${net.requested.join(", ")}`,
    );
  } finally {
    net.restore();
  }
});

test("an asset is verified against the manifest before it is parsed", async () => {
  const net = stubNetwork(routes());
  try {
    const bundle = await readAsset("dg-bundle.json");
    assert.deepEqual((bundle as { rows: number[] }).rows, [1, 2, 3]);
    assert.ok(net.requested.includes(`${BASE}dg-bundle.json`));
  } finally {
    net.restore();
  }
});

test("a substituted asset is refused, and its contents never reach a parser", async () => {
  const swapped = JSON.stringify({ kind: "dg.read-model.bundle", rows: [9, 9, 9] });
  assert.equal(
    Buffer.byteLength(swapped),
    Buffer.byteLength(BUNDLE),
    "same length, different bytes",
  );
  const tampered = routes();
  tampered.set(`${BASE}dg-bundle.json`, () => jsonResponse(swapped));
  const net = stubNetwork(tampered);
  try {
    await assert.rejects(
      () => readAsset("dg-bundle.json"),
      (error: unknown) =>
        error instanceof ReleaseError && /is not the file this release names/.test(error.message),
    );
  } finally {
    net.restore();
  }
});

test("a path the manifest does not list is refused WITHOUT a request", async () => {
  const net = stubNetwork(routes());
  try {
    await assert.rejects(() => readAsset("secrets.json"), ReleaseError);
    assert.ok(
      !net.requested.some((u) => u.includes("secrets.json")),
      "an unlisted path was fetched hopefully instead of being refused by name",
    );
  } finally {
    net.restore();
  }
});

test("hosted headshots resolve from the release, and an absent one asks for nothing", async () => {
  const net = stubNetwork(routes());
  try {
    const loaded = await release();
    assert.equal(headshotUrl(loaded, "12527"), `${BASE}headshots/12527.jpg`);
    assert.equal(headshotUrl(loaded, "99999"), null);
  } finally {
    net.restore();
  }
});

test("every request this file makes belongs to the fixture release", async () => {
  // The blanket guard. `.invalid` cannot resolve, so an escape would fail anyway — but it would fail
  // slowly and with a DNS error, and this says the real thing: nothing outside the release was asked
  // for at all.
  const net = stubNetwork(routes());
  try {
    await release();
    await readAsset("track-record.json");
    for (const url of net.requested) {
      assert.ok(url.startsWith(BASE), `a request escaped the fixture release: ${url}`);
    }
    assert.ok(net.requested.length > 0, "the stub recorded nothing, so it proved nothing");
  } finally {
    net.restore();
  }
});
