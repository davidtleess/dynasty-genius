// DG primitive: uncertainty as a visual with a DISCLOSED basis and a numeric
// sigma label (benchmark §2.3 + Codex delta: never a decorative glyph). A
// missing value renders "Range unavailable" — never a false range.
import "./ui.css";

export function SpreadBar({
  label,
  value,
  sigma,
  basis,
  pct,
  lane = "model",
}: {
  label: string;
  value: number | null;
  sigma?: number | undefined;
  basis: string;
  /** Dot position 0–100 on a domain the basis discloses. Without it the dot
   *  does not render — a decoratively-placed dot would be miniature fiction
   *  (visual-audit finding F1, 2026-07-05). */
  pct?: number | undefined;
  /** Lane isolation (Increment 0, Codex R3): a market spread must never
   *  inherit model blue. Default stays model for every existing call site. */
  lane?: "model" | "market";
}) {
  if (value === null || !Number.isFinite(value)) {
    return (
      <span className="dg-ui-spread dg-ui-spread--unavailable">Range unavailable</span>
    );
  }

  const dotPct =
    pct !== undefined && Number.isFinite(pct) ? Math.max(0, Math.min(100, pct)) : null;

  // ARIA: children of a role="img" are presentational — the position speaks
  // through the PARENT label; the dot carries data-pct for tests/tooling.
  const ariaLabel =
    dotPct !== null
      ? `${label} — basis: ${basis}; position ${dotPct} of 100`
      : `${label} — basis: ${basis}`;

  return (
    <span className="dg-ui-spread" role="img" aria-label={ariaLabel} data-lane={lane}>
      <span className="dg-ui-spread__bar">
        {dotPct !== null && (
          <span
            className="dg-ui-spread__dot"
            data-pct={dotPct}
            data-lane={lane}
            style={{ left: `${dotPct}%` }}
          />
        )}
      </span>
      {sigma !== undefined && Number.isFinite(sigma) && (
        <span className="dg-ui-spread__sigma">{`σ ${sigma}`}</span>
      )}
      <span className="dg-ui-spread__basis">Basis: {basis}</span>
    </span>
  );
}
