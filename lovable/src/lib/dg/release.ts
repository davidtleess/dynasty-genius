/**
 * DG-213 — hosted release delivery.
 *
 * The app reads either from the local preview or from one immutable public release, and the choice is
 * made once, explicitly, by `release.config.ts`. There is no path from one mode to the other at
 * runtime. That is the whole design: a fallback between them would mean the screen could show a
 * different capture than the one it claims, and nothing on the page would say so.
 *
 * Every document is hashed against the manifest before it is parsed, and the manifest itself is hashed
 * against a constant that root supplies out of band. A mismatch is a refusal. It is never a retry
 * somewhere else, never the prototype scorer, and never a different reading.
 */
export class ReleaseError extends Error {}

/**
 * Where a release lives and the one hash that proves its manifest. Defined here and imported by the
 * config so this module stays pure: it reads no global and imports nothing, which is why the whole of
 * it is testable without a bundler.
 */
export type ReleaseConfig = {
  /** Where the release's objects live. Must end in a slash. */
  base_url: string;
  /** sha256 of `asset-manifest.json` at that base. Supplied out of band, never read from the manifest. */
  manifest_sha256: string;
};

export type ReleaseAsset = {
  path: string;
  url: string;
  sha256: string;
  bytes: number;
  contentType: string;
};
export type Release = {
  release_base: string;
  source_commit: string;
  snapshot_id: string;
  assets: Map<string, ReleaseAsset>;
};

const HEX64 = /^[a-f\d]{64}$/;

/**
 * The app fetches exactly three kinds of object, so the manifest is read as a list of expected files
 * rather than as a directory listing. This is deliberately not configurable: a release that needs a
 * fourth shape needs a new schema version and a review, not a config key. Anything else in the
 * manifest is either a mistake or an attempt to make the app fetch something, and both are refusals.
 */
const DATASETS = ["dg-bundle.json", "track-record.json"] as const;
const HEADSHOT = /^headshots\/\d+\.jpg$/;
const expectedPath = (path: string) =>
  (DATASETS as readonly string[]).includes(path) || HEADSHOT.test(path);

/**
 * Shapes that must never reach a URL join. The allowlist above already excludes all of them, but they
 * are checked first and named individually: "that path is not one of the three" is a true message and
 * a useless one when the real answer is that the manifest tried to point somewhere else entirely.
 */
function needSafePath(path: string, index: number): void {
  const unsafe: Array<[boolean, string]> = [
    [path.includes("?") || path.includes("#"), "carries a query or fragment"],
    [path.includes("\\"), "contains a backslash"],
    [path.startsWith("/"), "is absolute"],
    [/^[a-z][a-z\d+.-]*:/i.test(path), "is a url, not a path within the release"],
    [path.split("/").includes(".."), "escapes the release base"],
    [/%2e|%2f|%5c/i.test(path), "carries a percent-encoded separator"],
  ];
  for (const [bad, why] of unsafe) need(!bad, `asset ${index} path ${JSON.stringify(path)} ${why}`);
}
const object = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
function need(condition: unknown, what: string): asserts condition {
  if (!condition) throw new ReleaseError(`hosted release: ${what}`);
}

