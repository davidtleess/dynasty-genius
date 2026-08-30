// THE FIXTURE-ROT LOCK — DG-118.
//
// Every file in this directory was captured read-only from the running product
// and frozen. A frozen payload is only useful while the contract it was frozen
// against still holds: when the API grows a required field, the fixture keeps
// the OLD shape, the product's own `zod.gen.ts` parse rejects it, and the
// surface quietly renders a degraded branch instead of the one under test.
//
// That is not hypothetical. The browser gate's hand-written capture-health
// fixture had drifted out of `zCaptureHealthResponse` (missing `backup`, added
// to the response, and `schedule_drift`, added to StoreHealth) and had been
// silently parse-erroring on the front page on every gate run. Nothing caught
// it, because capture-health is a SECONDARY read: a parse failure there does
// not produce a parse-error card, it rewrites one sentence about David's data
// and leaves every other assertion — rows, text length, axe, overflow — green.
// The gate's own receipt was clean while the thing it was grading was wrong.
//
// So the check does not live in an assertion about rendered output. It lives
// here, at the fixture: each file is parsed against the SAME generated schema
// the product parses that endpoint with, in the three-second unit suite
// (`liveFixtures.test.js`) and again at module load in the browser gate
// (`e2e/visual-smoke.spec.ts`). Regenerate `zod.gen.ts` with a new required
// field and both go red naming the file.
import type { ZodType } from "zod";

import {
  zCaptureHealthResponse,
  zLeaguePulseResponse,
  zModelCardResponse,
  zModelProvenanceResponse,
  zModelScoreboardResponse,
  zPlayerDetailResponse,
  zRealizedOutcomeScorecardResponse,
  zRosterAuditResponse,
  zRosterCapacityResponse,
  zSystemHealthResponse,
  zTrustSurfaceResponse,
  zWhatChangedResponse,
} from "../api/zod.gen";

/**
 * Fixture file name → the generated schema its endpoint is parsed with.
 *
 * Keyed by FILE NAME rather than by endpoint because two fixtures can stand for
 * the same endpoint: `whatChangedDegraded.live.json` is the same contract as
 * `whatChanged.live.json` captured in a degraded state, and a degraded response
 * is still the response schema — that is the point of `overall_status`.
 */
export const LIVE_FIXTURE_SCHEMAS: Record<string, ZodType> = {
  "captureHealth.live.json": zCaptureHealthResponse,
  "leaguePulse.live.json": zLeaguePulseResponse,
  "modelCard.live.json": zModelCardResponse,
  "modelProvenance.live.json": zModelProvenanceResponse,
  "modelScoreboard.live.json": zModelScoreboardResponse,
  "playerDetail.live.json": zPlayerDetailResponse,
  "realizedOutcome.live.json": zRealizedOutcomeScorecardResponse,
  "rosterAudit.live.json": zRosterAuditResponse,
  "rosterCapacity.live.json": zRosterCapacityResponse,
  "systemHealth.live.json": zSystemHealthResponse,
  "trustSurface.live.json": zTrustSurfaceResponse,
  "whatChanged.live.json": zWhatChangedResponse,
  "whatChangedDegraded.live.json": zWhatChangedResponse,
};

/**
 * Parses one fixture against its endpoint's schema.
 *
 * Throws with the file name and the first few Zod issues, because the failure a
 * reader needs is "which file, which field" — a bare ZodError inside a
 * Playwright module load reads like a broken test rather than a rotted fixture.
 */
export function parseLiveFixture(name: string, raw: unknown): unknown {
  const schema = LIVE_FIXTURE_SCHEMAS[name];
  if (schema === undefined) {
    throw new Error(
      `${name} has no schema in LIVE_FIXTURE_SCHEMAS. Every live fixture must be pinned to the generated schema its endpoint is parsed with, or it can rot without anything noticing.`,
    );
  }

  const result = schema.safeParse(raw);
  if (result.success) {
    return result.data;
  }

  const issues = result.error.issues
    .slice(0, 8)
    .map((issue) => `  ${issue.path.join(".") || "(root)"}: ${issue.message}`)
    .join("\n");
  throw new Error(
    `${name} no longer satisfies the schema its endpoint is parsed with. Re-capture it from the running product; do not hand-edit it.\n${issues}${
      result.error.issues.length > 8
        ? `\n  …and ${result.error.issues.length - 8} more`
        : ""
    }`,
  );
}
