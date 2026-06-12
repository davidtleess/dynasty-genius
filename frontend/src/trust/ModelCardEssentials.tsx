// Model Trust Console — ModelCardEssentials (T9). The surface's safety instructions.
//
// Renders the curated model-card fields full-text (no truncation): intended use, the
// out-of-scope uses, caveats, and known failure modes. This component is the SINGLE
// SOURCE of the "Model card unavailable" degradation message — TrustConsole mounts it
// unconditionally and it owns the null state, so the message can never render twice.
import type { TrustConsoleViewModel } from "./trustViewModel";

export function ModelCardEssentials({
  card,
}: {
  card: TrustConsoleViewModel["model_card"];
}) {
  if (card === null) {
    return <p className="dg-trust-card__unavailable">Model card unavailable</p>;
  }

  return (
    <section className="dg-trust-card" aria-label="Model card essentials">
      <p className="dg-trust-card__use">{card.intended_use}</p>

      <h4 className="dg-trust-card__heading">Out of scope</h4>
      <ul className="dg-trust-card__list">
        {card.out_of_scope_uses.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      <h4 className="dg-trust-card__heading">Caveats</h4>
      <ul className="dg-trust-card__list">
        {card.caveats.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      <h4 className="dg-trust-card__heading">Known failure modes</h4>
      <ul className="dg-trust-card__list">
        {card.known_failure_modes.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
