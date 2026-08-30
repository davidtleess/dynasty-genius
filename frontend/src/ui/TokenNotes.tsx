// DG primitive: a list of backend tokens, rendered as the copy dictionary says.
//
// Three rules live here so no surface has to remember them:
//   1. Absence renders NOTHING. An empty list produces no element, no heading and
//      no "none available" row — absence of content is not content (spec §6.6).
//   2. A mapped token renders its sentence in body copy.
//   3. An UNMAPPED token still reaches the screen, but only in the receipt layer
//      and labelled as raw. The fact is never dropped; it is just never dressed
//      up as prose the dictionary has not actually written.
import { lookupToken, type TokenNote } from "../lib/copy";
import "./ui.css";

export function TokenNotes({
  tokens,
  className,
  ariaLabel,
  notes,
}: {
  /** Raw backend tokens. Ignored when `notes` is supplied. */
  tokens?: readonly string[];
  /** Pre-translated notes, for callers that need a sourced sentence. */
  notes?: readonly TokenNote[];
  className?: string;
  ariaLabel?: string;
}) {
  const all = notes ?? (tokens ?? []).map(lookupToken);
  const spoken = all.filter((note) => note.mapped);
  const untranslated = all.filter((note) => !note.mapped);

  if (all.length === 0) return null;

  return (
    <>
      {spoken.length > 0 && (
        <ul className={className} {...(ariaLabel ? { "aria-label": ariaLabel } : {})}>
          {spoken.map((note) => (
            <li key={note.raw}>{note.text}</li>
          ))}
        </ul>
      )}
      {untranslated.length > 0 && (
        <p className="dg-ui-raw-note" data-receipt data-testid="untranslated-tokens">
          Straight from the data feed, not yet written in plain language:{" "}
          {untranslated.map((note) => note.raw).join(", ")}
        </p>
      )}
    </>
  );
}
