// DG-076: build-manifest emitter — node-env tests for the pure computation and
// the Vite plugin wrapper. No network, no real vite build; the plugin hook is
// driven directly with a captured emitFile.

import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  buildManifestPlugin,
  computeBuildManifest,
  hashFileSha256,
  readSourceSha,
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

beforeEach(() => {
  scratchDir = mkdtempSync(join(tmpdir(), "dg076-manifest-"));
  openapiPath = join(scratchDir, "openapi.json");
  writeFileSync(openapiPath, FIXTURE_BODY);
});

afterEach(() => {
  rmSync(scratchDir, { recursive: true, force: true });
});

describe("computeBuildManifest (DG-076)", () => {
  it("reports the repo's actual HEAD, the openapi bytes as-is, and the injected clock", () => {
    const expectedSha = execFileSync("git", ["-C", REPO_ROOT, "rev-parse", "HEAD"])
      .toString()
      .trim();

    const manifest = computeBuildManifest({
      repoRoot: REPO_ROOT,
      openapiPath,
      now: FIXED_NOW,
    });

    expect(manifest).toEqual({
      built_at: "2026-08-29T22:15:00.000Z",
      openapi_sha256: FIXTURE_SHA256,
      source_sha: expectedSha,
    });
    expect(manifest.source_sha).toMatch(/^[0-9a-f]{40}$/);
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
    const plugin = buildManifestPlugin({
      repoRoot: REPO_ROOT,
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
      source_sha: readSourceSha(REPO_ROOT),
    });
  });

  it("computes the manifest once per build: timestamp read at build, injected once", () => {
    let calls = 0;
    const plugin = buildManifestPlugin({
      repoRoot: REPO_ROOT,
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
