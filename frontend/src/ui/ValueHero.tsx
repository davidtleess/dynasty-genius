// DG primitive: the value number is the hero (benchmark §2.2) — big, focal,
// weighted; its basis disclosed beside it; never colored by verdict.
import "./ui.css";

export function ValueHero({
  label,
  value,
  basis,
}: {
  label: string;
  value: string;
  basis: string;
}) {
  return (
    <span className="dg-ui-value-hero">
      <span className="dg-ui-value-hero__label">{label}</span>
      <span className="dg-ui-value-hero__number">{value}</span>
      <span className="dg-ui-value-hero__basis">{basis}</span>
    </span>
  );
}
