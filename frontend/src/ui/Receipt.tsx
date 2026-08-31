// DG-120 — the receipt primitive: a human label, with its address beneath it.
//
// THE DISTINCTION THIS COMPONENT EXISTS TO HOLD. A receipt carries two kinds of
// string and the product used to render both the same way, which is how
// `roster_capacity: live_precondition_not_ok:capture_health_ok=degraded` ended
// up one click behind the header pill:
//
//   an IDENTIFIER is an ADDRESS — a path, an artifact id, a run id, a hash, a
//   git sha, a schema version. A person may want to copy it, paste it, grep for
//   it. Rewording it destroys the only thing it was for, so it is rendered
//   verbatim inside `data-identifier`, in mono, and the render rule stands aside
//   for it by that declaration and no other.
//
//   a MESSAGE is a SENTENCE — a status, a reason, a condition, a count. Nothing
//   is reachable by `live_precondition_not_ok`. It goes through `lib/copy.ts`
//   like every other sentence in the product, and if the dictionary has no
//   entry it is rendered raw as PROSE, which the render rule then fails on. An
//   unwritten sentence is a defect that should be loud.
//
// `data-receipt` stays on the wrapper: it marks the layer for styling and for
// the browser gate. It no longer grants an exemption — see renderRule.ts.
import type { ReactNode } from "react";

import { fieldLabel, type ReceiptSegment } from "../lib/copy";
import "./ui.css";

/**
 * An address, byte-exact. The ONE declaration that stands the render rule down
 * for machinery, so every use of it is a claim that these bytes name something
 * a person could go and look at.
 */
export function Identifier({ children }: { children: ReactNode }) {
  return (
    <span className="dg-receipt__id" data-identifier>
      {children}
    </span>
  );
}

/**
 * A translated message. Prose runs render as text; identifiers embedded inside
 * the sentence (a missing evidence path, a stream id) keep their own bytes.
 */
export function ReceiptMessage({ segments }: { segments: ReceiptSegment[] }) {
  return (
    <span className="dg-receipt__message">
      {segments.map((segment, index) =>
        segment.kind === "prose" ? (
          // biome-ignore lint/suspicious/noArrayIndexKey: segments are a positional decomposition of one sentence — position IS the identity, and the array is rebuilt whole whenever the sentence changes.
          <span key={`p${index}`}>{segment.text}</span>
        ) : (
          // biome-ignore lint/suspicious/noArrayIndexKey: as above.
          <Identifier key={`i${index}`}>{segment.raw}</Identifier>
        ),
      )}
    </span>
  );
}

/**
 * One receipt line: what it is in words, then the address underneath.
 *
 * The order is the point. A manager reads the label and stops; an operator
 * reads on to the address. Neither has to decode the other's half, and nothing
 * that was on screen before this component existed has left it.
 */
export function ReceiptRow({
  label,
  message,
  identifier,
}: {
  label: string;
  message?: ReceiptSegment[];
  identifier?: string | null;
}) {
  return (
    <span className="dg-receipt__row">
      <span className="dg-receipt__label">{label}</span>
      {message !== undefined && message.length > 0 && (
        <ReceiptMessage segments={message} />
      )}
      {/* Absence renders nothing (spec §6 rule 6): a row with no address prints
          no empty slot where one would look withheld. */}
      {identifier !== null && identifier !== undefined && identifier !== "" && (
        <Identifier>{identifier}</Identifier>
      )}
    </span>
  );
}

/**
 * A one-line citation: the label, then the address, on the same line.
 *
 * The dense form, for a receipt that is one short line — a schema version, a
 * lookup key. Same law as `ReceiptRow`: the label is ours and the value is the
 * artifact's, declared as an identifier so the render rule can tell them apart.
 *
 * `not recorded` is a FACT, not an absence: the field was read and held
 * nothing. It stays prose, so a future value that is machinery cannot slip in
 * behind an identifier declaration this row did not earn.
 */
export function ReceiptCitation({
  label,
  raw,
}: {
  label: string;
  raw: string | number | null;
}) {
  const shown = raw === null || raw === "" ? null : String(raw);
  return (
    <>
      {label}:{" "}
      {shown === null ? (
        <span className="dg-receipt__message">not recorded</span>
      ) : (
        <Identifier>{shown}</Identifier>
      )}
    </>
  );
}

/**
 * A field receipt: a value, then the producer field it came from.
 *
 * DG-119 rendered this shape as ONE string out of `copy.ts` — "0.841 (from
 * complementarity_score)" — which is precisely the form DG-120 retired one file
 * over: a single string cannot declare which half of itself is an address, so
 * the render rule could only take the whole line or leave it. Identical bytes on
 * screen, two nodes, and the field name declared as the address it is.
 *
 * `withLabel` prints the field's human name first, for a receipt that stands on
 * its own line. Leave it off where a `<dt>` already names the field — printing
 * both gives a manager the same words twice within eight lines, which reads as
 * a bug.
 *
 * `not recorded` is a FACT (the field was read and held nothing), so it stays
 * prose and never rides in behind the identifier declaration.
 */
export function FieldReceipt({
  field,
  value,
  withLabel = false,
}: {
  field: string;
  value: string | number | null;
  withLabel?: boolean;
}) {
  const shown = value === null || value === "" ? "not recorded" : String(value);
  return (
    <>
      {withLabel ? `${fieldLabel(field)} — ` : null}
      {shown} (from <Identifier>{field}</Identifier>)
    </>
  );
}
