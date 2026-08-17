// Read-only: the registered fold floors + inference/status blocks the round-7
// status-coherence gate binds to.
import { readFileSync } from "node:fs";
const r = JSON.parse(readFileSync(
  "/Users/davidleess/dynasty-genius-product/docs/validation/2026-07-21-qb-1-study-registration.json",
  "utf8",
));
console.log(JSON.stringify({ fold_floors: r.fold_floors, inference: r.inference }, null, 2).slice(0, 2500));
