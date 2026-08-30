// DG-076: build-manifest emitter — node-env tests for the pure computation and
// the Vite plugin wrapper. No network, no real vite build; the plugin hook is
// driven directly with a captured emitFile.

import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  buildManifestPlugin,
  computeBuildManifest,
  hashFileSha256,
  readSourceSha,
  readTreeDirty,
} from "./build-manifest.mjs";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
// sha256 of exactly `{"openapi":"3.1.0"}\n` — precomputed, so the test proves
// the module hashes the file's bytes as-is (regen trap: never regenerate).
const FIXTURE_BODY = '{"openapi":"3.1.0"}\n';
const FIXTURE_SHA256 =
  "7927cf5b451b44fb947646f0e189a8b41ed29b043923cf030c42d00da8a3b072";
const VARIANT_BODY = '{"openapi":"3.1.1"}\n';
const VARIANT_SHA256 =
  "eaf14cc54f3c50063ff0da05a2a043b359a0439d682c87695183882934e62faa";
const FIXED_NOW = () => new Date("2026-08-29T22:15:00.000Z");

let scratchDir;
let openapiPath;
let repoDir;

/** A throwaway git repo with one commit, so tree-state assertions are
 * deterministic — the DG-076 worktree itself is dirty exactly when it is
 * mid-edit, which would make these tests weather-dependent. */
function makeGitRepo() {
  const dir = mkdtempSync(join(tmpdir(), "dg076-repo-"));
  const git = (...args) =>
    execFileSync("git", ["-C", dir, ...args], { stdio: ["ignore", "pipe", "pipe"] });
  git("init", "-q");
  git("config", "user.email", "dg076@example.invalid");
  git("config", "user.name", "DG-076 test");
  writeFileSync(join(dir, "tracked.txt"), "one\n");
  writeFileSync(join(dir, ".gitignore"), "dist/\n");
  git("add", "tracked.txt", ".gitignore");
  git("commit", "-q", "-m", "seed");
  return { dir, git };
}

beforeEach(() => {
  scratchDir = mkdtempSync(join(tmpdir(), "dg076-manifest-"));
  openapiPath = join(scratchDir, "openapi.json");
  writeFileSync(openapiPath, FIXTURE_BODY);
  repoDir = null;
});

afterEach(() => {
  rmSync(scratchDir, { recursive: true, force: true });
  if (repoDir) rmSync(repoDir, { recursive: true, force: true });
});

describe("readTreeDirty (DG-076 provenance honesty)", () => {
  it("is false for a clean checkout", () => {
    const { dir } = makeGitRepo();
    repoDir = dir;
    expect(readTreeDirty(dir)).toBe(false);
  });

  it("is TRUE when an untracked source file is present — the file the bundle compiles but HEAD lacks", () => {
    // This is the exact defect that shipped: BuildStamp.tsx existed only in the
    // working tree, so the bundle carried code the named commit did not have.
    const { dir } = makeGitRepo();
    repoDir = dir;
    writeFileSync(join(dir, "BuildStamp.tsx"), "export const x = 1;\n");
    expect(readTreeDirty(dir)).toBe(true);
  });

  it("is true when a tracked file is modified", () => {
    const { dir } = makeGitRepo();
    repoDir = dir;
    writeFileSync(join(dir, "tracked.txt"), "two\n");
    expect(readTreeDirty(dir)).toBe(true);
  });

  it("ignores the build's own gitignored output — dist/ never marks its own provenance dirty", () => {
    const { dir } = makeGitRepo();
    repoDir = dir;
    mkdirSync(join(dir, "dist", "assets"), { recursive: true });
    writeFileSync(join(dir, "dist", "assets", "index.js"), "console.log(1);\n");
    expect(readTreeDirty(dir)).toBe(false);
  });

  it("fails loud outside a git checkout rather than guessing clean", () => {
    expect(() => readTreeDirty(scratchDir)).toThrow(/tree status/i);
  });
});

