// DG primitive: graded attribute bar (benchmark player-profile pattern) —
// rendered ONLY with a disclosed basis, always the neutral palette; grade
// magnitude is length, never a verdict color.
import "./ui.css";

export function GradedBar({
  label,
  value,
  basis,
}: {
  label: string;
  value: number;
  basis: string;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <span className="dg-ui-graded">
      <span className="dg-ui-graded__label">{label}</span>
      {/* biome-ignore lint/a11y/useSemanticElements: native <meter> cannot be
          custom-styled consistently cross-browser for the token-governed bar;
          explicit role="meter" + full aria value set is the accessible
          equivalent (same pattern as the AppShell banner precedent). */}
      <span
        className="dg-ui-graded__meter"
        role="meter"
        aria-label={label}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        data-palette="neutral"
      >
        <span className="dg-ui-graded__fill" style={{ width: `${clamped}%` }} />
      </span>
      <span className="dg-ui-graded__value">{value}</span>
      <span className="dg-ui-graded__basis">Basis: {basis}</span>
    </span>
  );
}
