// DG-213 — hosted release delivery. Written before the module.
//
// The whole risk here is a silent substitution: the hosted app quietly showing something other than
// the reviewed export, or the local app quietly reaching for the hosted one. Every test below is a
// refusal that must happen rather than a feature that must work.
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  readReleaseManifest,
  resolveAsset,
  headshotUrl,
  hostedSaveCapability,
  selectHostedReading,
  ReleaseError,
  type ReleaseConfig,
} from "../src/lib/dg/release.ts";

const BASE = "https://assets.example/dg/20260910T001048Z/";
const config: ReleaseConfig = { base_url: BASE, manifest_sha256: "a".repeat(64) };

const manifest = () => ({
  schema_version: "dg.delivery-assets.v1",
  source_commit: "da096297afdb16d02b8691589358ccbbfd2c0c36",
  snapshot_id: "f".repeat(64),
  asset_count: 4,
  assets: [
    {
      path: "dg-bundle.json",
      bytes: 3513172,
      sha256: "b".repeat(64),
      content_type: "application/json",
    },
    {
      path: "track-record.json",
      bytes: 609596,
      sha256: "c".repeat(64),
      content_type: "application/json",
    },
    {
      path: "headshots/12527.jpg",
      bytes: 41510,
      sha256: "d".repeat(64),
      content_type: "image/png",
    },
    {
      path: "headshots/8122.jpg",
      bytes: 33110,
      sha256: "e".repeat(64),
      content_type: "image/webp",
    },
  ],
});

// --- the manifest is read strictly ------------------------------------------------------------------

test("a well formed manifest reads", () => {
  const release = readReleaseManifest(manifest(), config);
  assert.equal(release.snapshot_id, "f".repeat(64));
  assert.equal(release.assets.size, 4);
});

test("an unexpected schema is refused rather than guessed at", () => {
  const bad = { ...manifest(), schema_version: "dg.delivery-assets.v2" };
  assert.throws(() => readReleaseManifest(bad, config), ReleaseError);
});

test("a manifest whose asset count disagrees with its own list is refused", () => {
  const bad = { ...manifest(), asset_count: 900 };
  assert.throws(() => readReleaseManifest(bad, config), ReleaseError);
});

test("an asset without a full hash is refused, because the hash is the only check we get", () => {
  const bad = manifest();
  bad.assets[0].sha256 = "short";
  assert.throws(() => readReleaseManifest(bad, config), ReleaseError);
});

// --- resolution never invents a URL -------------------------------------------------------------------

test("a listed asset resolves to the release base and carries its expected hash", () => {
  const release = readReleaseManifest(manifest(), config);
  const asset = resolveAsset(release, "dg-bundle.json");
  assert.equal(asset.url, `${BASE}dg-bundle.json`);
  assert.equal(asset.sha256, "b".repeat(64));
});

test("an asset the manifest does not list is refused BY NAME, never fetched hopefully", () => {
  const release = readReleaseManifest(manifest(), config);
  assert.throws(() => resolveAsset(release, "dg-bundle-v2.json"), /dg-bundle-v2\.json/);
});

test("a headshot absent from the release returns no url, so the initials fallback fires without a 404", () => {
  const release = readReleaseManifest(manifest(), config);
  assert.equal(headshotUrl(release, "12527"), `${BASE}headshots/12527.jpg`);
  assert.equal(headshotUrl(release, "99999"), null);
});

test("in local mode a headshot keeps the path the app already uses", () => {
  assert.equal(headshotUrl(null, "12527"), "/assets/headshots/12527.jpg");
  assert.equal(headshotUrl(null, "99999"), "/assets/headshots/99999.jpg");
});

// --- the two modes never cross ------------------------------------------------------------------------

test("hosted saving is disabled with a reason and expects nothing", () => {
  const capability = hostedSaveCapability();
  assert.equal(capability.enabled, false);
  assert.equal(capability.expected, null);
  // A real sentence saying where saving lives, not a failure notice: nothing has gone wrong here.
  // The exact wording is the exporter's, so the hosted app and the export say the same thing.
  assert.equal(capability.reason, "Saving new readings is available in the Mac preview.");
  assert.doesNotMatch(capability.reason, /\berror\b|\bfailed\b|could not|unavailable/i);
});

// --- a pinned reading is honoured or refused, never quietly swapped -------------------------------------

test("the pinned reading is returned when the release carries it", () => {
  const release = readReleaseManifest(manifest(), config);
  const view = {
    status: "available",
    selected: { snapshot_id: "f".repeat(64) },
    snapshots: [{ snapshot_id: "f".repeat(64) }],
  };
  assert.equal(
    selectHostedReading(view, release, "f".repeat(64)).selected.snapshot_id,
    "f".repeat(64),
  );
});

