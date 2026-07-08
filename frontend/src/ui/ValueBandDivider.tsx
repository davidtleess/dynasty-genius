// DG primitive: the value-band divider — DN's tier-banding scannability with
// a DISCLOSED numeric basis; subjective fantasy tiers ("Elite", "Bust") are
// constitutionally banned (benchmark translation §3).
import "./ui.css";

export function ValueBandDivider({ label, basis }: { label: string; basis: string }) {
  // A static labeled separator (non-focusable, never operated) is valid ARIA
  // 1.2; Biome's three separator rules all assume the focusable widget
  // variant, and <hr> cannot carry the label + disclosed-basis content.
  return (
    // biome-ignore lint/a11y/useFocusableInteractive: static non-widget separator; focus would be an a11y regression
    // biome-ignore lint/a11y/useSemanticElements: <hr> cannot carry the label + basis content this divider exists for
    // biome-ignore lint/a11y/useAriaPropsForRole: aria-valuenow applies only to the focusable window-splitter variant
    <div className="dg-ui-band-divider" role="separator" aria-label={label}>
      <span className="dg-ui-band-divider__tick" />
      <span className="dg-ui-band-divider__label">{label}</span>
      <span className="dg-ui-band-divider__basis">{basis}</span>
    </div>
  );
}
