// Shared, neutral rendering for the forced-cut capacity value-at-risk / recovery
// ranges (PR #92 RC v1). These are descriptive overlays on a frozen model
// baseline (decision_supported=false) — never a buy/sell verdict. The display
// deliberately gives both bounds equal visual weight and fails closed on
// missing or inverted data, so a range never reads as false precision or as a
// tidy fabricated number.

// Turn a backend snake_case token (caveat/status) into plain display copy.
export function humanizeToken(token: string): string {
  return token.replace(/_/g, " ");
}

// Neutral display string for a [low, high] range. Fails closed — returns null
// (caller renders "Range unavailable") when the range is missing, malformed, or
// inverted (low > high). We never render an inverted or partial range.
export function formatRange(
  range: readonly [number, number] | null | undefined,
): string | null {
  if (!range) {
    return null;
  }
  const [low, high] = range;
  // Fail closed on anything that is not a finite number — NaN, ±Infinity, or a
  // non-numeric value — so we never render a fabricated or partial bound.
  if (!Number.isFinite(low) || !Number.isFinite(high)) {
    return null;
  }
  if (low > high) {
    return null;
  }
  return `${low} to ${high}`;
}

// One labelled range row. The label and value live in separate spans so a
// label lookup matches only the label, while the aggregate lane text carries
// the numeric bounds. The single neutral class carries no directional modifier
// (no --positive / --negative), keeping best- and worst-case visually equal.
export function RangeRow({
  label,
  range,
}: {
  label: string;
  range: readonly [number, number] | null | undefined;
}) {
  const display = formatRange(range);
  return (
    <div className="dg-forced-cut-range">
      <span className="dg-forced-cut-range__label">{label}</span>
      <span className="dg-forced-cut-range__value">
        {display ?? "Range unavailable"}
      </span>
    </div>
  );
}
