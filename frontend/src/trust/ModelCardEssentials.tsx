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

  // DG-109: the model card is a CITED DOCUMENT, quoted full-text and
  // deliberately never truncated. Paraphrasing a statistic inside it (its
  // caveats name fold-to-fold RMSE) would misquote the card, which is the same
  // reason a provenance receipt keeps the artifact's real name. So the quoted
  // body is DECLARED as receipt and labelled as a quotation, rather than sitting
  // silently outside a rule it was always exempt from. The heading a manager
  // reads stays plain English.
  return (
    <section className="dg-trust-card" aria-label="Model card essentials">
      <p className="dg-trust-lede">
        The model's own card, quoted as written — what it is for, where it should not be
        used, and how it is known to fail.
      </p>
      <div className="dg-trust-quoted" data-receipt>
        <p className="dg-trust-card__use">{card.intended_use}</p>

        {/* DG-118: these three were <h4> under the shell's <h1> and nothing in
            between, so Model Trust's outline jumped h1 → h4 (axe: heading-order,
            measured on the built bundle). They are the surface's top-level
            sections, so h2 is what they were always describing. */}
        <h2 className="dg-trust-card__heading">Out of scope</h2>
        <ul className="dg-trust-card__list">
          {card.out_of_scope_uses.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>

        <h2 className="dg-trust-card__heading">Caveats</h2>
        <ul className="dg-trust-card__list">
          {card.caveats.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>

        <h2 className="dg-trust-card__heading">Known failure modes</h2>
        <ul className="dg-trust-card__list">
          {card.known_failure_modes.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
