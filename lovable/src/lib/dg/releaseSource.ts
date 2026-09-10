/**
 * DG-213 — the hosted transport. Thin on purpose.
 *
 * Every rule about what a release may contain lives in `release.ts`, which imports nothing and is
 * tested without a bundler. This file only fetches bytes, hashes them, and refuses. It is the one
 * place that knows the app might not be reading from disk.
 *
 * The order matters and is the whole point: bytes are hashed BEFORE they are parsed, and the manifest
 * is hashed against a constant that came from root out of band rather than from the manifest itself.
 * A document that fails its hash is never parsed, never partially applied, and never retried
 * somewhere else.
 */
import { readReleaseManifest, resolveAsset, ReleaseError, type Release } from "./release.ts";
import { RELEASE } from "./release.config.ts";

/** True when this build reads a published release. Decided at build time; never at runtime. */
export const hosted = RELEASE !== null;

let loaded: Release | null = null;
let request: Promise<Release> | undefined;

async function sha256(bytes: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Exported so the fetch path itself is tested. Every other check in this file is pure and cheap to
 * test; this one talks to the network, which is exactly why leaving it unexercised would mean the
 * hash and byte checks were only ever proved on paper.
 */
export async function readVerified(
  url: string,
  expected: string,
  what: string,
  declaredBytes?: number,
): Promise<unknown> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new ReleaseError(`${what} could not be read (${response.status})`);
  const bytes = await response.arrayBuffer();
  // The declared length is part of the manifest's contract, so it is checked and it is checked first.
  // It is not a second integrity proof — a substitution that survived the hash below could not fail
  // here — but a manifest whose own numbers disagree with the object it names is a broken manifest,
  // and saying so costs one comparison instead of hashing tens of megabytes to reach the same refusal.
  if (declaredBytes !== undefined && bytes.byteLength !== declaredBytes)
    throw new ReleaseError(
      `${what} is ${bytes.byteLength} bytes where this release declares ${declaredBytes}, so it has not been read.`,
    );
  const actual = await sha256(bytes);
  if (actual !== expected)
    throw new ReleaseError(`${what} is not the file this release names, so it has not been read.`);
  return JSON.parse(new TextDecoder().decode(bytes));
}

/**
 * The release, once. Concurrent callers share one manifest fetch.
 *
 * A rejection is remembered for the life of the page, which is deliberate rather than an oversight:
 * the recovery already on the screen is "Reload saved reading" in the header, a whole-page reload that
 * clears this module and starts clean. An in-process retry would be a second recovery path for the
 * same failure, and the pinned constants mean a retry could only ever re-fetch the identical object.
 */
export function release(): Promise<Release> {
  const config = RELEASE;
  if (!config)
    return Promise.reject(new ReleaseError("this build reads the local preview, not a release"));
  if (!request)
    request = readVerified(
      `${config.base_url}asset-manifest.json`,
      config.manifest_sha256,
      "the release manifest",
    ).then((value) => (loaded = readReleaseManifest(value, config)));
  return request;
}

/**
 * The release as already loaded, for the one caller that cannot await: the row mapper runs after the
 * bundle has been read, and the bundle cannot be read before the manifest. In local mode this is null
 * forever, which is exactly what `headshotUrl` expects.
 */
export function releaseNow(): Release | null {
  return loaded;
}

/** Read one asset the manifest lists, verified against the hash the manifest gives for it. */
export async function readAsset(path: string): Promise<unknown> {
  const asset = resolveAsset(await release(), path);
  return readVerified(asset.url, asset.sha256, path, asset.bytes);
}
