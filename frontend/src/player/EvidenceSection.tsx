// Surface-3 T8 — evidence body. Renders the FULL steel-manned counter-argument
// (no truncation), top drivers, risk flags and caveats — every one of them
// through the copy dictionary, so a snake_case driver never reaches the screen.
//
// DG-109, David's prose ruling: ABSENCE RENDERS NOTHING. "No counter-argument
// available", "No top drivers available", "No risk flags available" and "No
// caveats available" asserted nothing about the player — they were the shape of
// the data showing through. They are gone. What is NOT absence still speaks: a
// caveat we hold is still printed, and a token the dictionary cannot yet say is
// printed raw in the receipt layer rather than dropped.
import type { z } from "zod";

import type { zPlayerDetailResponse } from "../lib/api/zod.gen";
import { lookupToken } from "../lib/copy";
import { TokenNotes } from "../ui/TokenNotes";

type Evidence = NonNullable<z.infer<typeof zPlayerDetailResponse>["evidence"]>;

function isAgeCliffFlag(text: string): boolean {
  return text.toLowerCase().includes("cliff");
}

function EvidenceBody({ evidence }: { evidence: Evidence }) {
  const counterArgument = evidence.counter_argument;
  const drivers = evidence.top_drivers.items;
  const riskFlags = evidence.risk_flags.items;
  const caveats = evidence.caveats.items;

  return (
    <>
      {counterArgument.status === "available" && counterArgument.text ? (
        <p className="dg-evidence__counter">{counterArgument.text}</p>
      ) : null}

      <TokenNotes className="dg-evidence__drivers" tokens={drivers} />

      {riskFlags.length > 0 && (
        <ul className="dg-evidence__risks">
          {riskFlags.map((flag) => {
            // The amber age-cliff treatment is constitutional, so it keys off
            // the RAW token — the sentence says "decline", not "cliff".
            const note = lookupToken(flag);
            return (
              <li
                key={flag}
                className={
                  isAgeCliffFlag(flag)
                    ? "dg-evidence__risk dg-evidence__risk--age-cliff-amber"
                    : "dg-evidence__risk"
                }
                {...(note.mapped ? {} : { "data-receipt": true })}
              >
                {note.mapped ? note.text : note.raw}
              </li>
            );
          })}
        </ul>
      )}

      <TokenNotes className="dg-evidence__caveats" tokens={caveats} />
    </>
  );
}

export function EvidenceSection({ evidence }: { evidence: Evidence | null }) {
  // No evidence block at all is absence too — the section itself disappears
  // rather than announcing an empty region.
  if (!evidence) return null;

  const hasContent =
    (evidence.counter_argument.status === "available" &&
      Boolean(evidence.counter_argument.text)) ||
    evidence.top_drivers.items.length > 0 ||
    evidence.risk_flags.items.length > 0 ||
    evidence.caveats.items.length > 0;
  if (!hasContent) return null;

  return (
    <section className="dg-evidence" aria-label="Evidence">
      <EvidenceBody evidence={evidence} />
    </section>
  );
}