export function readReleaseManifest(value: unknown, config: ReleaseConfig): Release {
  need(object(value), "the asset manifest is not an object");
  const m = value as Record<string, unknown>;
  need(
    m["schema_version"] === "dg.delivery-assets.v1",
    `manifest schema ${String(m["schema_version"])} is not the one this app reads`,
  );
  need(typeof m["source_commit"] === "string", "the manifest names no source commit");
  need(HEX64.test(String(m["snapshot_id"])), "the manifest names no saved reading");
  need(Array.isArray(m["assets"]), "the manifest lists no assets");
  const list = m["assets"] as unknown[];
  // A count that disagrees with the list means the manifest was edited after it was generated, which
  // is exactly the case the hashes below cannot catch on their own.
  need(
    m["asset_count"] === list.length,
    `the manifest says ${String(m["asset_count"])} assets and lists ${list.length}`,
  );
  // https only, and no query or fragment: the base is joined by concatenation, so anything the base
  // carries would land in the middle of every asset url.
  need(config.base_url.startsWith("https://"), "the release base url must be https");
  need(config.base_url.endsWith("/"), "the release base url must end in a slash");
  need(
    !config.base_url.includes("?") && !config.base_url.includes("#"),
    "the release base url must carry no query or fragment",
  );

  const assets = new Map<string, ReleaseAsset>();
  list.forEach((entry, index) => {
    need(object(entry), `asset ${index} is not an object`);
    const a = entry as Record<string, unknown>;
    const raw = a["path"];
    need(typeof raw === "string" && raw.length > 0, `asset ${index} has no path`);
    const path = raw as string;
    needSafePath(path, index);
    need(
      expectedPath(path),
      `asset ${index} path ${JSON.stringify(path)} is not one this app reads`,
    );
    // A duplicate would be last-one-wins in the Map while the count still agreed, so a substituted
    // hash would travel inside an otherwise legitimate manifest.
    need(!assets.has(path), `the manifest lists ${path} more than once`);
    need(HEX64.test(String(a["sha256"])), `asset ${path} carries no full sha256`);
    // Zero bytes is not a small file, it is a file that was never written.
    need(
      Number.isInteger(a["bytes"]) && (a["bytes"] as number) > 0,
      `asset ${path} carries no positive byte length`,
    );
    assets.set(path, {
      path,
      url: `${config.base_url}${path}`,
      sha256: a["sha256"] as string,
      bytes: a["bytes"] as number,
      contentType: typeof a["content_type"] === "string" ? (a["content_type"] as string) : "",
    });
  });
  // Headshots are identity and may legitimately be absent — the card falls back to initials. The two
  // datasets are the reading itself: without either, there is nothing honest to render.
  for (const dataset of DATASETS) need(assets.has(dataset), `the release carries no ${dataset}`);
  return {
    release_base: config.base_url,
    source_commit: m["source_commit"] as string,
    snapshot_id: m["snapshot_id"] as string,
    assets,
  };
}

/** A path the manifest does not list is refused by name. Fetching it hopefully is how a 404 becomes data. */
export function resolveAsset(release: Release, path: string): ReleaseAsset {
  const asset = release.assets.get(path);
  need(asset, `the release does not carry ${path}`);
  return asset as ReleaseAsset;
}

/**
 * In hosted mode a player absent from the release returns null, so the identity falls back to initials
 * without a request that would 404. In local mode the existing path is unchanged, because the local
 * preview has always relied on the image's own error to trigger the fallback.
 */
export function headshotUrl(release: Release | null, playerId: string): string | null {
  const encoded = encodeURIComponent(playerId);
  if (!release) return `/assets/headshots/${encoded}.jpg`;
  return release.assets.get(`headshots/${playerId}.jpg`)?.url ?? null;
}

/**
 * Hosted readings are fixed and read-only. The reason says where saving lives rather than describing a
 * failure, because nothing has failed.
 */
export function hostedSaveCapability(): { enabled: false; reason: string; expected: null } {
  return {
    enabled: false,
    reason: "Saving new readings is available in the Mac preview.",
    expected: null,
  };
}

/**
 * Honour a pinned reading or refuse it. Serving a different capture than the link names is the worst
 * failure this screen has, because the reader believes he is looking at the one he pinned.
 */
export function selectHostedReading<T extends { selected?: unknown; snapshots?: unknown }>(
  view: T,
  release: Release,
  pinned: string | null,
): T & { selected: { snapshot_id: string } } {
  const selected = (view as { selected?: { snapshot_id?: unknown } }).selected;
  need(
    object(selected) && typeof selected.snapshot_id === "string",
    "the published reading names no snapshot",
  );
  const id = selected.snapshot_id as string;
  need(
    id === release.snapshot_id,
    "the published reading does not belong to this release; refusing rather than showing it",
  );
  if (pinned !== null)
    need(pinned === id, `this release does not carry the reading ${pinned.slice(0, 12)}…`);
  return view as T & { selected: { snapshot_id: string } };
}
