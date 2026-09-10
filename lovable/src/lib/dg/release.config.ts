/**
 * DG-213 — the one isolated constant that chooses where the app reads from.
 *
 * `null` selects LOCAL mode: the app fetches `/data/dg-bundle.json` and the private track-record bridge.
 * A configured release selects HOSTED mode: a fixed, verified reading from public objects, read-only.
 *
 * The choice is explicit in both directions. Nothing in the app degrades from one mode to the other,
 * because a quiet degradation is how a reader ends up looking at data he did not ask for.
 */
import type { ReleaseConfig } from "./release";

/** All 957 public objects independently verified against the reviewed v4 export on September 10. */
export const RELEASE: ReleaseConfig | null = {
  base_url:
    "https://dbpqiogerduqolxqxjbs.supabase.co/storage/v1/object/public/dg-reading-2e3027eaeebb0b85/",
  manifest_sha256: "2e3027eaeebb0b85c3ee6c6d1ab771fa24721e7362ac09d3f21497effd808f42",
};
