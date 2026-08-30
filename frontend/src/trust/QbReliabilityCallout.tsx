// Model Trust Console — QbReliabilityCallout (T9). QB-only, neutral.
//
// QB is the model's weakest position; this surfaces its measured reliability (OOS R2,
// Spearman) framed as ELEVATED UNCERTAINTY — a descriptive caveat, never a defect/failure
// badge. Rendered only for QB with a present reliability stamp; null for every other case.
// Null figures render a neutral "not available" token rather than a fabricated number.
import { describeToken } from "../lib/copy";
import type { TrustConsoleViewModel } from "./trustViewModel";

const fmt = (n: number | null | undefined): string =>
  n === null || n === undefined ? "not available" : n.toFixed(2);

export function QbReliabilityCallout({
  position,
  reliability,
}: {
  position: string;
  reliability: TrustConsoleViewModel["model_reliability"];
}) {
  if (position !== "QB" || !reliability) {
    return null;
  }

  return (
    <section className="dg-trust-qb" aria-label="QB reliability note">
      <p className="dg-trust-qb__label">Elevated uncertainty</p>
      <p className="dg-trust-qb__caveat">{describeToken(reliability.caveat)}</p>
      {/* DG-109: these two read "OOS R2: 0.12" and "Spearman: 0.34" — the
          data-science register David rejected, on a component that rides the
          Model Trust surface. Both numbers are unchanged; only their names are.
          `OOS` also sat under the render rule's four-capital floor, so nothing
          would have caught it. */}
      <p className="dg-trust-qb__metric">
        Share of the variation it explains on unseen seasons:{" "}
        {fmt(reliability.r2_oos_mean)}
      </p>
      <p className="dg-trust-qb__metric">
        How closely its ranking tracks the real one:{" "}
        {fmt(reliability.spearman_rho_mean)}
      </p>
    </section>
  );
}
