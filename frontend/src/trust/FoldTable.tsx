// Model Trust Console — FoldTable (T8). The per-fold evidence.
//
// The honest, fold-by-fold substantiation of "edge unproven": each row shows the fold's
// rank-correlation point estimates (Kendall tau, Spearman rho, rank IC) alongside their
// BCa 95% CIs. When a fold's Kendall OR Spearman CI band spans zero, the row carries an
// explicit NEUTRAL "CI includes zero" note — a factual statement that the per-fold edge
// is statistically indistinguishable from zero, NOT a pass/fail or red/green judgement.
import type { TrustConsoleViewModel } from "./trustViewModel";

type Fold = TrustConsoleViewModel["folds"][number];
type Band = readonly [number, number];

const f2 = (n: number): string => n.toFixed(2);
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
      <table className="dg-trust-folds__table" aria-label="Per-fold backtest results">
        <thead>
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
    </section>
  );
}
