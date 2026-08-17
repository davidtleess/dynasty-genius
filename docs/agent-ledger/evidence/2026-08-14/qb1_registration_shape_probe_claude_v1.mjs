// Read-only: extract the registered blocks the round-6 deep gate must bind to.
import { readFileSync } from "node:fs";
const r = JSON.parse(readFileSync(
  "/Users/davidleess/dynasty-genius-product/docs/validation/2026-07-21-qb-1-study-registration.json",
  "utf8",
));
const out = {
  topKeys: Object.keys(r),
  contrasts: (r.contrasts ?? []).map((c) => `${c.id}:${c.lane}:${c.direction}`),
  folds: r.folds ?? null,
  metrics: r.metrics ?? null,
  lanes: r.lanes ?? r.ridge_lanes ?? null,
  sensitivity: r.sensitivity_analyses ?? r.sensitivity ?? null,
  scoringKeys: Object.keys(r.scoring ?? {}),
};
console.log(JSON.stringify(out, null, 2).slice(0, 6000));