describe("computeBuildManifest (DG-076)", () => {
  it("reports the repo's actual HEAD, the openapi bytes as-is, and the injected clock", () => {
    const { dir } = makeGitRepo();
    repoDir = dir;
    const expectedSha = execFileSync("git", ["-C", dir, "rev-parse", "HEAD"])
      .toString()
      .trim();

    const manifest = computeBuildManifest({
      repoRoot: dir,
      openapiPath,
      now: FIXED_NOW,
    });

    expect(manifest).toEqual({
      built_at: "2026-08-29T22:15:00.000Z",
      openapi_sha256: FIXTURE_SHA256,
      source_dirty: false,
      source_sha: expectedSha,
    });
    expect(manifest.source_sha).toMatch(/^[0-9a-f]{40}$/);
  });

  it("marks the sha dirty when the tree that built it is not that commit", () => {
    const { dir } = makeGitRepo();
    repoDir = dir;
    writeFileSync(join(dir, "BuildStamp.tsx"), "export const x = 1;\n");

    const manifest = computeBuildManifest({
      repoRoot: dir,
      openapiPath,
      now: FIXED_NOW,
    });

    expect(manifest.source_dirty).toBe(true);
    // The sha is still reported — it is the nearest true anchor — but it is no
    // longer presented as the tree that produced the bundle.
    expect(manifest.source_sha).toMatch(/^[0-9a-f]{40}$/);
  });

  it("reads the real repo it runs in", () => {
    const expectedSha = execFileSync("git", ["-C", REPO_ROOT, "rev-parse", "HEAD"])
      .toString()
      .trim();
    const manifest = computeBuildManifest({
      repoRoot: REPO_ROOT,
      openapiPath,
      now: FIXED_NOW,
    });
    expect(manifest.source_sha).toBe(expectedSha);
    expect(typeof manifest.source_dirty).toBe("boolean");
  });

  it("hashes the working copy byte-for-byte: one changed byte, different hash", () => {
    expect(hashFileSha256(openapiPath)).toBe(FIXTURE_SHA256);
    writeFileSync(openapiPath, VARIANT_BODY);
    expect(hashFileSha256(openapiPath)).toBe(VARIANT_SHA256);
  });

  it("fails loud rather than emitting a mystery manifest", () => {
    // A directory outside any git repo cannot state a source sha.
    expect(() => readSourceSha(scratchDir)).toThrow(/source sha/i);
    // A missing openapi working copy cannot state a schema hash.
    expect(() =>
      computeBuildManifest({
        repoRoot: REPO_ROOT,
        openapiPath: join(scratchDir, "missing.json"),
        now: FIXED_NOW,
      }),
    ).toThrow();
  });
});

describe("buildManifestPlugin (DG-076)", () => {
  it("is build-only and emits exactly one manifest asset under assets/", () => {
    const { dir } = makeGitRepo();
    repoDir = dir;
    const plugin = buildManifestPlugin({
      repoRoot: dir,
      openapiPath,
      now: FIXED_NOW,
    });
    expect(plugin.name).toBe("dg-build-manifest");
    expect(plugin.apply).toBe("build");

    const emitted = [];
    plugin.buildStart.call({});
    plugin.generateBundle.call({
      emitFile: (file) => {
        emitted.push(file);
      },
    });

    expect(emitted).toHaveLength(1);
    expect(emitted[0].type).toBe("asset");
    expect(emitted[0].fileName).toBe("assets/build-manifest.json");
    const parsed = JSON.parse(emitted[0].source);
    expect(parsed).toEqual({
      built_at: "2026-08-29T22:15:00.000Z",
      openapi_sha256: FIXTURE_SHA256,
      source_dirty: false,
      source_sha: readSourceSha(dir),
    });
  });

  it("carries the dirty marker all the way into the emitted asset", () => {
    const { dir } = makeGitRepo();
    repoDir = dir;
    writeFileSync(join(dir, "BuildStamp.tsx"), "export const x = 1;\n");
    const plugin = buildManifestPlugin({
      repoRoot: dir,
      openapiPath,
      now: FIXED_NOW,
    });

    const emitted = [];
    plugin.buildStart.call({});
    plugin.generateBundle.call({
      emitFile: (file) => {
        emitted.push(file);
      },
    });

    expect(JSON.parse(emitted[0].source).source_dirty).toBe(true);
  });

  it("computes the manifest once per build: timestamp read at build, injected once", () => {
    let calls = 0;
    const { dir } = makeGitRepo();
    repoDir = dir;
    const plugin = buildManifestPlugin({
      repoRoot: dir,
      openapiPath,
      now: () => {
        calls += 1;
        return new Date("2026-08-29T22:15:00.000Z");
      },
    });

    const emitted = [];
    plugin.buildStart.call({});
    plugin.generateBundle.call({
      emitFile: (file) => {
        emitted.push(file);
      },
    });

    expect(calls).toBe(1);
    expect(emitted).toHaveLength(1);
  });
});
