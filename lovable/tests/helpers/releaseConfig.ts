/**
 * DG-213 — decide which delivery mode a test runs in, instead of inheriting whatever is committed.
 *
 * The problem this exists for. `release.config.ts` is production configuration: root fills it in when
 * a hosted destination exists, and `null` today is not a promise about tomorrow. Tests that silently
 * assumed `null` were not merely fragile — under a hosted config they **reached the real network**,
 * asserted the wrong thing, and failed for a reason that looks nothing like their subject. A test
 * suite whose result depends on a production constant is not a test suite.
 *
 * So each file states its mode. `pinLocal()` and `pinHosted()` substitute the config module's source
 * before it is ever loaded, using `node:module`'s synchronous `registerHooks` — no package, no flag,
 * no environment knob, and above all **no writing to the real config file**, which would make the
 * test run depend on being interrupted at the wrong moment.
 *
 * Two rules for callers, both load-bearing:
 *
 *   1. Call this at the TOP of the file, before importing anything that reads the config.
 *   2. Import the system under test with `await import(...)`, never a static import. A static import
 *      is hoisted above this call and resolves the real module first, at which point the module
 *      cache holds it and the hook can never be consulted.
 *
 * One mode per file, because the module cache is per process and `node --test` gives each file its
 * own process. A file that needs both modes is two files.
 */
import { registerHooks } from "node:module";

export type ReleaseFixture = { base_url: string; manifest_sha256: string } | null;

/** The exact module URL to intercept. Resolved from here so a moved file fails loudly, not silently. */
const CONFIG_URL = new URL("../../src/lib/dg/release.config.ts", import.meta.url).href;

function pin(value: ReleaseFixture): void {
  registerHooks({
    load(url: string, context: unknown, nextLoad: (u: string, c: unknown) => unknown) {
      if (url !== CONFIG_URL) return nextLoad(url, context);
      return {
        format: "module",
        shortCircuit: true,
        source: `export const RELEASE = ${JSON.stringify(value)};`,
      };
    },
  });
}

/** Local preview mode: no release, and every hosted path must refuse rather than invent a URL. */
export function pinLocal(): void {
  pin(null);
}

/** Hosted mode against a fixture base that is unroutable by construction. */
export function pinHosted(fixture: { base_url?: string; manifest_sha256: string }): {
  base_url: string;
  manifest_sha256: string;
} {
  // `.invalid` is reserved by RFC 2606 and can never resolve, so if a test ever escapes its stubbed
  // transport the failure is an immediate DNS refusal rather than a request to somebody's server.
  const config = {
    base_url: fixture.base_url ?? "https://dg-fixture.invalid/release/",
    manifest_sha256: fixture.manifest_sha256,
  };
  pin(config);
  return config;
}

/**
 * Serve a fixed set of URLs and REFUSE everything else by name.
 *
 * Refusing the unlisted URL is the point. A stub that returned a plausible empty response for an
 * unexpected request would let a test pass while the code fetched something nobody meant it to.
 */
export function stubNetwork(routes: Map<string, () => Response>): {
  requested: string[];
  restore: () => void;
} {
  const requested: string[] = [];
  const previous = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    requested.push(url);
    const route = routes.get(url);
    if (!route) {
      throw new Error(
        `test stub: nothing is registered for ${url}. A real request escaped the fixture.`,
      );
    }
    return route();
  }) as typeof fetch;
  return {
    requested,
    restore: () => {
      globalThis.fetch = previous;
    },
  };
}

/** sha256 of a string, as the release manifest records it. */
export async function sha256(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** A JSON response whose bytes are exactly `text`, so its hash is the one the manifest names. */
export const jsonResponse = (text: string): Response =>
  new Response(text, { headers: { "content-type": "application/json" } });
