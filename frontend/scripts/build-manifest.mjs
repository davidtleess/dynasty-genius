// DG-076: frontend build manifest — emitted into dist at build time so the
// served page can always say what build it is (no more week-stale-bundle
// mysteries: dist built Aug 22 was serving three days behind an Aug 25 trunk
// with nothing to flag it).
//
// The manifest carries exactly four facts, each read ONCE per build:
//   source_sha      — `git rev-parse HEAD` of the repo the build runs in
//   source_dirty    — whether the tree differed from that commit at build time.
//                     A sha alone is a FALSE receipt for a dirty build: the
//                     named commit is not the tree that produced the bundle.
//                     (This module's own first artifact proved it — a manifest
//                     naming a commit that contained no BuildStamp.tsx, sitting
//                     beside a bundle that did.) The build still succeeds —
//                     building mid-edit is normal — but it says so, and the
//                     ticket's sha-vs-serving-HEAD health check must treat a
//                     dirty build as "cannot match" rather than "match".
//   openapi_sha256  — sha256 of frontend/openapi.json AS-IS, byte-for-byte.
//                     REGEN TRAP (reference_openapi_regen_trap): never
//                     regenerate the working copy to get this hash — a dirty
//                     regen can silently revert landed commits. Hash what is
//                     on disk; a schema change shows up as a different hash.
//   built_at        — ISO-8601 UTC timestamp, read at build, injected once
//
// Failure policy: fail LOUD. A build that cannot state its own provenance is
// exactly the mystery this ticket exists to end — never emit a partial or
// guessed manifest.
//
// The emitted file lands at dist/assets/build-manifest.json deliberately:
// app/main.py mounts only dist/assets/ as static files (the SPA fallback 404s
// any other extension path), and `vite preview` serves dist/ at the root — so
// /assets/build-manifest.json is fetchable in both without backend changes.

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const DEFAULT_REPO_ROOT = resolve(SCRIPT_DIR, "..", "..");
const DEFAULT_OPENAPI_PATH = resolve(SCRIPT_DIR, "..", "openapi.json");
export const MANIFEST_FILE_NAME = "assets/build-manifest.json";

/** `git rev-parse HEAD` for the repo (worktrees included). Throws loud when
 * the directory cannot state a sha — never returns a guess. */
export function readSourceSha(repoRoot) {
  let raw;
  try {
    raw = execFileSync("git", ["-C", repoRoot, "rev-parse", "HEAD"], {
      stdio: ["ignore", "pipe", "pipe"],
    })
      .toString()
      .trim();
  } catch (cause) {
    throw new Error(
      `DG-076 build manifest: cannot read source sha from ${repoRoot} (is it a git checkout?)`,
      { cause },
    );
  }
  if (!/^[0-9a-f]{40}$/.test(raw)) {
    throw new Error(
      `DG-076 build manifest: git rev-parse returned a non-sha: ${JSON.stringify(raw)}`,
    );
  }
  return raw;
}

/** True when the working tree differs from HEAD — staged or unstaged edits to
 * tracked files, and untracked files too (an untracked .tsx still compiles into
 * the bundle, which is precisely how the first false receipt happened).
 *
 * `git status --porcelain` omits gitignored paths by default, so the build's
 * own dist/ output and node_modules never mark their own provenance dirty.
 * Throws loud when the directory cannot answer — a build that cannot tell
 * whether its tree is clean cannot state provenance at all. */
export function readTreeDirty(repoRoot) {
  let raw;
  try {
    raw = execFileSync("git", ["-C", repoRoot, "status", "--porcelain"], {
      stdio: ["ignore", "pipe", "pipe"],
    }).toString();
  } catch (cause) {
    throw new Error(
      `DG-076 build manifest: cannot read tree status from ${repoRoot} (is it a git checkout?)`,
      { cause },
    );
  }
  return raw.trim().length > 0;
}

/** sha256 hex digest of the file's bytes exactly as they sit on disk. */
export function hashFileSha256(filePath) {
  return createHash("sha256").update(readFileSync(filePath)).digest("hex");
}

/** Compute the full manifest. Every value is read here, once. */
export function computeBuildManifest({
  repoRoot = DEFAULT_REPO_ROOT,
  openapiPath = DEFAULT_OPENAPI_PATH,
  now = () => new Date(),
} = {}) {
  return {
    built_at: now().toISOString(),
    openapi_sha256: hashFileSha256(openapiPath),
    source_dirty: readTreeDirty(repoRoot),
    source_sha: readSourceSha(repoRoot),
  };
}

/** Vite plugin: build-only; computes the manifest once per build (buildStart)
 * and emits it as a plain asset the app can fetch. */
export function buildManifestPlugin(options = {}) {
  let manifest = null;
  return {
    name: "dg-build-manifest",
    apply: "build",
    buildStart() {
      // Computed here — once per build, watch rebuilds included — so every
      // chunk of one build carries one identity. Throws (loud) on failure.
      manifest = computeBuildManifest(options);
    },
    generateBundle() {
      if (manifest === null) {
        throw new Error("DG-076 build manifest: buildStart never ran");
      }
      this.emitFile({
        type: "asset",
        fileName: MANIFEST_FILE_NAME,
        source: `${JSON.stringify(manifest, null, 2)}\n`,
      });
    },
  };
}
