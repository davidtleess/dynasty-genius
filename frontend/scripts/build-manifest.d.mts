// DG-076: hand-written declarations for build-manifest.mjs so vite.config.ts
// (typechecked by `tsc --noEmit`) can import it. The repo intentionally has no
// @types/node dev-dependency, so the implementation stays untyped node ESM
// like the other scripts/ tools; this file is the typed seam.

import type { Plugin } from "vite";

export interface BuildManifest {
  built_at: string;
  openapi_sha256: string;
  /** True when the tree that produced this bundle was not `source_sha` itself. */
  source_dirty: boolean;
  source_sha: string;
}

export interface BuildManifestOptions {
  repoRoot?: string;
  openapiPath?: string;
  now?: () => Date;
}

export declare const MANIFEST_FILE_NAME: string;
export declare function readSourceSha(repoRoot: string): string;
export declare function readTreeDirty(repoRoot: string): boolean;
export declare function hashFileSha256(filePath: string): string;
export declare function computeBuildManifest(
  options?: BuildManifestOptions,
): BuildManifest;
export declare function buildManifestPlugin(options?: BuildManifestOptions): Plugin;
