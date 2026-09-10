// DG-213 — the track record client in HOSTED mode.
//
// `track-record.test.ts` pins local, where every mock answers the private bridge at
// `/api/private/...`. Under a hosted config the client reads a published document instead, so those
// mocks describe a request the code no longer makes — the query would go to the release manifest over
// the real network and fail on transport, while the assertions appeared to be about parsing. Hence a
// separate file: one delivery mode per process.
//
// What this covers that local cannot: the published document is hash-verified, the reading must
// belong to THIS release, a pinned reading the release does not carry is refused rather than
// silently replaced with the newest, and saving is closed with the exporter's own wording.
import { test } from "node:test";
import assert from "node:assert/strict";

import { views } from "./fixtures/track-record-views.ts";
import { pinHosted, stubNetwork, sha256, jsonResponse } from "./helpers/releaseConfig.ts";

/** The published reading, whose snapshot id is the one the release declares. */
const SNAPSHOT = "e".repeat(64);
const VIEW = JSON.stringify(views.enrolledPending);
const viewHash = await sha256(VIEW);

const MANIFEST = JSON.stringify({
  schema_version: "dg.delivery-assets.v1",
  source_commit: "da096297afdb16d02b8691589358ccbbfd2c0c36",
  snapshot_id: SNAPSHOT,
  asset_count: 2,
  assets: [
    { path: "dg-bundle.json", bytes: 12, sha256: "b".repeat(64), content_type: "application/json" },
    {
      path: "track-record.json",
      bytes: Buffer.byteLength(VIEW),
      sha256: viewHash,
      content_type: "application/json",
    },
  ],
});

const config = pinHosted({ manifest_sha256: await sha256(MANIFEST) });
const BASE = config.base_url;

const { trackRecordQuery, saveBoardReading, TrackRecordError } =
  await import("../src/lib/dg/track-record.ts");

const routes = () =>
  new Map<string, () => Response>([
    [`${BASE}asset-manifest.json`, () => jsonResponse(MANIFEST)],
    [`${BASE}track-record.json`, () => jsonResponse(VIEW)],
  ]);

test("the published reading is read from the release, not from the private bridge", async () => {
  const net = stubNetwork(routes());
  try {
    const view = await trackRecordQuery(null).queryFn!({} as never);
    assert.equal((view as { selected: { snapshot_id: string } }).selected.snapshot_id, SNAPSHOT);
    assert.ok(
      !net.requested.some((u) => u.includes("/api/private/")),
      `a hosted build called the local bridge: ${net.requested.join(", ")}`,
    );
    assert.ok(net.requested.every((u) => u.startsWith(BASE)));
  } finally {
    net.restore();
  }
});

test("saving is closed after the reading validates, in the exporter's own words", async () => {
  const net = stubNetwork(routes());
  try {
    const view = (await trackRecordQuery(null).queryFn!({} as never)) as {
      save_capability: { enabled: boolean; reason: string | null; expected: unknown };
    };
    assert.equal(view.save_capability.enabled, false);
    assert.equal(view.save_capability.expected, null);
    assert.equal(
      view.save_capability.reason,
      "Saving new readings is available in the Mac preview.",
    );
    // The fixture says saving is ENABLED, so this proves the hosted path overrode it rather than
    // happening to agree with it.
    assert.equal(views.enrolledPending.save_capability.enabled, true);
  } finally {
    net.restore();
  }
});

test("a pinned reading this release does not carry is REFUSED, in plain words", async () => {
  const net = stubNetwork(routes());
  try {
    await assert.rejects(
      () => trackRecordQuery("0".repeat(64)).queryFn!({} as never),
      (error: unknown) => {
        assert.ok(error instanceof TrackRecordError, `route rendering only knows TrackRecordError`);
        const message = (error as Error).message;
        assert.match(message, /not part of this published set/);
        // No hashes, byte counts or asset paths on a screen the manager reads.
        assert.doesNotMatch(message, /[0-9a-f]{12}|sha256|bytes|\.json/);
        return true;
      },
    );
  } finally {
    net.restore();
  }
});

test("a transport refusal reads as a refusal, never as a generic failure", async () => {
  const broken = routes();
  broken.set(`${BASE}track-record.json`, () => jsonResponse('{"schema_version":"tampered"}'));
  const net = stubNetwork(broken);
  try {
    await assert.rejects(
      () => trackRecordQuery(null).queryFn!({} as never),
      (error: unknown) => {
        assert.ok(error instanceof TrackRecordError);
        assert.match((error as Error).message, /could not be confirmed/);
        return true;
      },
    );
  } finally {
    net.restore();
  }
});

test("saving refuses in hosted mode instead of posting to a bridge that is not there", async () => {
  const net = stubNetwork(routes());
  try {
    await assert.rejects(
      () =>
        saveBoardReading({
          report_run: "20260906T214512Z",
          report_sha256: "a".repeat(64),
          market_sha256: "b".repeat(64),
          league_sha256: "c".repeat(64),
          catalog_run: "20260907T013635Z",
          catalog_content_sha256: "d".repeat(64),
        }),
      (error: unknown) =>
        error instanceof TrackRecordError &&
        /available in the Mac preview/.test((error as Error).message),
    );
    // A POST would surface as a transport error, and "the network failed" is a different and worse
    // claim than "this reading is published and fixed".
    assert.deepEqual(net.requested, []);
  } finally {
    net.restore();
  }
});
