// DG-076: the served page says what build it is. Reads the manifest that
// `vite build` emits into dist/assets/ (source sha, openapi hash, timestamp)
// and renders it as one muted line inside the status drawer's receipts panel.
// Fail-silent-honest: no manifest (dev server, pre-DG-076 dist), unreachable,
// or shape drift → no stamp. The stamp never guesses an identity.
import { useEffect, useState } from "react";
import { z } from "zod";

const zBuildManifest = z.object({
  built_at: z.string(),
  openapi_sha256: z.string().regex(/^[0-9a-f]{64}$/),
  // Required, never defaulted: a manifest that cannot say whether its tree was
  // clean has unknown provenance, and rendering it would silently assert
  // "clean". Missing field → shape drift → no stamp.
  source_dirty: z.boolean(),
  source_sha: z.string().regex(/^[0-9a-f]{40}$/),
});

type BuildManifest = z.infer<typeof zBuildManifest>;

const MANIFEST_URL = "/assets/build-manifest.json";

const STAMP_TIME = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

export function BuildStamp() {
  const [manifest, setManifest] = useState<BuildManifest | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // no-cache = always revalidate (cheap 304 via ETag). The URL is fixed
        // and unhashed and StaticFiles sends no Cache-Control, so the default
        // heuristic cache could serve the PREVIOUS build's manifest beside the
        // new bundle — stale-as-fresh on the line that exists to end that.
        const res = await fetch(MANIFEST_URL, { cache: "no-cache" });
        if (!res.ok) return;
        const parsed = zBuildManifest.safeParse(await res.json());
        if (parsed.success && !cancelled) setManifest(parsed.data);
      } catch {
        // No manifest, no stamp — never a fabricated build identity.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (manifest === null) return null;

  // Same rule as the drawer pill: an unreadable stamp shows no time rather
  // than overstating one. The shas are the load-bearing identity either way.
  const built = new Date(manifest.built_at);
  const builtLabel = Number.isNaN(built.getTime())
    ? null
    : `${STAMP_TIME.format(built)} ET`;

  // A dirty build's commit is an anchor, not an identity — the tree that
  // produced this bundle was not that commit. Say so rather than let seven
  // clean-looking characters stand in for a tree they do not describe.
  const sourceTitle = manifest.source_dirty
    ? `source commit ${manifest.source_sha}, plus uncommitted changes — this build's tree is not that commit`
    : `source commit ${manifest.source_sha}`;

  return (
    <p className="dg-build-stamp" data-testid="dg-build-stamp">
      <span title={sourceTitle}>
        Build {manifest.source_sha.slice(0, 7)}
        {manifest.source_dirty && "+dirty"}
      </span>
      <span title={`openapi sha256 ${manifest.openapi_sha256}`}>
        schema {manifest.openapi_sha256.slice(0, 8)}
      </span>
      {builtLabel !== null && <time dateTime={manifest.built_at}>{builtLabel}</time>}
    </p>
  );
}