test("no pinned reading returns what the release selected, deterministically", () => {
  const release = readReleaseManifest(manifest(), config);
  const view = {
    status: "available",
    selected: { snapshot_id: "f".repeat(64) },
    snapshots: [{ snapshot_id: "f".repeat(64) }],
  };
  assert.equal(selectHostedReading(view, release, null).selected.snapshot_id, "f".repeat(64));
});

test("a pinned reading the release does not carry is REFUSED, not replaced with the newest", () => {
  // Silently serving a different capture than the one the link names is the worst failure this
  // screen can have: the reader believes he is looking at the reading he pinned.
  const release = readReleaseManifest(manifest(), config);
  const view = {
    status: "available",
    selected: { snapshot_id: "f".repeat(64) },
    snapshots: [{ snapshot_id: "f".repeat(64) }],
  };
  assert.throws(() => selectHostedReading(view, release, "0".repeat(64)), ReleaseError);
});

test("the hosted view must belong to the release it was fetched from", () => {
  const release = readReleaseManifest(manifest(), config);
  const foreign = {
    status: "available",
    selected: { snapshot_id: "9".repeat(64) },
    snapshots: [{ snapshot_id: "9".repeat(64) }],
  };
  assert.throws(() => selectHostedReading(foreign, release, null), ReleaseError);
});

// --- the manifest is a list of expected files, not an arbitrary directory --------------------------
//
// Everything below is the same defect wearing different clothes: a manifest that passes every hash
// check while naming something the app was never meant to fetch. The hashes prove an object is the
// one the manifest describes. They prove nothing about whether the manifest should describe it.

test("a duplicate asset path is refused, not silently last-one-wins", () => {
  // A Map would keep the last entry and the count would still agree, so the substituted hash would
  // travel with a legitimate-looking manifest.
  const bad = manifest();
  bad.assets.push({
    path: "dg-bundle.json",
    bytes: 12,
    sha256: "9".repeat(64),
    content_type: "application/json",
  });
  bad.asset_count = 5;
  assert.throws(() => readReleaseManifest(bad, config), /dg-bundle\.json/);
});

test("a zero or negative byte length is refused", () => {
  for (const bytes of [0, -1]) {
    const bad = manifest();
    bad.assets[0].bytes = bytes;
    assert.throws(() => readReleaseManifest(bad, config), ReleaseError, `bytes ${bytes}`);
  }
});

test("an asset path carrying a query or a fragment is refused", () => {
  for (const path of ["dg-bundle.json?v=2", "dg-bundle.json#frag"]) {
    const bad = manifest();
    bad.assets[0].path = path;
    assert.throws(() => readReleaseManifest(bad, config), ReleaseError, path);
  }
});

test("an asset path that is really a URL, or escapes the base, is refused", () => {
  for (const path of [
    "https://evil.example/dg-bundle.json", // absolute
    "//evil.example/dg-bundle.json", // protocol relative
    "/dg-bundle.json", // host root
    "../dg-bundle.json", // traversal
    "headshots/../../dg-bundle.json", // traversal, mid path
    "%2e%2e/dg-bundle.json", // encoded traversal
    "headshots\\12527.jpg", // backslash
  ]) {
    const bad = manifest();
    bad.assets[0].path = path;
    assert.throws(() => readReleaseManifest(bad, config), ReleaseError, path);
  }
});

test("a release base that is not https is refused", () => {
  for (const base_url of [
    "http://assets.example/dg/",
    "file:///Users/davidleess/dg/",
    "javascript:x/",
  ]) {
    assert.throws(
      () => readReleaseManifest(manifest(), { ...config, base_url }),
      ReleaseError,
      base_url,
    );
  }
});

test("only the three known dataset shapes are allowed to appear at all", () => {
  // The app fetches exactly three kinds of object. Anything else in the manifest is either a mistake
  // or an attempt to get the app to fetch something; both are refusals, and neither is a warning.
  for (const path of [
    "README.md",
    "dg-bundle.json.bak",
    "headshots/index.json",
    "headshots/abc.jpg",
    "headshots/12527.jpeg",
    "assets/dg-bundle.json",
  ]) {
    const bad = manifest();
    bad.assets[0].path = path;
    assert.throws(() => readReleaseManifest(bad, config), ReleaseError, path);
  }
});

test("a release missing either dataset is refused before anything renders", () => {
  for (const drop of ["dg-bundle.json", "track-record.json"]) {
    const bad = manifest();
    bad.assets = bad.assets.filter((a) => a.path !== drop);
    bad.asset_count = bad.assets.length;
    assert.throws(
      () => readReleaseManifest(bad, config),
      new RegExp(drop.replace(".", "\\.")),
      drop,
    );
  }
});

test("a release carrying no headshot at all is still a release", () => {
  // Headshots are identity, not data. Their absence degrades to initials; it is not a refusal.
  const thin = manifest();
  thin.assets = thin.assets.filter((a) => !a.path.startsWith("headshots/"));
  thin.asset_count = thin.assets.length;
  assert.equal(readReleaseManifest(thin, config).assets.size, 2);
});
