// Model Trust Console — FoldTable (T8). The per-fold evidence.
//
// The honest, fold-by-fold substantiation of "edge unproven": each row shows the fold's
// rank-correlation point estimates (Kendall tau, Spearman rho, rank IC) alongside their
// BCa 95% CIs. When a fold's Kendall OR Spearman CI band spans zero, the row carries an
// explicit NEUTRAL "CI includes zero" note — a factual statement that the per-fold edge
// is statistically indistinguishable from zero, NOT a pass/fail or red/green judgement.
import { TableScroll } from "../ui/TableScroll";
import type { TrustConsoleViewModel } from "./trustViewModel";

type Fold = TrustConsoleViewModel["folds"][number];
type Band = readonly [number, number];

// Display-only: collapse the negative-zero artifact (e.g. -0.004 -> "-0.00") to "0.00".
// This NEVER touches includesZero, which runs on the raw band numbers — a raw -0.003 lower
// bound still counts as CI-includes-zero even though it now displays as 0.00.
const f2 = (n: number): string => {
  const s = n.toFixed(2);
  return s === "-0.00" ? "0.00" : s;
};
const ci = (band: Band): string => `[${f2(band[0])}, ${f2(band[1])}]`;

// CI includes zero <=> the closed band straddles (or touches) zero.
const includesZero = (band: Band): boolean => band[0] <= 0 && band[1] >= 0;

const COLUMNS = [
  "Fold",
  "Train years",
  "Test year",
  "N train",
  "N test",
  "Kendall tau",
  "Kendall CI95",
  "Spearman rho",
  "Spearman CI95",
  "Rank IC",
  "RMSE",
  "MAE",
  "CI note",
] as const;

export function FoldTable({ folds }: { folds: TrustConsoleViewModel["folds"] }) {
  if (folds.length === 0) {
    return <p className="dg-trust-folds__empty">No fold data</p>;
  }

  return (
    <section className="dg-trust-folds" aria-label="Per-fold backtest results section">
      {/* DG-109: this table IS the receipt for "edge unproven" — a statistician's
          worksheet, cited by its real statistic names (Kendall tau, RMSE, MAE) so
          the numbers can be checked against the artifact. Renaming the columns
          would stop it being a receipt, so the exemption is DECLARED here rather
          than left implicit. The sentence a manager reads is the truth panel
          above it; this is the working underneath. */}
      {/* DG-120: `data-quoted` carries a condition the rule states — the source
          must be NAMED ON SCREEN beside the quotation, so a reader knows whose
          words they are reading. "In the statistician's own terms" named a
          register, not a document, and the document was named only in the
          comment below. It is named here now, where David can see it. */}
      <p className="dg-trust-lede">
        The season-by-season working behind that, with the backtest artifact's own
        column names kept as it writes them.
      </p>
      {/* DG-117: thirteen columns of statistics, `white-space: nowrap` on every
          cell, 1039px of table inside a 358px column at 390px — and the page
          took all 665px of the overflow. Model Trust was the worst sideways
          scroll in the product. The receipt keeps every column; the scrolling
          moves inside it. */}
      <TableScroll label="Per-fold backtest results">
        <table
          className="dg-trust-folds__table"
          aria-label="Per-fold backtest results"
          data-receipt
        >
          {/* DG-120: the exemption narrows to the HEADER ROW, which is the part
              that quotes the backtest artifact's own vocabulary — "RMSE" is the
              statistic's real name and the reason a number here can be checked
              against `eval/backtest_artifact.py`. The body cells are numbers and
              the CI note is our sentence; both are audited like any other copy,
              where before the whole table was waved through. */}
          <thead data-quoted>
            <tr>
              {COLUMNS.map((col) => (
                <th key={col} scope="col">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {folds.map((fold: Fold) => {
              const ciIncludesZero =
                includesZero(fold.kendall_tau_bca_ci95) ||
                includesZero(fold.spearman_rho_bca_ci95);
              return (
                <tr key={fold.fold_index}>
                  <td>Fold {fold.fold_index}</td>
                  <td>{fold.train_years.join(", ")}</td>
                  <td>{fold.test_year}</td>
                  <td>{fold.n_train}</td>
                  <td>{fold.n_test}</td>
                  <td>{f2(fold.kendall_tau)}</td>
                  <td>{ci(fold.kendall_tau_bca_ci95)}</td>
                  <td>{f2(fold.spearman_rho)}</td>
                  <td>{ci(fold.spearman_rho_bca_ci95)}</td>
                  <td>{f2(fold.rank_ic)}</td>
                  <td>{f2(fold.rmse)}</td>
                  <td>{f2(fold.mae)}</td>
                  <td className="dg-trust-folds__ci-note">
                    {ciIncludesZero ? "CI includes zero" : ""}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </TableScroll>
    </section>
  );
}
