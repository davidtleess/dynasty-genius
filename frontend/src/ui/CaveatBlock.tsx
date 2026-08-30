// DG primitive: the standard region caveat — high-contrast neutral (or
// structural-amber) disclosure block, single instance per region, never a
// card nested inside a card (reset spec Task 2).
//
// DG-109 review fix: this primitive used to render `items` VERBATIM, so whether
// a raw pipeline key reached the screen depended on each caller remembering to
// translate. Two of the five call sites did not — ModelRegion and MarketRegion
// on the FRONT PAGE handed it `comparison_window.status` and `aborted_reason`
// straight from the API, and on 2026-08-30 the live feed put
// `model_multi_vintage_ambiguous` on David's screen inside a caveat. The
// enforcement test could not see it because the captured fixture happened to be
// a quiet day with no status on that field.
//
// So the rule moved into the primitive, where a caller cannot forget it, and it
// is the same rule `TokenNotes` follows: a mapped token speaks its sentence in
// body copy; an UNMAPPED one still reaches the screen but only in the receipt
// layer, labelled as raw, never dressed up as prose the dictionary has not
// written. Prose passed in by a caller is returned untouched — `lookupToken` on
// a string carrying no raw key is a pass-through — so the composed sentences
// the baseline sections build still render exactly as they did.
import { lookupToken } from "../lib/copy";
import "./ui.css";

export function CaveatBlock({
  tone,
  title,
  items,
}: {
  tone: "neutral" | "structural";
  title: string;
  items: string[];
}) {
  const notes = items.map(lookupToken);
  const spoken = notes.filter((note) => note.mapped);
  const untranslated = notes.filter((note) => !note.mapped);

  // Absence renders nothing — an empty caveat block asserts nothing (spec §6.6).
  if (notes.length === 0) return null;

  return (
    <aside className="dg-ui-caveat" role="note" aria-label={title} data-tone={tone}>
      <span className="dg-ui-caveat__title">{title}</span>
      {spoken.length > 0 && (
        <ul className="dg-ui-caveat__items">
          {spoken.map((note) => (
            <li key={note.raw}>{note.text}</li>
          ))}
        </ul>
      )}
      {untranslated.length > 0 && (
        <p className="dg-ui-raw-note" data-receipt data-testid="untranslated-caveats">
          Straight from the data feed, not yet written in plain language:{" "}
          {untranslated.map((note) => note.raw).join(", ")}
        </p>
      )}
    </aside>
  );
}
