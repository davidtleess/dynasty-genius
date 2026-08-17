// Read-only: the registered h5 block fields the round-6 deep gate binds to.
import { readFileSync } from "node:fs";
const r = JSON.parse(readFileSync(
  "/Users/davidleess/dynasty-genius-product/docs/validation/2026-07-21-qb-1-study-registration.json",
  "utf8",
));
console.log(JSON.stringify({ h5: r.h5, fold_floors: r.fold_floors }, null, 2).slice(0, 3000));
